import pandas as pd
import re
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Load your address CSV
addresses_df = pd.read_csv("addresses.csv")

# Load PIN validation dataset (optional)
try:
    pin_df = pd.read_csv("pincodes.csv")
    pin_df['Pincode'] = pin_df['Pincode'].astype(str)
except:
    pin_df = None

# ---- Utility Functions ----

def normalize_address(address):
    address = str(address).lower()
    address = re.sub(r'[^\w\s/-]', ' ', address)  # Remove special chars
    address = re.sub(r'\s+', ' ', address)  # Remove multiple spaces

    abbr_dict = {
        'rd': 'road',
        'sec': 'sector',
        'ph': 'phase',
        'opp': 'opposite',
        'w/o': 'wife of',
        's/o': 'son of',
        'c/o': 'care of',
        'no': 'number',
        'h no': 'house number',
        'h.': 'house'
    }

    for k, v in abbr_dict.items():
        address = re.sub(rf'\b{k}\b', v, address)

    return address.strip()

def extract_pin(address):
    match = re.search(r'\b\d{6}\b', address)
    return match.group() if match else None

def extract_care_of(address):
    match = re.search(r'(son of|wife of|care of) [a-z ]+', address)
    return match.group() if match else None

def extract_landmark(address):
    match = re.search(r'(near|opposite) [a-z0-9 ]+', address)
    return match.group() if match else None

def extract_entities(address):
    doc = nlp(address)
    entities = {}
    for ent in doc.ents:
        if ent.label_ in ['GPE', 'LOC']:
            entities[ent.label_] = ent.text
    return entities

def validate_pin(pin_code):
    if pin_df is not None and pin_code:
        result = pin_df[pin_df['Pincode'] == pin_code]
        if not result.empty:
            row = result.iloc[0]
            return {
                'city_from_pin': row.get('City'),
                'district_from_pin': row.get('District'),
                'state_from_pin': row.get('State')
            }
    return {}

# ---- Main Processing Loop ----

parsed_data = []

for index, row in addresses_df.iterrows():
    original = row['address']
    normalized = normalize_address(original)
    pin_code = extract_pin(normalized)
    care_of = extract_care_of(normalized)
    landmark = extract_landmark(normalized)
    entities = extract_entities(normalized)
    validation = validate_pin(pin_code)

    parsed_data.append({
        'original_address': original,
        'normalized': normalized,
        'pin_code': pin_code,
        'care_of': care_of,
        'landmark': landmark,
        'entity_city_or_gpe': entities.get('GPE'),
        'entity_location': entities.get('LOC'),
        'city_from_pin': validation.get('city_from_pin'),
        'district_from_pin': validation.get('district_from_pin'),
        'state_from_pin': validation.get('state_from_pin')
    })

# ---- Output Result to CSV ----
parsed_df = pd.DataFrame(parsed_data)
parsed_df.to_csv("parsed_addresses_output.csv", index=False)
print("✅ Parsing complete. Results saved to parsed_addresses_output.csv")
