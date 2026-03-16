"""
extractor.py — Regex-based field extraction for Indian addresses.

Each public function accepts a *normalised* (lower-case) address string
and returns the extracted value (str) or None.

Design principles
─────────────────
• Every pattern is named and documented.
• Functions never raise — they return None on failure.
• Patterns are compiled once at module load for performance.
• All returned strings are title-cased by the helpers in utils.py.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from utils import title_case_smart

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

_F = re.IGNORECASE | re.UNICODE


def _first_match(patterns: list[re.Pattern], text: str, group: int = 1) -> Optional[str]:
    """Return the first non-empty capture group from any pattern, or None."""
    for pat in patterns:
        m = pat.search(text)
        if m:
            val = m.group(group).strip(" ,.-")
            if val:
                return title_case_smart(val)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# PIN CODE
# ──────────────────────────────────────────────────────────────────────────────

_PIN_PATTERNS = [
    # Explicit prefix:  "pin 226016" / "pin: 226016" / "pincode - 226016"
    re.compile(r'\bpin(?:code)?\s*[:\-]?\s*(\d{6})\b', _F),
    # Preceded by dash/hyphen:  "UP - 226016"  or  "- 226016"
    re.compile(r'[-–]\s*(\d{6})\b', _F),
    # Bare 6-digit block (must be word-bounded so it doesn't match phone numbers)
    re.compile(r'\b(\d{6})\b'),
]


def extract_pincode(text: str) -> Optional[str]:
    """Extract a valid 6-digit Indian PIN code."""
    for pat in _PIN_PATTERNS:
        m = pat.search(text)
        if m:
            pin = m.group(1).strip()
            if len(pin) == 6 and pin.isdigit():
                return pin
    return None


# ──────────────────────────────────────────────────────────────────────────────
# CARE-OF  (S/O, W/O, C/O, D/O, H/O …)
# ──────────────────────────────────────────────────────────────────────────────

_CARE_OF_PATTERNS = [
    # "s/o ram singh"  /  "son of ram singh"
    re.compile(r'\b(?:s/o|son of)\s+([a-z][a-z\s\.]{2,40}?)(?:,|\s+h(?:ouse)?\s|\s+plot|\s+near|\s+opp|$)', _F),
    re.compile(r'\b(?:w/o|wife of)\s+([a-z][a-z\s\.]{2,40}?)(?:,|\s+h(?:ouse)?\s|\s+plot|\s+near|\s+opp|$)', _F),
    re.compile(r'\b(?:c/o|care of)\s+([a-z][a-z\s\.]{2,40}?)(?:,|\s+h(?:ouse)?\s|\s+plot|\s+near|\s+opp|$)', _F),
    re.compile(r'\b(?:d/o|daughter of)\s+([a-z][a-z\s\.]{2,40}?)(?:,|\s+h(?:ouse)?\s|\s+plot|\s+near|\s+opp|$)', _F),
    re.compile(r'\b(?:h/o|husband of)\s+([a-z][a-z\s\.]{2,40}?)(?:,|\s+h(?:ouse)?\s|\s+plot|\s+near|\s+opp|$)', _F),
    re.compile(r'\b(?:f/o|father of)\s+([a-z][a-z\s\.]{2,40}?)(?:,|\s+h(?:ouse)?\s|\s+plot|\s+near|\s+opp|$)', _F),
    re.compile(r'\b(?:m/o|mother of)\s+([a-z][a-z\s\.]{2,40}?)(?:,|\s+h(?:ouse)?\s|\s+plot|\s+near|\s+opp|$)', _F),
]


def extract_care_of(text: str) -> Optional[str]:
    return _first_match(_CARE_OF_PATTERNS, text)


# ──────────────────────────────────────────────────────────────────────────────
# HOUSE / FLAT / PLOT NUMBER
# ──────────────────────────────────────────────────────────────────────────────

_HOUSE_PATTERNS = [
    # "H No 15/1"  /  "H.No. 15A"  /  "House No: 3B"
    re.compile(r'\bh(?:ouse)?\.?\s*no\.?\s*[:\-]?\s*([a-z0-9][a-z0-9/\-]*)', _F),
    # "House Number 42"
    re.compile(r'\bhouse\s+number\s+([a-z0-9][a-z0-9/\-]*)', _F),
    # "Plot No 7"  /  "Plot Number 7/A"
    re.compile(r'\bplot\s*no\.?\s*[:\-]?\s*([a-z0-9][a-z0-9/\-]*)', _F),
    # "Door No 23"
    re.compile(r'\bdoor\s*no\.?\s*[:\-]?\s*([a-z0-9][a-z0-9/\-]*)', _F),
    # "Flat No 4B"  /  "Flat 4B"
    re.compile(r'\bflat\s*no\.?\s*[:\-]?\s*([a-z0-9][a-z0-9/\-]*)', _F),
    # "Room No 12"
    re.compile(r'\broom\s*no\.?\s*[:\-]?\s*([a-z0-9][a-z0-9/\-]*)', _F),
    # "Khasra No 452/3"
    re.compile(r'\bkhasra\s*no\.?\s*[:\-]?\s*([0-9][0-9/\-]*)', _F),
    # "Gali No 4"  /  "Gali 4"
    re.compile(r'\bgali\s+(?:no\.?\s*)?([0-9]+)', _F),
]


def extract_house_number(text: str) -> Optional[str]:
    for pat in _HOUSE_PATTERNS:
        m = pat.search(text)
        if m:
            val = re.sub(r'[^\w/\-]', '', m.group(1)).upper()
            if val:
                return val
    return None


# ──────────────────────────────────────────────────────────────────────────────
# BUILDING NAME
# ──────────────────────────────────────────────────────────────────────────────

_BUILDING_PATTERNS = [
    re.compile(r'\b(?:building|bldg|tower)\s+([a-z0-9][a-z0-9\s\-\.]{1,40}?)(?:,|$)', _F),
    re.compile(r'\b([a-z0-9][a-z0-9\s\-\.]{2,30}?)\s+(?:apartment|apartments|apts|residency|complex|heights|plaza|arcade|mansion|towers)(?:\s|,|$)', _F),
    re.compile(r'\b([a-z0-9][a-z0-9\s\-\.]{2,30}?)\s+(?:society|soc)(?:\s|,|$)', _F),
]


def extract_building_name(text: str) -> Optional[str]:
    return _first_match(_BUILDING_PATTERNS, text)


# ──────────────────────────────────────────────────────────────────────────────
# LANDMARK
# ──────────────────────────────────────────────────────────────────────────────

_LANDMARK_PATTERNS = [
    # "Near City Mall"  /  "Opp. Apollo Hospital"  /  "Opposite Metro Station"
    re.compile(r'\b(?:near|opp(?:osite)?\.?|adj(?:acent)?\.?|beside|behind|in front of|next to)\s+([a-z0-9][a-z0-9\s\-\.]{2,50}?)(?:,|\.|$)', _F),
    # "Landmark: Apollo Hospital"
    re.compile(r'\blandmark\s*[:\-]\s*([a-z0-9][a-z0-9\s\-\.]{2,50}?)(?:,|$)', _F),
]


def extract_landmark(text: str) -> Optional[str]:
    return _first_match(_LANDMARK_PATTERNS, text)


# ──────────────────────────────────────────────────────────────────────────────
# LOCALITY + STREET  (returns a tuple)
# ──────────────────────────────────────────────────────────────────────────────

_LOCALITY_PATTERNS = [
    # Sector / Block patterns
    re.compile(r'\bsector\s*([0-9a-z\-]+)', _F),
    re.compile(r'\bblock\s+([a-z0-9]\b[a-z0-9\s\-]{0,20}?)(?:,|$)', _F),
    re.compile(r'\bphase\s+([0-9ivxlc]+)', _F),
]

_STREET_PATTERNS = [
    # "12 Main Road" / "Nehru Marg" / "MG Road"
    re.compile(r'([a-z][a-z\s\-\.]{2,40}?)\s+(?:road|marg|street|lane|avenue|path|bypass|highway|nagar road)(?:\s|,|$)', _F),
    # "Street 5"
    re.compile(r'\bstreet\s+([0-9]+)', _F),
]


def extract_locality_info(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns (locality, street)."""
    locality = None
    street   = None

    # Sector / Block / Phase → locality
    for pat in _LOCALITY_PATTERNS:
        m = pat.search(text)
        if m:
            locality = title_case_smart(pat.pattern.split(r'\b')[1].split('\\')[0].strip() + ' ' + m.group(1).strip())
            break

    # Named road → street
    street = _first_match(_STREET_PATTERNS, text)

    return locality, street


