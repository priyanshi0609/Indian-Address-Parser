# parser.py

from models import ParsedAddress
from utils import get_abbreviations, get_state_mappings, normalize_text
from extractor import *
from config import logger
from data_loader import load_datasets
from rapidfuzz import process, fuzz
import re


class IndianAddressParser:

    def __init__(self):
        self.addresses_df, _, self.city_lookup, self.pin_lookup = load_datasets()
        self.abbreviations = get_abbreviations()
        self.state_mappings = get_state_mappings()

    # -------------------------------
    # 🔥 CITY + STATE EXTRACTION
    # -------------------------------

    def extract_city_state(self, text: str, pincode: str = None):
        city = state = None

        # 1️⃣ PRIORITY: Pincode inference
        if pincode and pincode in self.pin_lookup:
            pin_data = self.pin_lookup[pincode]
            return pin_data['city'], pin_data['state']

        words = re.split(r'[,\n\s\.]+', text.lower())
        words = [w.strip() for w in words if w.strip()]

        # Exact multi-word matching
        for i in range(len(words) - 2):
            three = ' '.join(words[i:i+3])
            two = ' '.join(words[i:i+2])

            if three in self.city_lookup:
                return three.title(), self.city_lookup[three]['state']

            if two in self.city_lookup:
                return two.title(), self.city_lookup[two]['state']

        # 🔥 Fuzzy matching (handles typos)
        combined_text = ' '.join(words)

        best_match = process.extractOne(
            combined_text,
            self.city_lookup.keys(),
            scorer=fuzz.partial_ratio
        )

        if best_match and best_match[1] > 85:
            matched_city = best_match[0]
            return matched_city.title(), self.city_lookup[matched_city]['state']

        return None, None

    # -------------------------------
    # 🔥 PINCODE VALIDATION
    # -------------------------------

    def validate_with_pincode(self, parsed: ParsedAddress) -> ParsedAddress:

        if parsed.pincode and parsed.pincode in self.pin_lookup:
            pin_data = self.pin_lookup[parsed.pincode]

            if not parsed.city:
                parsed.city = pin_data['city']

            if not parsed.district:
                parsed.district = pin_data['district']

            if not parsed.state:
                parsed.state = pin_data['state']

        return parsed

    # -------------------------------
    # 🔥 MAIN PARSER
    # -------------------------------

    def parse_address(self, address: str) -> ParsedAddress:

        if not address:
            return ParsedAddress()

        norm = normalize_text(address, self.abbreviations)
        parsed = ParsedAddress()

        # 1️⃣ Extract pincode first
        parsed.pincode = extract_pincode(norm)

        # 2️⃣ Infer city/state early
        parsed.city, parsed.state = self.extract_city_state(norm, parsed.pincode)

        # 3️⃣ Other components
        parsed.care_of = extract_care_of(norm)
        parsed.house_number = extract_house_number(norm)
        parsed.landmark = extract_landmark(norm)
        parsed.village = extract_village_info(norm)
        parsed.locality, parsed.street = extract_locality_info(norm)
        parsed.district, parsed.subdistrict = extract_district_info(norm)

        # 4️⃣ Validate against pincode
        parsed = self.validate_with_pincode(parsed)

        # -----------------------
        # 🔥 Confidence Scoring
        # -----------------------

        confidence = 0
        errors = []

        if parsed.pincode:
            confidence += 0.2
        else:
            errors.append("Pincode missing")

        if parsed.city:
            confidence += 0.2
        else:
            errors.append("City not detected")

        if parsed.state:
            confidence += 0.2
        else:
            errors.append("State not detected")

        if parsed.house_number:
            confidence += 0.2

        if parsed.locality or parsed.street:
            confidence += 0.2

        parsed.confidence_score = round(confidence, 2)
        parsed.validation_errors = errors

        logger.info(f"Parsed with confidence {parsed.confidence_score}")

        return parsed

    # -------------------------------
    # BULK PARSING
    # -------------------------------

    def parse_all_addresses(self):

        results = []

        for i, row in self.addresses_df.iterrows():
            original = row.get('address', '')
            parsed = self.parse_address(original)

            results.append({
                'id': i + 1,
                'original': original,
                'parsed': parsed.to_dict()
            })

        return results