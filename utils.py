# Helper regex setup and normalization
import re
import pandas as pd

def get_abbreviations():
    return {
        's/o': 'son of', 'w/o': 'wife of', 'c/o': 'care of', 'd/o': 'daughter of',
        'rd': 'road', 'st': 'street', 'sec': 'sector', 'ph': 'phase',
        'h.no': 'house number', 'vill': 'village', 'po': 'post office', 'dist': 'district'
    }

def get_state_mappings():
    return {
        'up': 'Uttar Pradesh', 'mh': 'Maharashtra', 'dl': 'Delhi', 'ka': 'Karnataka',
        'tn': 'Tamil Nadu', 'rj': 'Rajasthan', 'br': 'Bihar', 'gj': 'Gujarat'
    }

def normalize_text(text: str, abbreviations: dict) -> str:
    if not text or pd.isna(text): return ""
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s,./\-()]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    words = text.split()
    expanded = [abbreviations.get(re.sub(r'[^\w]', '', w), w) for w in words]
    return ' '.join(expanded).strip()