# ──────────────────────────────────────────────────────────────────────────────
# VILLAGE
# ──────────────────────────────────────────────────────────────────────────────

_VILLAGE_PATTERNS = [
    re.compile(r'\b(?:village|vill(?:age)?\.?|gram|gaon)\s+([a-z][a-z\s]{2,40}?)(?:,|\s+post|\s+po\b|\s+block|\s+dist|$)', _F),
]


def extract_village_info(text: str) -> Optional[str]:
    return _first_match(_VILLAGE_PATTERNS, text)


# ──────────────────────────────────────────────────────────────────────────────
# DISTRICT + SUBDISTRICT
# ──────────────────────────────────────────────────────────────────────────────

_DISTRICT_PATTERNS = [
    re.compile(r'\b(?:district|dist(?:t)?\.?)\s+([a-z][a-z\s]{2,40}?)(?:,|$)', _F),
    re.compile(r'\b(?:zila|zilla)\s+([a-z][a-z\s]{2,40}?)(?:,|$)', _F),
]

_SUBDISTRICT_PATTERNS = [
    re.compile(r'\b(?:tehsil|taluka|tal\.?|mandal|block)\s+([a-z][a-z\s]{2,40}?)(?:,|$)', _F),
    re.compile(r'\b(?:subdistrict|sub-district|sub district)\s+([a-z][a-z\s]{2,40}?)(?:,|$)', _F),
]


