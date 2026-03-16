"""
utils.py — Text normalisation helpers for the Indian Address Parser.

Key responsibilities
────────────────────
1. Expand abbreviations (s/o → son of, rd → road, …)
2. Inject spaces into CamelCase / stuck tokens  (237okhlaphase3 → 237 okhla phase 3)
3. Strip noise (excessive punctuation, unicode junk)
4. Standardise state codes  (UP → Uttar Pradesh)
"""

from __future__ import annotations

import re
from typing import Dict


# ──────────────────────────────────────────────────────────────────────────────
# Static reference data
# ──────────────────────────────────────────────────────────────────────────────

def get_abbreviations() -> Dict[str, str]:
    """
    Maps lowercase abbreviated tokens → full forms.
    Keys must NOT contain punctuation (punctuation is stripped before lookup).
    """
    return {
        # Care-of markers
        "so":   "son of",
        "wo":   "wife of",
        "co":   "care of",
        "do":   "daughter of",
        "ho":   "husband of",

        # Road / Street
        "rd":   "road",
        "st":   "street",
        "ave":  "avenue",
        "blvd": "boulevard",
        "marg": "marg",

        # Locality
        "nagar": "nagar",
        "sec":   "sector",
        "ph":    "phase",
        "extn":  "extension",
        "ext":   "extension",
        "encl":  "enclave",
        "col":   "colony",
        "soc":   "society",
        "appt":  "apartment",
        "apts":  "apartments",
        "apt":   "apartment",

        # House / Plot
        "hno":   "house number",
        "hno":   "house number",   # alias
        "hn":    "house number",
        "no":    "number",
        "plt":   "plot",

        # Village / Post
        "vill":  "village",
        "vlg":   "village",
        "po":    "post office",
        "ps":    "police station",
        "po":    "post office",

        # Administrative
        "dist":  "district",
        "distt": "district",
        "subdist": "subdistrict",
        "tehsil": "tehsil",
        "tal":   "taluka",

        # Landmark
        "opp":   "opposite",
        "nr":    "near",
        "adj":   "adjacent",

        # Generic
        "bldg":  "building",
        "blk":   "block",
        "flr":   "floor",
        "fl":    "floor",
    }


def get_state_mappings() -> Dict[str, str]:
    """Maps common state abbreviations / codes → official full names."""
    return {
        # Two-letter postal codes
        "an": "Andaman and Nicobar Islands",
        "ap": "Andhra Pradesh",
        "ar": "Arunachal Pradesh",
        "as": "Assam",
        "br": "Bihar",
        "cg": "Chhattisgarh",
        "ch": "Chandigarh",
        "dd": "Dadra and Nagar Haveli and Daman and Diu",
        "dl": "Delhi",
        "ga": "Goa",
        "gj": "Gujarat",
        "hp": "Himachal Pradesh",
        "hr": "Haryana",
        "jh": "Jharkhand",
        "jk": "Jammu and Kashmir",
        "ka": "Karnataka",
        "kl": "Kerala",
        "la": "Ladakh",
        "ld": "Lakshadweep",
        "mh": "Maharashtra",
        "ml": "Meghalaya",
        "mn": "Manipur",
        "mp": "Madhya Pradesh",
        "mz": "Mizoram",
        "nl": "Nagaland",
        "od": "Odisha",
        "or": "Odisha",     # legacy code
        "pb": "Punjab",
        "py": "Puducherry",
        "rj": "Rajasthan",
        "sk": "Sikkim",
        "tg": "Telangana",
        "tn": "Tamil Nadu",
        "tr": "Tripura",
        "ts": "Telangana",  # alternate
        "uk": "Uttarakhand",
        "up": "Uttar Pradesh",
        "wb": "West Bengal",

        # Common colloquial / long-form aliases
        "uttarpradesh": "Uttar Pradesh",
        "maharashtra":  "Maharashtra",
        "tamilnadu":    "Tamil Nadu",
        "westbengal":   "West Bengal",
        "madhyapradesh": "Madhya Pradesh",
    }


# ──────────────────────────────────────────────────────────────────────────────
# CamelCase / stuck-token splitter
# ──────────────────────────────────────────────────────────────────────────────

_CAMEL_RE = re.compile(
    r'(?<=[a-z])(?=[A-Z])'          # lowercase → uppercase boundary
    r'|(?<=[A-Z])(?=[A-Z][a-z])'    # consecutive caps boundary
    r'|(?<=[a-zA-Z])(?=\d)'         # letter → digit
    r'|(?<=\d)(?=[a-zA-Z])'         # digit → letter
)


def split_stuck_tokens(text: str) -> str:
    """
    Inserts spaces at letter↔digit and camelCase boundaries.

    Example:
        '237okhlaphase3'  →  '237 okhla phase 3'
        'NewDelhi110001'  →  'New Delhi 110001'
    """
    return _CAMEL_RE.sub(' ', text)


# ──────────────────────────────────────────────────────────────────────────────
# Main normalisation pipeline
# ──────────────────────────────────────────────────────────────────────────────

def normalize_text(text: str, abbreviations: Dict[str, str]) -> str:
    """
    Full normalisation pipeline:

    1. Lower-case
    2. Split stuck tokens  (digit↔letter, camelCase)
    3. Remove noise characters
    4. Normalise separators
    5. Expand abbreviations word-by-word
    6. Collapse whitespace

    Returns the normalised string (still lower-case; callers title-case as needed).
    """
    if not text:
        return ""

    text = str(text).strip()

    # 1. Split stuck tokens BEFORE lower-casing so camelCase works
    text = split_stuck_tokens(text)

    # 2. Lower-case
    text = text.lower()

    # 3. Normalise common Unicode / transliteration noise
    text = text.replace("–", "-").replace("—", "-")

    # 4. Remove characters that aren't alphanumeric, space, comma, dot, slash, hyphen, parentheses
    text = re.sub(r'[^\w\s,./\-()\u0900-\u097F]', ' ', text)

    # 5. Normalise repeated punctuation
    text = re.sub(r',+', ',', text)
    text = re.sub(r'\.+', '.', text)
    text = re.sub(r'-+', '-', text)

    # 6. Expand abbreviations
    words = text.split()
    expanded = []
    for word in words:
        # Strip leading/trailing punctuation for lookup, keep original if no match
        clean = re.sub(r'[^\w]', '', word)
        expanded.append(abbreviations.get(clean, word))

    # 7. Collapse whitespace
    return re.sub(r'\s+', ' ', ' '.join(expanded)).strip()


def title_case_smart(text: str) -> str:
    """
    Title-cases a string while keeping small conjunctions / prepositions lower.
    E.g. "son of ram singh" → "Son of Ram Singh"
    """
    LOWER_WORDS = {"of", "the", "and", "in", "at", "near", "opp", "via"}
    words = text.split()
    result = []
    for i, w in enumerate(words):
        result.append(w if (i > 0 and w in LOWER_WORDS) else w.capitalize())
    return ' '.join(result)