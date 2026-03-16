"""
config.py — Centralized configuration for the Indian Address Parser.
All tunable constants, thresholds, and logging live here.
"""

import logging
import sys
from pathlib import Path

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR  # CSVs sit next to the source files

ADDRESSES_CSV   = DATA_DIR / "addresses.csv"
PINCODES_CSV    = DATA_DIR / "pincodes.csv"
CITIES_CSV      = DATA_DIR / "Cities_Towns_District_State_India.csv"

# ──────────────────────────────────────────────
# Parser thresholds
# ──────────────────────────────────────────────
FUZZY_CITY_THRESHOLD   = 85   # minimum rapidfuzz score for city match
FUZZY_STATE_THRESHOLD  = 80   # minimum rapidfuzz score for state match

# Confidence weights (must sum to 1.0)
CONFIDENCE_WEIGHTS = {
    "pincode":  0.25,
    "city":     0.20,
    "state":    0.20,
    "house":    0.15,
    "locality": 0.10,
    "care_of":  0.05,
    "landmark": 0.05,
}

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "address_parser") -> logging.Logger:
    """
    Returns a logger that writes INFO+ to stdout and WARNING+ to stderr.
    Safe to call multiple times — won't duplicate handlers.
    """
    log = logging.getLogger(name)
    if log.handlers:
        return log  # already configured

    log.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    log.addHandler(stdout_handler)
    log.propagate = False
    return log


logger = setup_logger()