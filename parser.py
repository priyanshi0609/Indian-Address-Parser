# Main IndianAddressParser class
from models import ParsedAddress
from utils import get_abbreviations, get_state_mappings, normalize_text
from extractor import *
from config import logger
from data_loader import load_datasets

class IndianAddressParser:
    def __init__(self):
        self.addresses_df, _, self.city_lookup, self.pin_lookup = load_datasets()
        self.abbreviations = get_abbreviations()
        self.state_mappings = get_state_mappings()

    def extract_city_state(self, text: str, pincode: str = None):
        city = state = None
        words = re.split(r'[,\n]', text.lower())
        for token in words:
            token = token.strip()
            if token in self.city_lookup:
                return token.title(), self.city_lookup[token]['state']
        if pincode and pincode in self.pin_lookup:
            return self.pin_lookup[pincode]['city'], self.pin_lookup[pincode]['state']
        return city, state

    def validate_with_pincode(self, parsed: ParsedAddress) -> ParsedAddress:
        if parsed.pincode in self.pin_lookup:
            parsed.city = parsed.city or self.pin_lookup[parsed.pincode]['city']
            parsed.district = parsed.district or self.pin_lookup[parsed.pincode]['district']
            parsed.state = parsed.state or self.pin_lookup[parsed.pincode]['state']
        return parsed

    def parse_address(self, address: str) -> ParsedAddress:
        if not address: return ParsedAddress()
        norm = normalize_text(address, self.abbreviations)
        parsed = ParsedAddress()
        parsed.pincode = extract_pincode(norm)
        parsed.care_of = extract_care_of(norm)
        parsed.house_number = extract_house_number(norm)
        parsed.landmark = extract_landmark(norm)
        parsed.village = extract_village_info(norm)
        parsed.locality, parsed.street = extract_locality_info(norm)
        parsed.district, parsed.subdistrict = extract_district_info(norm)
        parsed.city, parsed.state = self.extract_city_state(norm, parsed.pincode)
        return self.validate_with_pincode(parsed)

    def parse_all_addresses(self):
        results = []
        for i, row in self.addresses_df.iterrows():
            original = row.get('address', '')
            parsed = self.parse_address(original)
            results.append({'id': i + 1, 'original': original, 'parsed': parsed.to_dict()})
        return results

    def export_results_json(self, results, filename="parsed_output.json"):
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Exported results to {filename}")
