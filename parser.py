"""
parser.py — Core address parsing logic for the Indian Address Parser.

Core Philosophy — "PIN as Anchor"
───────────────────────────────────
A 6-digit PIN code uniquely identifies a post office area in India.
From that single anchor we can derive city, district, and state with
100% accuracy — even when the user never mentioned any of them.

Real-world delivery agent scenario:
    Input:  "Near Durga Mandir, Shahdara, 110032"
    Output: city=Delhi, state=Delhi, district=East Delhi,
            locality=Shahdara, landmark=Near Durga Mandir
    (house_number flagged as missing)

Pipeline (in order):
  1.  Normalise raw text
  2.  Extract PIN code  ← anchor
  3.  Enrich city / district / state from PIN lookup
  4.  Extract all explicitly mentioned fields (regex)
  5.  Infer locality from leftover tokens after known fields removed
  6.  Fallback city/state from text if PIN lookup missed
  7.  Compute confidence score + missing-field warnings
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rapidfuzz import fuzz, process

from config import CONFIDENCE_WEIGHTS, FUZZY_CITY_THRESHOLD, logger
from data_loader import load_datasets
from extractor import (
    extract_building_name,
    extract_care_of,
    extract_district_info,
    extract_house_number,
    extract_landmark,
    extract_locality_info,
    extract_pincode,
    extract_state_from_text,
    extract_village_info,
    infer_locality_from_tokens,
)
from models import ParsedAddress
from utils import get_abbreviations, get_state_mappings, normalize_text


# ──────────────────────────────────────────────────────────────────────────────
# Noise tokens to ignore during leftover inference
# ──────────────────────────────────────────────────────────────────────────────
_SKIP_TOKENS: Set[str] = {
    "near", "opp", "opposite", "beside", "behind", "next", "to",
    "son", "of", "wife", "daughter", "husband", "father", "mother",
    "care", "house", "number", "flat", "plot", "door", "room",
    "street", "road", "marg", "lane", "sector", "block", "phase",
    "village", "gram", "gaon", "post", "office", "district", "tehsil",
    "taluka", "mandal", "state", "india", "and", "the", "in", "at",
    "pin", "pincode",
}


class IndianAddressParser:
    """
    Parses raw Indian address strings into structured ParsedAddress objects.

    The PIN code is treated as the primary anchor:
    - If a PIN is present, city / district / state are filled from the
      PIN lookup table — even if the user never mentioned them.
    - All other fields are extracted from what remains in the address text.
    - A leftover-token scan fills locality when no explicit locality keyword
      (Sector / Block / Phase) was found.

    Usage
    ─────
        parser = IndianAddressParser()
        result = parser.parse_address("Near Durga Mandir, Shahdara, 110032")
        print(result.to_dict())
        # → city=Delhi, state=Delhi, district=East Delhi,
        #   locality=Shahdara, landmark=Near Durga Mandir
    """

    def __init__(self) -> None:
        self.addresses_df, _, self.city_lookup, self.pin_lookup = load_datasets()
        self.abbreviations  = get_abbreviations()
        self.state_mappings = get_state_mappings()

        # Lower-case canonical state names for exact matching
        self._state_names: Dict[str, str] = {
            v.lower(): v for v in self.state_mappings.values()
        }
        self._state_names.update(
            {k.lower(): v for k, v in self.state_mappings.items()}
        )

        # Sorted city list for fuzzy matching (longer names first avoids
        # short-city names stealing matches from multi-word city names)
        self._city_keys: List[str] = sorted(
            self.city_lookup.keys(), key=len, reverse=True
        )

        logger.info("IndianAddressParser initialised.")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1 — PIN-code anchor  (highest confidence)
    # ─────────────────────────────────────────────────────────────────────────

    def _enrich_from_pin(self, parsed: ParsedAddress) -> str:
        """
        Fill city / district / state from the PIN lookup.
        Never overwrites fields already populated.
        Returns the match method string.
        """
        if not parsed.pincode or parsed.pincode not in self.pin_lookup:
            return "none"

        data = self.pin_lookup[parsed.pincode]

        if not parsed.city:
            parsed.city = data["city"]
        if not parsed.district:
            parsed.district = data["district"]
        if not parsed.state:
            parsed.state = data["state"]

        return "pincode"

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2 — Text-based city/state fallback  (when PIN is missing/unknown)
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_city_state_exact(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Exact multi-word city name scan (3-gram → 2-gram → 1-gram)."""
        words = re.split(r'[,\n\s./\-]+', text.lower())
        words = [w for w in words if len(w) > 1]

        for n in (3, 2, 1):
            for i in range(len(words) - n + 1):
                candidate = " ".join(words[i : i + n])
                if candidate in self.city_lookup:
                    data = self.city_lookup[candidate]
                    return candidate.title(), data["state"], "exact"

        return None, None, "none"

    def _resolve_city_state_fuzzy(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str], str]:
        """Fuzzy city name match — handles typos and partial names."""
        if not self._city_keys:
            return None, None, "none"

        result = process.extractOne(
            text.lower(),
            self._city_keys,
            scorer=fuzz.token_set_ratio,
        )

        if result and result[1] >= FUZZY_CITY_THRESHOLD:
            matched = result[0]
            data = self.city_lookup[matched]
            return matched.title(), data["state"], "fuzzy"

        return None, None, "none"

    def _resolve_city_state_from_text(
        self, norm: str, parsed: ParsedAddress
    ) -> str:
        """
        Try to fill city/state from the address text itself.
        Called only when PIN lookup didn't supply them.
        Returns match method.
        """
        city, state, method = self._resolve_city_state_exact(norm)
        if not city:
            city, state, method = self._resolve_city_state_fuzzy(norm)

        if city and not parsed.city:
            parsed.city = city
        if state and not parsed.state:
            parsed.state = state

        # Last resort — bare state abbreviation like ", UP" or ", MH"
        if not parsed.state:
            parsed.state = extract_state_from_text(norm, self.state_mappings)
            if parsed.state:
                method = "state_abbr"

        return method

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3 — Leftover token inference  (fills locality when not explicit)
    # ─────────────────────────────────────────────────────────────────────────

    def _infer_missing_locality(self, norm: str, parsed: ParsedAddress) -> None:
        """
        After all explicit extractors have run, any comma-separated token
        that doesn't match a known field value is a candidate for locality.

        Example:
            "Near Durga Mandir, Shahdara, 110032"
            After removing landmark, pincode → leftover = ["shahdara"]
            → locality = "Shahdara"
        """
        if parsed.locality:
            return  # already found by explicit extractor

        known_values: Set[str] = {
            v.lower()
            for v in [
                parsed.city, parsed.district, parsed.state,
                parsed.pincode, parsed.village, parsed.subdistrict,
            ]
            if v
        }

        locality = infer_locality_from_tokens(norm, known_values, _SKIP_TOKENS)
        if locality:
            parsed.locality = locality

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4 — Confidence scoring
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_confidence(
        self, parsed: ParsedAddress
    ) -> Tuple[float, List[str]]:
        """
        Weighted confidence score in [0.0, 1.0].

        Scoring logic:
        • PIN present AND in known lookup  → full pincode weight
        • PIN present but NOT in lookup    → half weight (could be new PIN)
        • City / state inferred from PIN   → full weight (very reliable)
        • City / state from text match     → full weight
        • House number missing             → flagged (delivery needs this)

        Returns (score, missing_field_warnings).
        """
        weights = CONFIDENCE_WEIGHTS
        score   = 0.0
        errors  = []

        # PIN scoring
        if parsed.pincode:
            if parsed.pincode in self.pin_lookup:
                score += weights.get("pincode", 0)
            else:
                # PIN exists but not in our dataset — partial credit
                score += weights.get("pincode", 0) * 0.5
                errors.append("Pincode not found in reference dataset")
        else:
            errors.append("Pincode missing — location accuracy reduced")

        # City / State
        if parsed.city:
            score += weights.get("city", 0)
        else:
            errors.append("City not detected")

        if parsed.state:
            score += weights.get("state", 0)
        else:
            errors.append("State not detected")

        # House number — most critical for delivery
        if parsed.house_number:
            score += weights.get("house", 0)
        else:
            errors.append("House number missing — delivery agent may need to ask")

        # Locality / street
        if parsed.locality or parsed.street:
            score += weights.get("locality", 0)
        else:
            errors.append("Locality/street not detected")

        # Optional bonus fields (no error if missing)
        if parsed.care_of:
            score += weights.get("care_of", 0)
        if parsed.landmark:
            score += weights.get("landmark", 0)

        return round(min(score, 1.0), 2), errors

    # ─────────────────────────────────────────────────────────────────────────
    # Public — parse a single address
    # ─────────────────────────────────────────────────────────────────────────

    def parse_address(self, address: str) -> ParsedAddress:
        """
        Parse one raw Indian address string into structured fields.

        Handles:
        • Completely unstructured input  ("Near Durga Mandir, Shahdara 110032")
        • Missing state/city             (inferred from PIN)
        • Missing house number           (flagged in validation_errors)
        • Noisy / concatenated tokens    ("237okhlaphase3NewDelhi110001")
        • Spelling mistakes in city names (fuzzy match)
        • Rural addresses                (village, district, tehsil)

        Args:
            address: Raw unstructured Indian address string.

        Returns:
            ParsedAddress with all detected fields + confidence_score
            + validation_errors listing what's missing.
        """
        if not address or not str(address).strip():
            logger.warning("Empty address received.")
            p = ParsedAddress()
            p.validation_errors = ["Empty input"]
            return p

        # ── 1. Normalise ─────────────────────────────────────────────────────
        norm   = normalize_text(address, self.abbreviations)
        parsed = ParsedAddress()

        # ── 2. Extract PIN — this is our anchor ──────────────────────────────
        parsed.pincode = extract_pincode(norm)

        # ── 3. Immediately enrich city/district/state from PIN ───────────────
        #       This fires even if user wrote ONLY the PIN + landmark.
        method = self._enrich_from_pin(parsed)

        # ── 4. Extract all explicitly mentioned fields ────────────────────────
        parsed.care_of       = extract_care_of(norm)
        parsed.house_number  = extract_house_number(norm)
        parsed.building_name = extract_building_name(norm)
        parsed.landmark      = extract_landmark(norm)
        parsed.locality, parsed.street = extract_locality_info(norm)
        parsed.village       = extract_village_info(norm)
        parsed.district, parsed.subdistrict = extract_district_info(norm)

        # ── 5. Fill city/state from text if PIN lookup didn't supply them ─────
        if not parsed.city or not parsed.state:
            text_method = self._resolve_city_state_from_text(norm, parsed)
            if method == "none":
                method = text_method

        # ── 6. Infer locality from leftover tokens  ───────────────────────────
        #       e.g. "Shahdara" in "Near Durga Mandir, Shahdara, 110032"
        self._infer_missing_locality(norm, parsed)

        # ── 7. Record how we resolved city/state ─────────────────────────────
        parsed.match_method = method

        # ── 8. Confidence score ───────────────────────────────────────────────
        parsed.confidence_score, parsed.validation_errors = self._compute_confidence(parsed)

        logger.debug(
            "Parsed | conf=%.2f | method=%s | city=%s | state=%s | pin=%s | "
            "house=%s | locality=%s | landmark=%s",
            parsed.confidence_score,
            parsed.match_method,
            parsed.city,
            parsed.state,
            parsed.pincode,
            parsed.house_number,
            parsed.locality,
            parsed.landmark,
        )

        return parsed

    # ─────────────────────────────────────────────────────────────────────────
    # Public — bulk parse from CSV
    # ─────────────────────────────────────────────────────────────────────────

    def parse_all_addresses(self) -> List[Dict]:
        """Parse every row in addresses.csv."""
        if self.addresses_df.empty:
            logger.warning("No sample addresses loaded — bulk parse skipped.")
            return []

        results = []
        for idx, row in self.addresses_df.iterrows():
            raw    = str(row.get("address", "")).strip()
            parsed = self.parse_address(raw)
            results.append({"id": idx + 1, "original": raw, "parsed": parsed.to_dict()})

        logger.info("Bulk parsed %d addresses.", len(results))
        return results

    def export_results_json(
        self, results: List[Dict], path: str = "parsed_output.json"
    ) -> None:
        """Write bulk parse results to a JSON file."""
        output = Path(path)
        output.write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Results exported → %s", output.resolve())