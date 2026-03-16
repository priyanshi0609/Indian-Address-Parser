"""
parser.py — Core address parsing logic for the Indian Address Parser.

Architecture
────────────
IndianAddressParser.parse_address(raw: str) → ParsedAddress

Parsing pipeline (in order):
  1. Normalise text
  2. Extract PIN code
  3. Resolve city + state via PIN lookup (highest confidence)
  4. Extract all other fields with regex extractors
  5. Fallback: resolve city + state via fuzzy city-name match
  6. Fallback: resolve state from inline abbreviation
  7. Validate / enrich from PIN lookup
  8. Compute structured confidence score
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from config import (
    FUZZY_CITY_THRESHOLD,
    CONFIDENCE_WEIGHTS,
    logger,
)
from data_loader import load_datasets
from extractor import (
    extract_care_of,
    extract_building_name,
    extract_house_number,
    extract_landmark,
    extract_locality_info,
    extract_pincode,
    extract_village_info,
    extract_district_info,
    extract_state_from_text,
)
from models import ParsedAddress
from utils import get_abbreviations, get_state_mappings, normalize_text


class IndianAddressParser:
    """
    Parses raw Indian address strings into structured ParsedAddress objects.

    Usage
    ─────
        parser = IndianAddressParser()
        result = parser.parse_address("S/O Ram Singh, H No 15/1, Indira Nagar, Lucknow, UP - 226016")
        print(result.to_dict())
    """

    def __init__(self) -> None:
        self.addresses_df, _, self.city_lookup, self.pin_lookup = load_datasets()
        self.abbreviations   = get_abbreviations()
        self.state_mappings  = get_state_mappings()

        # Build state lookup for exact name matching (lower → canonical)
        self._state_names = {v.lower(): v for v in self.state_mappings.values()}
        self._state_names.update({k.lower(): v for k, v in self.state_mappings.items()})

        # Pre-build a list of city names for fuzzy matching
        self._city_keys: List[str] = list(self.city_lookup.keys())

        logger.info("IndianAddressParser initialised.")

    # ─────────────────────────────────────────────────────────────────────────
    # City + State resolution  (three strategies, most → least confident)
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_city_state_from_pin(
        self, pincode: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Strategy 1 — PIN lookup (most accurate)."""
        if pincode and pincode in self.pin_lookup:
            data = self.pin_lookup[pincode]
            return data["city"], data["state"], "pincode"
        return None, None, "none"

    def _resolve_city_state_exact(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Strategy 2 — exact multi-word city name match."""
        words = re.split(r'[,\n\s./\-]+', text.lower())
        words = [w.strip() for w in words if len(w.strip()) > 1]

        # Try 3-gram, 2-gram, 1-gram
        for n in (3, 2, 1):
            for i in range(len(words) - n + 1):
                candidate = ' '.join(words[i:i + n])
                if candidate in self.city_lookup:
                    data = self.city_lookup[candidate]
                    return candidate.title(), data["state"], "exact"

        return None, None, "none"

    def _resolve_city_state_fuzzy(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Strategy 3 — fuzzy city name match (handles typos)."""
        if not self._city_keys:
            return None, None, "none"

        # Use token_set_ratio so word order doesn't matter
        result = process.extractOne(
            text.lower(),
            self._city_keys,
            scorer=fuzz.token_set_ratio,
        )

        if result and result[1] >= FUZZY_CITY_THRESHOLD:
            matched = result[0]
            data    = self.city_lookup[matched]
            return matched.title(), data["state"], "fuzzy"

        return None, None, "none"

    def extract_city_state(
        self, text: str, pincode: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], str]:
        """
        Orchestrates the three resolution strategies in priority order.
        Returns (city, state, method).
        """
        # 1. PIN-based (most reliable)
        city, state, method = self._resolve_city_state_from_pin(pincode)
        if city:
            return city, state, method

        # 2. Exact name match
        city, state, method = self._resolve_city_state_exact(text)
        if city:
            return city, state, method

        # 3. Fuzzy name match
        city, state, method = self._resolve_city_state_fuzzy(text)
        if city:
            return city, state, method

        return None, None, "none"

    # ─────────────────────────────────────────────────────────────────────────
    # PIN code validation / enrichment
    # ─────────────────────────────────────────────────────────────────────────

    def _validate_with_pincode(self, parsed: ParsedAddress) -> ParsedAddress:
        """
        Fill any missing city / district / state values from the PIN lookup.
        Never overwrites values that are already set.
        """
        if not parsed.pincode or parsed.pincode not in self.pin_lookup:
            return parsed

        data = self.pin_lookup[parsed.pincode]
        if not parsed.city:
            parsed.city = data["city"]
        if not parsed.district:
            parsed.district = data["district"]
        if not parsed.state:
            parsed.state = data["state"]

        return parsed

    # ─────────────────────────────────────────────────────────────────────────
    # Confidence scoring
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_confidence(self, parsed: ParsedAddress) -> Tuple[float, List[str]]:
        """
        Weighted confidence score in [0.0, 1.0].
        Returns (score, list_of_missing_field_messages).
        """
        weights = CONFIDENCE_WEIGHTS
        score   = 0.0
        errors  = []

        checks = [
            ("pincode",  parsed.pincode,                   "Pincode missing"),
            ("city",     parsed.city,                      "City not detected"),
            ("state",    parsed.state,                     "State not detected"),
            ("house",    parsed.house_number,              "House number missing"),
            ("locality", parsed.locality or parsed.street, "Locality/street not detected"),
            ("care_of",  parsed.care_of,                   None),
            ("landmark", parsed.landmark,                  None),
        ]

        for key, value, error_msg in checks:
            if value:
                score += weights.get(key, 0)
            elif error_msg:
                errors.append(error_msg)

        return round(score, 2), errors

    # ─────────────────────────────────────────────────────────────────────────
    # Main parse method
    # ─────────────────────────────────────────────────────────────────────────

    def parse_address(self, address: str) -> ParsedAddress:
        """
        Parse a single raw address string.

        Args:
            address: Raw unstructured Indian address.

        Returns:
            ParsedAddress dataclass with all detected fields and metadata.
        """
        if not address or not str(address).strip():
            logger.warning("Empty address received.")
            parsed = ParsedAddress()
            parsed.validation_errors = ["Empty input"]
            return parsed

        # ── 1. Normalise ──────────────────────────────────────────────────────
        norm = normalize_text(address, self.abbreviations)
        parsed = ParsedAddress()

        # ── 2. PIN code (before city/state so PIN can inform them) ──────────
        parsed.pincode = extract_pincode(norm)

        # ── 3. City + State ───────────────────────────────────────────────────
        parsed.city, parsed.state, parsed.match_method = self.extract_city_state(
            norm, parsed.pincode
        )

        # ── 4. Care-of, House, Building, Landmark ────────────────────────────
        parsed.care_of      = extract_care_of(norm)
        parsed.house_number = extract_house_number(norm)
        parsed.building_name = extract_building_name(norm)
        parsed.landmark     = extract_landmark(norm)

        # ── 5. Locality + Street ──────────────────────────────────────────────
        parsed.locality, parsed.street = extract_locality_info(norm)

        # ── 6. Village, District, Subdistrict ─────────────────────────────────
        parsed.village = extract_village_info(norm)
        parsed.district, parsed.subdistrict = extract_district_info(norm)

        # ── 7. State fallback from inline abbreviation (e.g. ", UP") ─────────
        if not parsed.state:
            parsed.state = extract_state_from_text(norm, self.state_mappings)

        # ── 8. Enrich from PIN lookup (fill missing fields) ───────────────────
        parsed = self._validate_with_pincode(parsed)

        # ── 9. Confidence score ───────────────────────────────────────────────
        parsed.confidence_score, parsed.validation_errors = self._compute_confidence(parsed)

        logger.debug(
            f"Parsed | confidence={parsed.confidence_score} | method={parsed.match_method} "
            f"| city={parsed.city} | state={parsed.state} | pin={parsed.pincode}"
        )

        return parsed

    # ─────────────────────────────────────────────────────────────────────────
    # Bulk parsing
    # ─────────────────────────────────────────────────────────────────────────

    def parse_all_addresses(self) -> List[Dict]:
        """
        Parse every row in addresses.csv.
        Returns a list of dicts ready for JSON serialisation.
        """
        if self.addresses_df.empty:
            logger.warning("No sample addresses loaded — bulk parse skipped.")
            return []

        results = []
        for idx, row in self.addresses_df.iterrows():
            raw     = str(row.get("address", "")).strip()
            parsed  = self.parse_address(raw)
            results.append({
                "id":       idx + 1,
                "original": raw,
                "parsed":   parsed.to_dict(),
            })

        logger.info(f"Bulk parsed {len(results)} addresses.")
        return results

    def export_results_json(self, results: List[Dict], path: str = "parsed_output.json") -> None:
        """Write bulk parse results to a JSON file."""
        output = Path(path)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Results exported → {output.resolve()}")