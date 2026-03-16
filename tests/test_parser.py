"""
tests/test_parser.py — Unit + integration tests for the Indian Address Parser.

Run with:
    pytest tests/ -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# ─── Module under test ────────────────────────────────────────────────────────
from extractor import (
    extract_care_of,
    extract_house_number,
    extract_landmark,
    extract_pincode,
    extract_village_info,
    extract_district_info,
    extract_building_name,
)
from utils import normalize_text, split_stuck_tokens, get_abbreviations
from parser import IndianAddressParser
from main import app

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def parser():
    return IndianAddressParser()


ABBRS = get_abbreviations()


# ──────────────────────────────────────────────────────────────────────────────
# utils.py tests
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalization:
    def test_basic_lowercasing(self):
        assert normalize_text("LUCKNOW", ABBRS) == "lucknow"

    def test_abbreviation_expansion(self):
        result = normalize_text("H.No 15 Sec 4 Ph 2 dist Lucknow", ABBRS)
        assert "house number" in result
        assert "sector" in result
        assert "phase" in result
        assert "district" in result

    def test_stuck_token_split(self):
        result = split_stuck_tokens("237okhlaphase3")
        assert "237" in result
        assert "okhla" in result.lower()
        assert "phase" in result.lower()
        assert "3" in result

    def test_empty_string(self):
        assert normalize_text("", ABBRS) == ""

    def test_special_characters_removed(self):
        result = normalize_text("Hello!!! @#$ World***", ABBRS)
        assert "!" not in result
        assert "@" not in result


# ──────────────────────────────────────────────────────────────────────────────
# extractor.py tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPincodeExtraction:
    def test_bare_pincode(self):
        assert extract_pincode("Lucknow 226016") == "226016"

    def test_pincode_with_dash(self):
        assert extract_pincode("UP - 226016") == "226016"

    def test_pincode_with_prefix(self):
        assert extract_pincode("pin: 110001") == "110001"

    def test_no_pincode(self):
        assert extract_pincode("Near Railway Station, Delhi") is None

    def test_ignores_7digit_number(self):
        assert extract_pincode("Order 1234567") is None

    def test_ignores_5digit_number(self):
        assert extract_pincode("Plot 12345 Block A") is None


class TestCareOfExtraction:
    def test_son_of(self):
        val = extract_care_of("s/o ram singh, h no 15")
        assert val is not None
        assert "Ram Singh" in val

    def test_wife_of(self):
        val = extract_care_of("w/o suresh kumar, flat 3b")
        assert val is not None
        assert "Suresh Kumar" in val

    def test_care_of(self):
        val = extract_care_of("c/o national public school, sector 5")
        assert val is not None

    def test_daughter_of(self):
        val = extract_care_of("d/o mohan lal, village rampur")
        assert val is not None

    def test_no_care_of(self):
        assert extract_care_of("near metro station, delhi") is None


class TestHouseNumberExtraction:
    def test_h_no(self):
        assert extract_house_number("H No 15/1 Indira Nagar") == "15/1"

    def test_house_number_full(self):
        assert extract_house_number("House Number 42A") == "42A"

    def test_plot_no(self):
        assert extract_house_number("Plot No 7/B, Sector 4") == "7/B"

    def test_flat_no(self):
        assert extract_house_number("Flat No 4B, Tower 3") == "4B"

    def test_door_no(self):
        assert extract_house_number("Door No 23, MG Road") == "23"


class TestLandmarkExtraction:
    def test_near(self):
        val = extract_landmark("near city mall, indira nagar")
        assert val is not None
        assert "City Mall" in val

    def test_opposite(self):
        val = extract_landmark("opp apollo hospital, delhi")
        assert val is not None

    def test_no_landmark(self):
        assert extract_landmark("house no 5, sector 10, delhi") is None


class TestVillageExtraction:
    def test_village(self):
        val = extract_village_info("village rampur, post office kunda, dist pratapgarh")
        assert val is not None
        assert "Rampur" in val

    def test_vill_abbr(self):
        val = extract_village_info("vill rampur, dist lucknow")
        assert val is not None

    def test_no_village(self):
        assert extract_village_info("sector 5, noida, up") is None


class TestDistrictExtraction:
    def test_district(self):
        district, _ = extract_district_info("dist lucknow, up - 226016")
        assert district is not None
        assert "Lucknow" in district

    def test_no_district(self):
        district, _ = extract_district_info("near metro station, delhi")
        assert district is None


# ──────────────────────────────────────────────────────────────────────────────
# parser.py integration tests
# ──────────────────────────────────────────────────────────────────────────────

class TestFullParsing:
    SAMPLE_ADDRESS = "S/O Ram Singh, H No 15/1 Near City Mall, Indira Nagar, Lucknow, UP - 226016"

    def test_returns_parsed_address(self, parser):
        result = parser.parse_address(self.SAMPLE_ADDRESS)
        assert result is not None

    def test_pincode_detected(self, parser):
        result = parser.parse_address(self.SAMPLE_ADDRESS)
        assert result.pincode == "226016"

    def test_care_of_detected(self, parser):
        result = parser.parse_address(self.SAMPLE_ADDRESS)
        assert result.care_of is not None
        assert "Ram Singh" in result.care_of

    def test_house_number_detected(self, parser):
        result = parser.parse_address(self.SAMPLE_ADDRESS)
        assert result.house_number == "15/1"

    def test_landmark_detected(self, parser):
        result = parser.parse_address(self.SAMPLE_ADDRESS)
        assert result.landmark is not None

    def test_confidence_score_range(self, parser):
        result = parser.parse_address(self.SAMPLE_ADDRESS)
        assert 0.0 <= result.confidence_score <= 1.0

    def test_empty_address(self, parser):
        result = parser.parse_address("")
        assert result.confidence_score == 0.0
        assert "Empty input" in result.validation_errors

    def test_noisy_address(self, parser):
        noisy = "s/o ramsingh!!! h.no=15, near-city mall,,, lucknow UP 226016"
        result = parser.parse_address(noisy)
        assert result.pincode == "226016"

    def test_stuck_token_address(self, parser):
        # "237okhlaphase3" should be split and parsed
        result = parser.parse_address("237okhlaphase3 NewDelhi 110001")
        assert result.pincode == "110001"

    def test_rural_address(self, parser):
        result = parser.parse_address(
            "Vill Rampur, Post Office Kunda, Dist Pratapgarh, UP - 230143"
        )
        assert result.village is not None
        assert result.district is not None
        assert result.pincode == "230143"

    def test_to_dict_no_none_values(self, parser):
        """to_dict() should not include None address fields."""
        result = parser.parse_address(self.SAMPLE_ADDRESS)
        d = result.to_dict()
        address_fields = [
            "care_of", "house_number", "building_name", "street",
            "locality", "landmark", "village", "subdistrict",
            "district", "city", "state", "pincode",
        ]
        for k in address_fields:
            if k in d:
                assert d[k] is not None, f"Field '{k}' should not be None in output"


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI endpoint tests
# ──────────────────────────────────────────────────────────────────────────────

class TestAPIEndpoints:
    def test_root(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "version" in res.json()

    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] in ("ok", "degraded")

    def test_parse_single_success(self, client):
        res = client.post("/parse", json={"address": "H No 15, Sector 4, Delhi - 110001"})
        assert res.status_code == 200
        body = res.json()
        assert "original" in body
        assert "parsed" in body
        assert body["parsed"]["pincode"] == "110001"

    def test_parse_single_empty(self, client):
        res = client.post("/parse", json={"address": ""})
        assert res.status_code == 422   # Pydantic validation error (min_length=5)

    def test_parse_bulk_success(self, client):
        res = client.post("/parse/bulk", json={
            "addresses": [
                "H No 15, Sector 4, Delhi - 110001",
                "Flat 3B, MG Road, Bangalore - 560001",
            ]
        })
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        assert len(body["results"]) == 2

    def test_parse_bulk_too_many(self, client):
        res = client.post("/parse/bulk", json={"addresses": ["addr"] * 501})
        assert res.status_code == 422

    def test_process_time_header(self, client):
        res = client.post("/parse", json={"address": "Lucknow UP 226016"})
        assert "X-Process-Time-Ms" in res.headers