def extract_district_info(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns (district, subdistrict)."""
    district    = _first_match(_DISTRICT_PATTERNS, text)
    subdistrict = _first_match(_SUBDISTRICT_PATTERNS, text)
    return district, subdistrict


# ──────────────────────────────────────────────────────────────────────────────
# STATE  (from text, not from PIN code)
# ──────────────────────────────────────────────────────────────────────────────

_STATE_INLINE_PATTERNS = [
    # "State: Maharashtra"
    re.compile(r'\bstate\s*[:\-]\s*([a-z][a-z\s]{2,40}?)(?:,|\.|$)', _F),
]


def extract_state_from_text(text: str, state_mappings: dict) -> Optional[str]:
    """
    Try to find a state reference directly in the text.
    Handles both full names and 2-letter codes.
    """
    # Inline "state: XYZ"
    val = _first_match(_STATE_INLINE_PATTERNS, text)
    if val:
        return val

    # Two-letter state codes that appear as standalone tokens
    words = re.split(r'[\s,./\-]+', text.lower())
    for word in words:
        clean = re.sub(r'[^\w]', '', word)
        if clean in state_mappings:
            return state_mappings[clean]

    return None


# ──────────────────────────────────────────────────────────────────────────────
# LOCALITY INFERENCE FROM LEFTOVER TOKENS
# ──────────────────────────────────────────────────────────────────────────────

def infer_locality_from_tokens(
    text: str,
    known_values: set,
    skip_tokens: set,
) -> Optional[str]:
    """
    After all explicit extractors have run, scan comma-separated segments
    and return the first segment that:
      1. Is not a known field value (city, district, state, pincode …)
      2. Does not start with a skip-word (near, opp, son of …)
      3. Is not purely numeric (e.g. the PIN code itself)
      4. Has at least 3 characters

    This catches locality names like "Shahdara", "Lajpat Nagar",
    "Andheri West" that users write without any keyword prefix.

    Example
    ───────
    Input:  "near durga mandir, shahdara, 110032"
    known_values = {"delhi", "east delhi", "110032"}
    skip_tokens  = {"near", "opp", ...}

    Segments after split: ["near durga mandir", "shahdara", "110032"]
    • "near durga mandir" → starts with skip-word "near" → skip
    • "shahdara"          → not in known_values, not a skip-word → ✅ LOCALITY
    • "110032"            → purely numeric → skip
    """
    # Split on commas (primary separator) and newlines
    segments = re.split(r'[,\n]+', text)

    for seg in segments:
        seg = seg.strip(" .-")
        if not seg or len(seg) < 3:
            continue

        # Skip purely numeric segments (PIN code, house numbers with no letters)
        if re.fullmatch(r'[\d\s/\-]+', seg):
            continue

        # Skip segments whose first word is a known skip-token or known value
        first_word = seg.split()[0].lower() if seg.split() else ""
        if first_word in skip_tokens:
            continue

        seg_lower = seg.lower().strip()

        # Skip if this segment IS one of the already-resolved values
        if seg_lower in known_values:
            continue

        # Skip if the segment contains a resolved value as a substring
        # (e.g. "delhi 110032" when city=Delhi)
        if any(kv and kv in seg_lower for kv in known_values):
            continue

        # Skip single-character tokens
        words_in_seg = [w for w in seg.split() if w.strip()]
        if len(words_in_seg) == 1 and len(words_in_seg[0]) <= 2:
            continue

        # This is our best candidate for locality
        return title_case_smart(seg_lower)

    return None