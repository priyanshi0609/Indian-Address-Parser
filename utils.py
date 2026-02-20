# utils.py
import re
from rapidfuzz import process, fuzz


def get_abbreviations():
    return {
        's/o': 'son of',
        'w/o': 'wife of',
        'c/o': 'care of',
        'd/o': 'daughter of',
        'rd': 'road',
        'st': 'street',
        'sec': 'sector',
        'ph': 'phase',
        'h.no': 'house number',
        'hno': 'house number',
        'vill': 'village',
        'vlg': 'village',
        'po': 'post office',
        'dist': 'district'
    }


def get_state_mappings():
    return {
        'up': 'Uttar Pradesh',
        'mh': 'Maharashtra',
        'dl': 'Delhi',
        'ka': 'Karnataka',
        'tn': 'Tamil Nadu',
        'rj': 'Rajasthan',
        'br': 'Bihar',
        'gj': 'Gujarat'
    }


def normalize_text(text: str, abbreviations: dict) -> str:
    """
    Strong normalization pipeline for noisy Indian addresses.
    """

    if not text:
        return ""

    text = str(text).lower().strip()

    # Remove unwanted special characters
    text = re.sub(r'[^\w\s,./\-()]', ' ', text)

    # Normalize commas
    text = re.sub(r',+', ',', text)

    # Normalize spaces
    text = re.sub(r'\s+', ' ', text)

    # Expand abbreviations
    words = text.split()
    expanded_words = []

    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        expanded_words.append(abbreviations.get(clean_word, word))

    normalized = ' '.join(expanded_words).strip()

    return normalized