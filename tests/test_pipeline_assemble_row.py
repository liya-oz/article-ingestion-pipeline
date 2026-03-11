import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from pipeline import assemble_row

def test_assemble_row_all_keys_and_format():
    test_record = {
        "doi": "10.1234/example.doi",
        "title": "Sample Title",
        "abstract": "Sample abstract.",
        "year": 2022,
        "authors": [{"given": "Alice", "family": "Smith"}, {"given": "Bob", "family": "Jones"}],
        "references": [
            {"raw": "Reference 1", "doi": "10.5678/ref1"},
            {"raw": "Reference 2", "doi": None}
        ],
        "openalex_id": "OA123456",
        "country_detection_method": "crossref",
        "provenance": {"title": "crossref", "year": "crossref"},
        "metadata_errors": ["warning: missing_abstract"]
    }

    row = assemble_row(test_record)
    expected_keys = {
        "doi", "title", "abstract", "year", "author_first_names", "author_last_names",
        "author_genders", "countries_research", "references_count", "references_list",
        "openalex_id", "country_detection_method", "provenance", "authors_json", "references_json", "metadata_errors"
    }
    assert set(row.keys()) == expected_keys
    assert row["author_first_names"] == "Alice|Bob"
    assert row["author_last_names"] == "Smith|Jones"
    assert row["author_genders"] == "unknown|unknown"
    assert row["references_count"] == 2
    assert "Reference 2" in row["references_list"]
    assert row["openalex_id"] == "OA123456"
    assert row["country_detection_method"] == "crossref"
    assert json.loads(row["provenance"]) == {"title": "crossref", "year": "crossref"}
    assert json.loads(row["authors_json"])[0]["given"] == "Alice"
    assert json.loads(row["references_json"])[0]["doi"] == "10.5678/ref1"
    assert "warning: missing_abstract" in row["metadata_errors"]