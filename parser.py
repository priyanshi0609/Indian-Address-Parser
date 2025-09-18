# Main IndianAddressParser class
from models import ParsedAddress
from utils import get_abbreviations, get_state_mappings, normalize_text
from extractor import *
from config import logger
from data_loader import load_datasets
import re

class IndianAddressParser:
    def __init__(self):
        self.addresses_df, _, self.city_lookup, self.pin_lookup = load_datasets()
        self.abbreviations = get_abbreviations()
        self.state_mappings = get_state_mappings()

    def extract_city_state(self, text: str, pincode: str = None):
        city = state = None
        
        # First try pincode lookup if available
        if pincode and pincode in self.pin_lookup:
            return self.pin_lookup[pincode]['city'], self.pin_lookup[pincode]['state']
        
        # Split by various delimiters
        words = re.split(r'[,\n\s\.]+', text.lower())
        words = [word.strip() for word in words if word.strip()]
        
        # Check for multi-word city names first (2-3 words)
        for i in range(len(words) - 2):
            three_word = ' '.join(words[i:i+3])
            two_word = ' '.join(words[i:i+2])
            
            if three_word in self.city_lookup:
                return three_word.title(), self.city_lookup[three_word]['state']
            if two_word in self.city_lookup:
                return two_word.title(), self.city_lookup[two_word]['state']
        
        # Check single words
        for token in words:
            if token in self.city_lookup:
                return token.title(), self.city_lookup[token]['state']
        
        return city, state

    def validate_with_pincode(self, parsed: ParsedAddress) -> ParsedAddress:
        if parsed.pincode and parsed.pincode in self.pin_lookup:
            pin_data = self.pin_lookup[parsed.pincode]
            parsed.city = parsed.city or pin_data['city']
            parsed.district = parsed.district or pin_data['district']
            parsed.state = parsed.state or pin_data['state']
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
        
        # Enhanced parsing for complex addresses without clear patterns
        if not parsed.house_number:
            parsed.house_number = extract_house_number_advanced(norm)
        if not parsed.locality:
            parsed.locality = extract_locality_advanced(norm, parsed)
        
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

# Enhanced extractor functions
import re

# Define regex patterns
pin_pattern = re.compile(r'\b\d{6}\b')
care_of_patterns = [
    re.compile(r'(?:s/o|son of)\s+([a-z\s]+?)(?:,|\s+|$)', re.IGNORECASE),
    re.compile(r'(?:w/o|wife of)\s+([a-z\s]+?)(?:,|\s+|$)', re.IGNORECASE),
    re.compile(r'(?:c/o|care of)\s+([a-z\s]+?)(?:,|\s+|$)', re.IGNORECASE),
    re.compile(r'(?:d/o|daughter of)\s+([a-z\s]+?)(?:,|\s+|$)', re.IGNORECASE)
]

