#!/usr/bin/env python3
"""
Enhanced Indian Address Parser System
Parses unstructured Indian addresses into structured JSON format
Author: AI Assistant
Version: 2.0
"""

import pandas as pd
import re
import json
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

# Configure logging for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ParsedAddress:
    """Data class to store parsed address components"""
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
        """Convert to dictionary format"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

class IndianAddressParser:
    """
    Enhanced Indian Address Parser with rule-based approach
    Handles various address formats and extracts structured components
    """
    
    def __init__(self):
        """Initialize parser with datasets and patterns"""
        self.load_datasets()
        self.setup_patterns()
        self.setup_abbreviations()
        self.setup_state_mappings()
        
    def load_datasets(self):
        """Load PIN code and address datasets"""
        try:
            # Load addresses dataset
            self.addresses_df = pd.read_csv("addresses.csv")
            logger.info(f"Loaded {len(self.addresses_df)} addresses from CSV")
            
            # Load PIN code validation dataset
            self.pin_df = pd.read_csv("pincodes.csv")
            self.pin_df['Pincode'] = self.pin_df['Pincode'].astype(str)
            logger.info(f"Loaded {len(self.pin_df)} PIN codes from CSV")
            
            # Create PIN code lookup dictionary for faster access
            self.pin_lookup = {}
            for _, row in self.pin_df.iterrows():
                self.pin_lookup[row['Pincode']] = {
                    'city': row['City'],
                    'district': row['District'],
                    'state': row['State']
                }
                
        except FileNotFoundError as e:
            logger.error(f"Dataset file not found: {e}")
            self.addresses_df = None
            self.pin_df = None
            self.pin_lookup = {}
        except Exception as e:
            logger.error(f"Error loading datasets: {e}")
            raise
    
    def setup_patterns(self):
        """Setup regex patterns for address component extraction"""
        # PIN code pattern (6 digits)
        self.pin_pattern = re.compile(r'\b\d{6}\b')
        
        # Care-of patterns
        self.care_of_patterns = [
            re.compile(r'(?:s/o|son of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
            re.compile(r'(?:w/o|wife of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
            re.compile(r'(?:c/o|care of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
            re.compile(r'(?:d/o|daughter of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE)
        ]
        
        # House number patterns
        self.house_patterns = [
            re.compile(r'(?:h\.?\s*no\.?|house\s+no\.?|house\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
            re.compile(r'(?:plot\s+no\.?|plot\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
            re.compile(r'(?:door\s+no\.?|door\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
            re.compile(r'(?:flat\s+no\.?|flat\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
            re.compile(r'(?:shop\s+no\.?|shop\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
        ]
        
        # Landmark patterns
        self.landmark_patterns = [
            re.compile(r'(?:near|opp\.?|opposite)\s+([a-z0-9\s]+?)(?:,|$)', re.IGNORECASE),
            re.compile(r'(?:behind|beside|next to)\s+([a-z0-9\s]+?)(?:,|$)', re.IGNORECASE),
        ]
        
        # Locality/Sector patterns
        self.locality_patterns = [
            re.compile(r'(?:sector|sec\.?)\s*([0-9a-z\-]+)', re.IGNORECASE),
            re.compile(r'(?:phase|ph\.?)\s*([0-9a-z\-]+)', re.IGNORECASE),
            re.compile(r'(?:block|blk\.?)\s*([0-9a-z\-]+)', re.IGNORECASE),
            re.compile(r'(?:ward\s+no\.?)\s*([0-9]+)', re.IGNORECASE),
        ]
        
        # Village patterns
        self.village_patterns = [
            re.compile(r'(?:village|vill\.?|vil\.?)\s+([a-z\s]+?)(?:,|\s+post|$)', re.IGNORECASE),
            re.compile(r'(?:post\s+office|po\.?)\s+([a-z\s]+?)(?:,|\s+tehsil|$)', re.IGNORECASE),
        ]
        
        # District patterns
        self.district_patterns = [
            re.compile(r'(?:district|dist\.?)\s+([a-z\s]+?)(?:,|$)', re.IGNORECASE),
            re.compile(r'(?:tehsil)\s+([a-z\s]+?)(?:,|\s+dist|$)', re.IGNORECASE),
        ]
    
    def setup_abbreviations(self):
        """Setup abbreviation mappings for normalization"""
        self.abbreviations = {
            # Relationship abbreviations
            's/o': 'son of',
            'w/o': 'wife of',
            'c/o': 'care of',
            'd/o': 'daughter of',
            
            # Location abbreviations
            'rd': 'road',
            'st': 'street',
            'ave': 'avenue',
            'sec': 'sector',
            'ph': 'phase',
            'blk': 'block',
            'opp': 'opposite',
            'nr': 'near',
            
            # House/building abbreviations
            'h': 'house',
            'h.': 'house',
            'hno': 'house number',
            'h no': 'house number',
            'h.no': 'house number',
            'bldg': 'building',
            'apt': 'apartment',
            'flr': 'floor',
            
            # Administrative abbreviations
            'vill': 'village',
            'vil': 'village',
            'po': 'post office',
            'dist': 'district',
            'teh': 'tehsil',
            'sub': 'subdistrict',
            
            # Directional abbreviations
            'n': 'north',
            's': 'south',
            'e': 'east',
            'w': 'west',
            'ne': 'northeast',
            'nw': 'northwest',
            'se': 'southeast',
            'sw': 'southwest',
        }
    
    def setup_state_mappings(self):
        """Setup state name mappings for normalization"""
        self.state_mappings = {
            'up': 'Uttar Pradesh',
            'mp': 'Madhya Pradesh',
            'hp': 'Himachal Pradesh',
            'ap': 'Andhra Pradesh',
            'wb': 'West Bengal',
            'tn': 'Tamil Nadu',
            'ka': 'Karnataka',
            'kl': 'Kerala',
            'gj': 'Gujarat',
            'mh': 'Maharashtra',
            'rj': 'Rajasthan',
            'pb': 'Punjab',
            'hr': 'Haryana',
            'br': 'Bihar',
            'jh': 'Jharkhand',
            'or': 'Odisha',
            'as': 'Assam',
            'ml': 'Meghalaya',
            'mn': 'Manipur',
            'mz': 'Mizoram',
            'nl': 'Nagaland',
            'tr': 'Tripura',
            'ar': 'Arunachal Pradesh',
            'sk': 'Sikkim',
            'ga': 'Goa',
            'ut': 'Uttarakhand',
            'ch': 'Chhattisgarh',
            'ts': 'Telangana',
            'dl': 'Delhi',
            'ld': 'Lakshadweep',
            'an': 'Andaman and Nicobar Islands',
            'py': 'Puducherry',
            'jk': 'Jammu and Kashmir',
            'la': 'Ladakh',
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize address text by cleaning and expanding abbreviations"""
        if not text or pd.isna(text):
            return ""
        
        # Convert to string and lowercase
        text = str(text).lower().strip()
        
        # Remove extra punctuation but keep essential ones
        text = re.sub(r'[^\w\s,./\-()]', ' ', text)
        
        # Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Split concatenated words with numbers (e.g., "123abc" -> "123 abc")
        text = re.sub(r'(\d+)([a-z]+)', r'\1 \2', text)
        text = re.sub(r'([a-z]+)(\d+)', r'\1 \2', text)
        
        # Expand abbreviations
        words = text.split()
        expanded_words = []
        
        for word in words:
            # Clean word of punctuation for lookup
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.abbreviations:
                expanded_words.append(self.abbreviations[clean_word])
            else:
                expanded_words.append(word)
        
        return ' '.join(expanded_words).strip()
    
    def extract_pincode(self, text: str) -> Optional[str]:
        """Extract PIN code from address text"""
        match = self.pin_pattern.search(text)
        return match.group().strip() if match else None
    
    def extract_care_of(self, text: str) -> Optional[str]:
        """Extract care-of information from address"""
        for pattern in self.care_of_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip().title()
        return None
    
    def extract_house_number(self, text: str) -> Optional[str]:
        """Extract house number from address"""
        for pattern in self.house_patterns:
            match = pattern.search(text)
            if match:
                house_num = match.group(1).strip()
                # Clean house number
                house_num = re.sub(r'[^\w/\-]', '', house_num)
                return house_num if house_num else None
        return None
    
    def extract_landmark(self, text: str) -> Optional[str]:
        """Extract landmark information from address"""
        for pattern in self.landmark_patterns:
            match = pattern.search(text)
            if match:
                landmark = match.group(1).strip().title()
                # Clean up landmark
                landmark = re.sub(r'\s+', ' ', landmark)
                return landmark if len(landmark) > 2 else None
        return None
    
    def extract_locality_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract locality and street information"""
        locality = None
        street = None
        
        # Check for sector/phase/block patterns
        for pattern in self.locality_patterns:
            match = pattern.search(text)
            if match:
                locality_type = pattern.pattern.split('|')[0].replace('(?:', '').replace('\\s*', ' ')
                locality_value = match.group(1).strip()
                locality = f"{locality_type.title()} {locality_value}"
                break
        
        # Look for road/street patterns
        road_patterns = [
            re.compile(r'(?:road|rd)\s+([a-z0-9\s]+?)(?:,|$)', re.IGNORECASE),
            re.compile(r'(?:street|st)\s+([a-z0-9\s]+?)(?:,|$)', re.IGNORECASE),
            re.compile(r'([a-z\s]+?)\s+(?:road|rd)(?:,|$)', re.IGNORECASE),
        ]
        
        for pattern in road_patterns:
            match = pattern.search(text)
            if match:
                street = match.group(1).strip().title()
                break
        
        return locality, street
    
    def extract_village_info(self, text: str) -> Optional[str]:
        """Extract village information from address"""
        for pattern in self.village_patterns:
            match = pattern.search(text)
            if match:
                village = match.group(1).strip().title()
                return village if len(village) > 2 else None
        return None
    
    def extract_district_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract district and subdistrict information"""
        district = None
        subdistrict = None
        
        for pattern in self.district_patterns:
            match = pattern.search(text)
            if match:
                if 'tehsil' in pattern.pattern.lower():
                    subdistrict = match.group(1).strip().title()
                else:
                    district = match.group(1).strip().title()
        
        return district, subdistrict
    
    def extract_city_state(self, text: str, pincode: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Extract city and state information"""
        city = None
        state = None
        
        # First try to get from PIN code
        if pincode and pincode in self.pin_lookup:
            pin_data = self.pin_lookup[pincode]
            city = pin_data['city']
            state = pin_data['state']
            return city, state
        
        # Tokenize address by commas
        parts = [part.strip() for part in text.split(',')]
        
        # Look for state in the last few parts
        for part in reversed(parts[-3:]):  # Check last 3 parts
            part_clean = re.sub(r'\d+', '', part).strip()  # Remove digits
            part_clean = re.sub(r'\s+', ' ', part_clean)
            
            # Check for state abbreviations
            for abbr, full_name in self.state_mappings.items():
                if abbr == part_clean.lower() or full_name.lower() in part_clean.lower():
                    state = full_name
                    break
            
            if state:
                break
        
        # Look for city (usually second to last part if state is found)
        if len(parts) >= 2:
            potential_city = parts[-2].strip()
            potential_city = re.sub(r'\d+', '', potential_city).strip()
            if len(potential_city) > 1 and not any(x in potential_city.lower() for x in ['sector', 'phase', 'block']):
                city = potential_city.title()
        
        return city, state
    
    def validate_with_pincode(self, parsed: ParsedAddress) -> ParsedAddress:
        """Validate and enhance parsed address with PIN code data"""
        if not parsed.pincode or parsed.pincode not in self.pin_lookup:
            return parsed
        
        pin_data = self.pin_lookup[parsed.pincode]
        
        # Use PIN code data if parsed data is missing
        if not parsed.city:
            parsed.city = pin_data['city']
        if not parsed.district:
            parsed.district = pin_data['district']
        if not parsed.state:
            parsed.state = pin_data['state']
        
        return parsed
    
    def parse_address(self, address: str) -> ParsedAddress:
        """Main method to parse a single address"""
        if not address or pd.isna(address):
            return ParsedAddress()
        
        # Normalize the address text
        normalized = self.normalize_text(address)
        
        # Initialize parsed address object
        parsed = ParsedAddress()
        
        # Extract components using regex patterns
        parsed.pincode = self.extract_pincode(normalized)
        parsed.care_of = self.extract_care_of(normalized)
        parsed.house_number = self.extract_house_number(normalized)
        parsed.landmark = self.extract_landmark(normalized)
        parsed.village = self.extract_village_info(normalized)
        
        # Extract locality and street
        locality, street = self.extract_locality_info(normalized)
        parsed.locality = locality
        parsed.street = street
        
        # Extract district and subdistrict
        district, subdistrict = self.extract_district_info(normalized)
        parsed.district = district
        parsed.subdistrict = subdistrict
        
        # Extract city and state
        city, state = self.extract_city_state(normalized, parsed.pincode)
        parsed.city = city
        parsed.state = state
        
        # Validate and enhance with PIN code data
        parsed = self.validate_with_pincode(parsed)
        
        return parsed
    
    def print_table_header(self):
        """Print table header"""
        columns = ['ID', 'Care Of', 'House No', 'Building', 'Street', 'Locality', 'Landmark', 'City', 'Village', 'District', 'Subdistrict', 'State', 'Pincode']
        widths = [3, 15, 10, 15, 15, 15, 15, 15, 15, 15, 15, 15, 8]
        
        header = "|".join(f"{col:^{width}}" for col, width in zip(columns, widths))
        separator = "+".join("-" * width for width in widths)
        
        print(separator)
        print(header)
        print(separator)
    
    def print_table_row(self, address_id: int, parsed: ParsedAddress):
        """Print a single table row"""
        widths = [3, 15, 10, 15, 15, 15, 15, 15, 15, 15, 15, 15, 8]
        
        def truncate(text, width):
            if not text:
                return ""
            return text[:width-1] + "~" if len(text) >= width else text
        
        values = [
            str(address_id),
            truncate(parsed.care_of or "", widths[1]),
            truncate(parsed.house_number or "", widths[2]),
            truncate(parsed.building_name or "", widths[3]),
            truncate(parsed.street or "", widths[4]),
            truncate(parsed.locality or "", widths[5]),
            truncate(parsed.landmark or "", widths[6]),
            truncate(parsed.city or "", widths[7]),
            truncate(parsed.village or "", widths[8]),
            truncate(parsed.district or "", widths[9]),
            truncate(parsed.subdistrict or "", widths[10]),
            truncate(parsed.state or "", widths[11]),
            truncate(parsed.pincode or "", widths[12])
        ]
        
        row = "|".join(f"{val:<{width}}" for val, width in zip(values, widths))
        print(row)
    
    def parse_all_addresses(self) -> List[Dict]:
        """Parse all addresses from the dataset and return results"""
        if self.addresses_df is None:
            logger.error("No addresses dataset loaded")
            return []
        
        results = []
        total_addresses = len(self.addresses_df)
        
        print(f"Processing {total_addresses} addresses...")
        print()
        
        # Print table header
        self.print_table_header()
        
        for index, row in self.addresses_df.iterrows():
            original_address = row['address']
            
            # Parse the address
            parsed = self.parse_address(original_address)
            parsed_dict = parsed.to_dict()
            
            # Print table row
            self.print_table_row(index + 1, parsed)
            
            # Create result entry
            result = {
                'address_id': index + 1,
                'original_address': original_address,
                'parsed_components': parsed_dict
            }
            
            results.append(result)
        
        # Print table footer
        widths = [3, 15, 10, 15, 15, 15, 15, 15, 15, 15, 15, 15, 8]
        separator = "+".join("-" * width for width in widths)
        print(separator)
        
        return results
    
    def export_results_json(self, results: List[Dict], filename: str = "parsed_addresses.json"):
        """Export results to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results exported to {filename}")
        except Exception as e:
            logger.error(f"Error exporting results: {e}")


def main():
    """Main function to run the address parser"""
    try:
        # Initialize the parser
        print("Initializing Indian Address Parser...")
        parser = IndianAddressParser()
        
        # Check if datasets were loaded successfully
        if parser.addresses_df is None:
            print("Error: Could not load address dataset. Please ensure 'addresses.csv' exists.")
            return
        
        # Parse all addresses and display results
        results = parser.parse_all_addresses()
        
        if not results:
            print("No addresses were parsed successfully.")
            return
        
        # Ask user if they want to export results
        print()
        export_choice = input("Export results to JSON? (y/n): ").lower().strip()
        if export_choice in ['y', 'yes']:
            parser.export_results_json(results)
        
        print(f"Total addresses processed: {len(results)}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()