"""
models.py — Data models for the Indian Address Parser.

ParsedAddress is used internally (dataclass) and also exposed
as a Pydantic schema for the FastAPI layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Internal dataclass  (used by parser / extractor logic)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ParsedAddress:
    # Relational / Care-of
    care_of: Optional[str]      = None

    # Physical location hierarchy
    house_number:  Optional[str] = None
    building_name: Optional[str] = None
    street:        Optional[str] = None
    locality:      Optional[str] = None
    landmark:      Optional[str] = None
    village:       Optional[str] = None
    subdistrict:   Optional[str] = None
    district:      Optional[str] = None
    city:          Optional[str] = None
    state:         Optional[str] = None
    pincode:       Optional[str] = None

    # Quality metadata
    confidence_score:   float      = 0.0
    validation_errors:  List[str]  = field(default_factory=list)
    match_method:       str        = "none"   # "pincode", "exact", "fuzzy", "none"

    # ── serialisation ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        """
        Serialise to dict.
        • Always includes metadata fields.
        • Skips address fields that are None (keeps response clean).
        • Returns fields in a logical geographic order.
        """
        ADDRESS_FIELDS_ORDER = [
            "care_of", "house_number", "building_name", "street",
            "locality", "landmark", "village", "subdistrict",
            "district", "city", "state", "pincode",
        ]
        META_FIELDS = {"confidence_score", "validation_errors", "match_method"}

        result: Dict = {}

        for key in ADDRESS_FIELDS_ORDER:
            val = getattr(self, key)
            if val is not None:
                result[key] = val

        for key in META_FIELDS:
            result[key] = getattr(self, key)

        return result


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic request / response schemas  (used by FastAPI)
# ──────────────────────────────────────────────────────────────────────────────

class AddressRequest(BaseModel):
    address: str = Field(
        ...,
        min_length=5,
        max_length=500,
        examples=["S/O Ram Singh, H No 15/1 Near City Mall, Indira Nagar, Lucknow, UP - 226016"],
        description="Raw unstructured Indian address string.",
    )


class BulkAddressRequest(BaseModel):
    addresses: List[str] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="List of raw address strings (max 500 per request).",
    )


class ParsedAddressResponse(BaseModel):
    care_of:        Optional[str] = None
    house_number:   Optional[str] = None
    building_name:  Optional[str] = None
    street:         Optional[str] = None
    locality:       Optional[str] = None
    landmark:       Optional[str] = None
    village:        Optional[str] = None
    subdistrict:    Optional[str] = None
    district:       Optional[str] = None
    city:           Optional[str] = None
    state:          Optional[str] = None
    pincode:        Optional[str] = None
    confidence_score: float       = 0.0
    validation_errors: List[str]  = []
    match_method:   str           = "none"


class SingleParseResponse(BaseModel):
    original: str
    parsed:   ParsedAddressResponse


class BulkParseResponse(BaseModel):
    total:   int
    results: List[SingleParseResponse]


class HealthResponse(BaseModel):
    status:      str
    version:     str
    datasets_ok: bool