# Enhanced house number patterns
house_patterns = [
    re.compile(r'(?:h\.?\s*no\.?|house\s+no\.?|house\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
    re.compile(r'(?:plot\s+no\.?|plot\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
    re.compile(r'(?:door\s+no\.?|door\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
    re.compile(r'\b(?:no\.?|number)\s+([a-z0-9/\-]+)', re.IGNORECASE),
]

# Patterns for addresses like "C160 92 I.P Extension"
advanced_house_patterns = [
    re.compile(r'\b([A-Z]?\d+[A-Z]?)\s+(\d+)\s+', re.IGNORECASE),  # C160 92
    re.compile(r'\b([A-Z]?\d+[A-Z]?/\d+)\b', re.IGNORECASE),  # C160/92
    re.compile(r'\b(\d+[A-Z]?-\d+[A-Z]?)\b', re.IGNORECASE),  # 160A-92B
    re.compile(r'\b([A-Z]\d+)\b', re.IGNORECASE),  # C160
]

landmark_patterns = [
    re.compile(r'(?:near|opp\.?|opposite|beside|next to|close to)\s+([a-z0-9\s\.]+?)(?:,|\s+|$)', re.IGNORECASE),
]

locality_patterns = [
    re.compile(r'(?:sector|sec\.?)\s*([0-9a-z\-]+)', re.IGNORECASE),
    re.compile(r'\b(?:street|st\.?|road|rd\.?|lane|ln\.?|colony|col\.?|extension|extn\.?)\s+([a-z0-9\s\.]+?)(?:,|\s+|$)', re.IGNORECASE),
]

village_patterns = [
    re.compile(r'(?:village|vill\.?)\s+([a-z\s]+?)(?:,|\s+post|\s+|$)', re.IGNORECASE),
    re.compile(r'\b(vill\.?|vlg\.?)\s*([a-z\s]+?)(?:,|\s+|$)', re.IGNORECASE),
]

district_patterns = [
    re.compile(r'(?:district|dist\.?)\s+([a-z\s]+?)(?:,|\s+|$)', re.IGNORECASE),
    re.compile(r'\b(dist\.?)\s*([a-z\s]+?)(?:,|\s+|$)', re.IGNORECASE),
]

# Extraction functions
def extract_pincode(text):
    match = pin_pattern.search(text)
    return match.group().strip() if match else None

def extract_care_of(text):
    for pattern in care_of_patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().title()
    return None

def extract_house_number(text):
    for pattern in house_patterns:
        match = pattern.search(text)
        if match:
            house_no = match.group(1) if len(match.groups()) > 0 else match.group(0)
            return re.sub(r'[^\w/\-]', '', house_no.strip())
    return None

def extract_house_number_advanced(text):
    """Extract house numbers from complex patterns like 'C160 92'"""
    for pattern in advanced_house_patterns:
        match = pattern.search(text)
        if match:
            # Combine matched groups for complex patterns
            if len(match.groups()) > 1:
                return ' '.join([g for g in match.groups() if g])
            else:
                return match.group(1)
    return None

def extract_landmark(text):
    for pattern in landmark_patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().title()
    return None

def extract_locality_info(text):
    # Try sector pattern first
    match = locality_patterns[0].search(text)
    if match:
        return f"Sector {match.group(1)}", None
    
    # Try street/road patterns
    for pattern in locality_patterns[1:]:
        match = pattern.search(text)
        if match:
            locality_name = match.group(1).strip().title()
            return locality_name, None
    
    return None, None

def extract_locality_advanced(text, parsed):
    """Advanced locality extraction for addresses like 'I.P Extension'"""
    # Remove already extracted components
    temp_text = text.lower()
    if parsed.house_number:
        temp_text = temp_text.replace(parsed.house_number.lower(), '')
    if parsed.pincode:
        temp_text = temp_text.replace(parsed.pincode, '')
    
    # Look for common locality indicators
    locality_indicators = ['extension', 'extn', 'colony', 'col', 'area', 'nagar', 'layout']
    words = re.split(r'[,\s\.]+', temp_text.strip())
    
    locality_parts = []
    for word in words:
        if word and word not in locality_indicators and not word.isdigit():
            locality_parts.append(word)
        elif word in locality_indicators:
            locality_parts.append(word)
    
    if locality_parts:
        return ' '.join(locality_parts).title()
    
    return None

def extract_village_info(text):
    for pattern in village_patterns:
        match = pattern.search(text)
        if match:
            if len(match.groups()) > 1:
                return match.group(2).strip().title() if match.group(2) else match.group(1).strip().title()
            else:
                return match.group(1).strip().title()
    return None

def extract_district_info(text):
    for pattern in district_patterns:
        match = pattern.search(text)
        if match:
            if len(match.groups()) > 1:
                return match.group(2).strip().title() if match.group(2) else match.group(1).strip().title(), None
            else:
                return match.group(1).strip().title(), None
    return None, None