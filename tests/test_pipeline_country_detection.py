import sys
import os
import json
import pytest

# Add project root to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline import load_country_mapping, build_country_name_index, detect_countries_from_text, detect_countries_from_record

@pytest.fixture(scope="session")
def country_mapping():
    # Adjust path as needed - assumes country.json is at project root
    return load_country_mapping("country.json")

@pytest.fixture(scope="session")
def name_index(country_mapping):
    return build_country_name_index(country_mapping)

def test_load_country_mapping(country_mapping):
    # Example check: mapping contains US and United States
    assert "US" in country_mapping
    assert country_mapping["US"] == "United States"

def test_build_country_name_index(name_index):
    # Example check: US variants exist
    assert "united states" in name_index
    assert name_index["united states"] == "US"
    assert "usa" in name_index
    assert name_index["usa"] == "US"
    # Example: UK is in name index
    assert "united kingdom" in name_index
    assert name_index["united kingdom"] == "GB"

def test_detect_countries_from_text(name_index):
    title = "Collaborations between Canada and Kenya"
    abstract = "Researchers from the United States joined the project."
    result = detect_countries_from_text(title, abstract, name_index)
    assert set(result) == {"CA", "KE", "US"}

def test_detect_countries_from_record(name_index, country_mapping):
    record = {
        "title": "Research in the United Kingdom",
        "abstract": "Studies also conducted in Kenya.",
        "countries": ["US"],
        "country_detection_method": "",
        "provenance": {},
        "metadata_errors": []
    }
    updated = detect_countries_from_record(record)
    # Should set text-detected countries
    assert set(updated["countries"]) == {"GB", "KE"}
    assert updated["country_detection_method"] == "detected_in_text"
    assert updated["provenance"]["countries"] == "detected_in_text"
    assert isinstance(updated["metadata_errors"], list)