import sys
from pathlib import Path
import pytest

# Add project root to sys.path for pipeline import
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import parse_openalex_response

def test_parse_openalex_response_full():
    openalex_json = {
        "id": "OA123",
        "title": "Test Title",
        "abstract_inverted_index": {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3]
        },
        "publication_year": 2024,
        "authorships": [
            {
                "author": {"display_name": "Alice Smith"},
                "institutions": [{"country_code": "US"}]
            },
            {
                "author": {"display_name": "Bob Jones"},
                "institutions": [{"country_code": "GB"}]
            }
        ]
    }
    result = parse_openalex_response(openalex_json)
    assert result["openalex_id"] == "OA123"
    assert result["title"] == "Test Title"
    assert result["abstract"] == "This is a test"
    assert result["year"] == 2024
    assert result["authors"] == [
        {"given": "Alice", "family": "Smith"},
        {"given": "Bob", "family": "Jones"}
    ]
    assert set(result["countries"]) == {"US", "GB"}
    assert result["warnings"] == []

def test_parse_openalex_response_missing_fields():
    openalex_json = {}
    result = parse_openalex_response(openalex_json)
    assert result["openalex_id"] == ""
    assert result["title"] == ""
    assert result["abstract"] == ""
    assert result["year"] is None
    assert result["authors"] == []
    assert result["countries"] == []
    # Should have all warnings
    assert "missing_title" in result["warnings"]
    assert "missing_abstract" in result["warnings"]
    assert "missing_year" in result["warnings"]
    assert "missing_authors" in result["warnings"]
    assert "missing_countries" in result["warnings"]