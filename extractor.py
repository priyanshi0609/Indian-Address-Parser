import re

# Define regex patterns
pin_pattern = re.compile(r'\b\d{6}\b')
care_of_patterns = [
    re.compile(r'(?:s/o|son of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
    re.compile(r'(?:w/o|wife of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
    re.compile(r'(?:c/o|care of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE),
    re.compile(r'(?:d/o|daughter of)\s+([a-z\s]+?)(?:,|\s+h\s|$)', re.IGNORECASE)
]
house_patterns = [
    re.compile(r'(?:h\.?\s*no\.?|house\s+no\.?|house\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
    re.compile(r'(?:plot\s+no\.?|plot\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
    re.compile(r'(?:door\s+no\.?|door\s+number)\s*[:\-]?\s*([a-z0-9/\-]+)', re.IGNORECASE),
]
landmark_patterns = [
    re.compile(r'(?:near|opp\.?|opposite)\s+([a-z0-9\s]+?)(?:,|$)', re.IGNORECASE),
]
locality_patterns = [
    re.compile(r'(?:sector|sec\.?)\s*([0-9a-z\-]+)', re.IGNORECASE),
]
village_patterns = [
    re.compile(r'(?:village|vill\.?)\s+([a-z\s]+?)(?:,|\s+post|$)', re.IGNORECASE),
]
district_patterns = [
    re.compile(r'(?:district|dist\.?)\s+([a-z\s]+?)(?:,|$)', re.IGNORECASE),
]

# Extraction functions
def extract_pincode(text): return pin_pattern.search(text).group().strip() if pin_pattern.search(text) else None
def extract_care_of(text): return next((p.search(text).group(1).strip().title() for p in care_of_patterns if p.search(text)), None)
def extract_house_number(text): return next((re.sub(r'[^\w/\-]', '', p.search(text).group(1).strip()) for p in house_patterns if p.search(text)), None)
def extract_landmark(text): return next((p.search(text).group(1).strip().title() for p in landmark_patterns if p.search(text)), None)
def extract_locality_info(text): return (f"Sector {m.group(1)}", None) if (m := locality_patterns[0].search(text)) else (None, None)
def extract_village_info(text): return next((p.search(text).group(1).strip().title() for p in village_patterns if p.search(text)), None)
def extract_district_info(text): return (m.group(1).strip().title(), None) if (m := district_patterns[0].search(text)) else (None, None)
