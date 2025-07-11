import pandas as pd
import re
import json
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ParsedAddress:
    care_of: Optional[str] = None
    house_number: Optional[str] = None
    building_name: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    subdistrict: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

class IndianAddressParser:
    def __init__(self):
        self.load_datasets()
        self.setup_patterns()
        self.setup_abbreviations()
        self.setup_state_mappings()

    def load_datasets(self):
        try:
            self.addresses_df = pd.read_csv("addresses.csv")
            self.pin_df = pd.read_csv("pincodes.csv")
            self.pin_df['Pincode'] = self.pin_df['Pincode'].astype(str)

            # NEW: Load city-district-state mapping
            self.city_df = pd.read_csv("Cities_Towns_District_State_India.csv")
            self.city_df.columns = [col.strip() for col in self.city_df.columns]
            self.city_df.dropna(subset=["City/Town", "District", "State/Union territory*"], inplace=True)
            self.city_lookup = {
                row["City/Town"].strip().lower(): {
                    "district": row["District"].strip(),
                    "state": row["State/Union territory*"].strip()
                }
                for _, row in self.city_df.iterrows()
            }

            # PIN code lookup
            self.pin_lookup = {
                row['Pincode']: {
                    'city': row['City'],
                    'district': row['District'],
                    'state': row['State']
                }
                for _, row in self.pin_df.iterrows()
            }

            logger.info("All datasets loaded successfully.")

        except Exception as e:
            logger.error(f"Dataset load error: {e}")
            self.addresses_df = None
            self.pin_df = None
            self.city_lookup = {}
            self.pin_lookup = {}

    def setup_patterns(self):
        self.pin_pattern = re.compile(r'\b\d{6}\b')
        self.care_of_patterns = [
            re.compile(r'(?:s/o|son of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
            re.compile(r'(?:w/o|wife of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
            re.compile(r'(?:c/o|care of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
            re.compile(r'(?:d/o|daughter of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE)
        ]
        self.house_patterns = [
            re.compile(r'(?:h\.?\s*no\.?|house\s+no\.?|house\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
            re.compile(r'(?:plot\s+no\.?|plot\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
            re.compile(r'(?:door\s+no\.?|door\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
        ]
        self.landmark_patterns = [
            re.compile(r'(?:near|opp\.?|opposite)\s+([a-z0-9\s]+?)(?:,|$)', re.IGNORECASE),
        ]
        self.locality_patterns = [
            re.compile(r'(?:sector|sec\.?)\s*([0-9a-z\-]+)', re.IGNORECASE),
        ]
        self.village_patterns = [
            re.compile(r'(?:village|vill\.?)\s+([a-z\s]+?)(?:,|\s+post|$)', re.IGNORECASE),
        ]
        self.district_patterns = [
            re.compile(r'(?:district|dist\.?)\s+([a-z\s]+?)(?:,|$)', re.IGNORECASE),
        ]

    def setup_abbreviations(self):
        self.abbreviations = {
            's/o': 'son of', 'w/o': 'wife of', 'c/o': 'care of', 'd/o': 'daughter of',
            'rd': 'road', 'st': 'street', 'sec': 'sector', 'ph': 'phase',
            'h.no': 'house number', 'vill': 'village', 'po': 'post office', 'dist': 'district'
        }

    def setup_state_mappings(self):
        self.state_mappings = {
            'up': 'Uttar Pradesh', 'mh': 'Maharashtra', 'dl': 'Delhi', 'ka': 'Karnataka',
            'tn': 'Tamil Nadu', 'rj': 'Rajasthan', 'br': 'Bihar', 'gj': 'Gujarat'
            # ...add others as needed
        }

    def normalize_text(self, text: str) -> str:
        if not text or pd.isna(text): return ""
        text = str(text).lower().strip()
        text = re.sub(r'[^\w\s,./\-()]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        words = text.split()
        expanded = [self.abbreviations.get(re.sub(r'[^\w]', '', w), w) for w in words]
        return ' '.join(expanded).strip()

    def extract_pincode(self, text: str) -> Optional[str]:
        match = self.pin_pattern.search(text)
        return match.group().strip() if match else None

    def extract_care_of(self, text: str) -> Optional[str]:
        for p in self.care_of_patterns:
            m = p.search(text)
            if m:
                return m.group(1).strip().title()
        return None

    def extract_house_number(self, text: str) -> Optional[str]:
        for p in self.house_patterns:
            m = p.search(text)
            if m:
                return re.sub(r'[^\w/\-]', '', m.group(1).strip())
        return None

    def extract_landmark(self, text: str) -> Optional[str]:
        for p in self.landmark_patterns:
            m = p.search(text)
            if m:
                return m.group(1).strip().title()
        return None

    def extract_locality_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        for p in self.locality_patterns:
            m = p.search(text)
            if m:
                return f"Sector {m.group(1)}", None
        return None, None

    def extract_village_info(self, text: str) -> Optional[str]:
        for p in self.village_patterns:
            m = p.search(text)
            if m:
                return m.group(1).strip().title()
        return None

    def extract_district_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        for p in self.district_patterns:
            m = p.search(text)
            if m:
                return m.group(1).strip().title(), None
        return None, None

    def extract_city_state(self, text: str, pincode: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        city = None
        state = None
        words = re.split(r'[,\n]', text.lower())
        for token in words:
            token = token.strip()
            if token in self.city_lookup:
                city = token.title()
                state = self.city_lookup[token]['state']
                return city, state

        if pincode and pincode in self.pin_lookup:
            return self.pin_lookup[pincode]['city'], self.pin_lookup[pincode]['state']

        return city, state

    def validate_with_pincode(self, parsed: ParsedAddress) -> ParsedAddress:
        if parsed.pincode in self.pin_lookup:
            if not parsed.city:
                parsed.city = self.pin_lookup[parsed.pincode]['city']
            if not parsed.district:
                parsed.district = self.pin_lookup[parsed.pincode]['district']
            if not parsed.state:
                parsed.state = self.pin_lookup[parsed.pincode]['state']
        return parsed

    def parse_address(self, address: str) -> ParsedAddress:
        if not address or pd.isna(address):
            return ParsedAddress()
        norm = self.normalize_text(address)
        parsed = ParsedAddress()
        parsed.pincode = self.extract_pincode(norm)
        parsed.care_of = self.extract_care_of(norm)
        parsed.house_number = self.extract_house_number(norm)
        parsed.landmark = self.extract_landmark(norm)
        parsed.village = self.extract_village_info(norm)
        locality, street = self.extract_locality_info(norm)
        parsed.locality = locality
        parsed.street = street
        district, subdistrict = self.extract_district_info(norm)
        parsed.district = district
        parsed.subdistrict = subdistrict
        city, state = self.extract_city_state(norm, parsed.pincode)
        parsed.city = city
        parsed.state = state
        parsed = self.validate_with_pincode(parsed)
        return parsed

    def parse_all_addresses(self) -> List[Dict]:
        results = []
        for i, row in self.addresses_df.iterrows():
            original = row.get('address', '')
            parsed = self.parse_address(original)
            results.append({
                'id': i+1,
                'original': original,
                'parsed': parsed.to_dict()
            })
        return results

    def export_results_json(self, results: List[Dict], filename: str = "parsed_output.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Exported to {filename}")

def main():
    print("Initializing Address Parser...")
    parser = IndianAddressParser()
    if parser.addresses_df is None:
        print("Missing addresses.csv")
        return
    results = parser.parse_all_addresses()
    parser.export_results_json(results)

if __name__ == "__main__":
    main()
