"""
data_loader.py — Loads and indexes reference datasets.

Datasets used
─────────────
1. addresses.csv          — sample addresses for bulk parsing / evaluation
2. pincodes.csv           — PIN code → city / district / state mapping
3. Cities_Towns_…_India.csv — city / town → district / state mapping

All lookups are returned as plain dicts for O(1) access.
DataFrames are also returned for callers that want to iterate rows.

Performance note
────────────────
Datasets are typically loaded once (inside IndianAddressParser.__init__).
For production, wrap with an LRU cache or a singleton pattern.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from config import ADDRESSES_CSV, CITIES_CSV, PINCODES_CSV, logger


# ──────────────────────────────────────────────────────────────────────────────
# Type aliases
# ──────────────────────────────────────────────────────────────────────────────

CityLookup = Dict[str, Dict[str, str]]   # city_lower → {district, state}
PinLookup  = Dict[str, Dict[str, str]]   # pincode    → {city, district, state}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe_str(val: Any) -> str:
    return str(val).strip() if pd.notna(val) else ""


def _clean_col(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from all column names."""
    df.columns = [c.strip() for c in df.columns]
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Loaders
# ──────────────────────────────────────────────────────────────────────────────

def _load_addresses(path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, dtype=str)
        df = _clean_col(df)
        # Ensure there is an 'address' column regardless of original name
        for candidate in ("address", "Address", "raw_address", "text"):
            if candidate in df.columns:
                df.rename(columns={candidate: "address"}, inplace=True)
                break
        logger.info(f"Loaded {len(df)} sample addresses from '{path.name}'.")
        return df
    except FileNotFoundError:
        logger.warning(f"addresses.csv not found at '{path}'. Bulk parsing will be unavailable.")
        return pd.DataFrame(columns=["address"])
    except Exception as exc:
        logger.error(f"Failed to load addresses: {exc}")
        return pd.DataFrame(columns=["address"])


def _load_pincodes(path) -> Tuple[pd.DataFrame, PinLookup]:
    """
    Expects columns: Pincode, City, District, State
    Returns (dataframe, lookup_dict).
    """
    try:
        df = pd.read_csv(path, dtype=str)
        df = _clean_col(df)
        df["Pincode"] = df["Pincode"].str.strip()

        lookup: PinLookup = {}
        for _, row in df.iterrows():
            pin = _safe_str(row.get("Pincode", ""))
            if len(pin) == 6 and pin.isdigit():
                lookup[pin] = {
                    "city":     _safe_str(row.get("City",     "")).title(),
                    "district": _safe_str(row.get("District", "")).title(),
                    "state":    _safe_str(row.get("State",    "")).title(),
                }

        logger.info(f"Loaded {len(lookup):,} PIN codes from '{path.name}'.")
        return df, lookup

    except FileNotFoundError:
        logger.warning(f"pincodes.csv not found at '{path}'. PIN-based lookup disabled.")
        return pd.DataFrame(), {}
    except Exception as exc:
        logger.error(f"Failed to load pincodes: {exc}")
        return pd.DataFrame(), {}


def _load_cities(path) -> CityLookup:
    """
    Expects columns: City/Town, District, State/Union territory*
    Returns lookup keyed by lower-case city name.
    """
    try:
        df = pd.read_csv(path, dtype=str)
        df = _clean_col(df)

        # Flexible column resolution
        city_col  = next((c for c in df.columns if re.search(r'city|town', c, re.I)), None)
        dist_col  = next((c for c in df.columns if re.search(r'district', c, re.I)), None)
        state_col = next((c for c in df.columns if re.search(r'state|territory', c, re.I)), None)

        if not all([city_col, dist_col, state_col]):
            logger.warning("Cities CSV has unexpected columns — city lookup disabled.")
            return {}

        df.dropna(subset=[city_col, dist_col, state_col], inplace=True)

        lookup: CityLookup = {}
        for _, row in df.iterrows():
            city  = _safe_str(row[city_col]).lower()
            dist  = _safe_str(row[dist_col]).title()
            state = _safe_str(row[state_col]).title()
            if city:
                lookup[city] = {"district": dist, "state": state}

        logger.info(f"Loaded {len(lookup):,} cities/towns from '{path.name}'.")
        return lookup

    except FileNotFoundError:
        logger.warning(f"Cities CSV not found at '{path}'. City lookup disabled.")
        return {}
    except Exception as exc:
        logger.error(f"Failed to load cities: {exc}")
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def load_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, CityLookup, PinLookup]:
    """
    Load all reference datasets.

    Returns
    ───────
    addresses_df : DataFrame   — sample addresses
    pin_df       : DataFrame   — raw PIN code table
    city_lookup  : dict        — city_lower → {district, state}
    pin_lookup   : dict        — pincode    → {city, district, state}
    """
    addresses_df          = _load_addresses(ADDRESSES_CSV)
    pin_df, pin_lookup    = _load_pincodes(PINCODES_CSV)
    city_lookup           = _load_cities(CITIES_CSV)

    datasets_ok = bool(city_lookup) or bool(pin_lookup)
    if not datasets_ok:
        logger.warning("No reference datasets loaded — accuracy will be significantly reduced.")

    return addresses_df, pin_df, city_lookup, pin_lookup