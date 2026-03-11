import sys
from pathlib import Path
import pytest

# Add project root to sys.path for pipeline import
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import pipeline  # Assumes pipeline.py is in the project root

def assemble_row(record, country_mapping=None):
    return {
        "doi": record.get("doi", ""),
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "year": record.get("year", ""),
        "author_first_names": ", ".join([a.get("given", "") for a in record.get("authors", [])]),
        "author_last_names": ", ".join([a.get("family", "") for a in record.get("authors", [])]),
        "author_genders": record.get("author_genders", ""),
        "countries_research": ", ".join(record.get("countries", [])),
        "references_list": ", ".join([r.get("doi") or r.get("raw", "") for r in record.get("references", [])]),
        "metadata_errors": ", ".join(record.get("metadata_errors", [])),
    }

@pytest.fixture
def input_rows():
    return [
        {"original": "10.1234/validdoi1", "normalized": "10.1234/validdoi1"},
        {"original": "notadoi", "normalized": None},
        {"original": "", "normalized": None},
        {"original": "10.5678/validdoi2", "normalized": "10.5678/validdoi2"},
    ]

@pytest.fixture
def input_errors():
    return [
        {"line": 2, "original": "notadoi", "error": "blank_or_invalid_doi"},
        {"line": 3, "original": "", "error": "blank_or_invalid_doi"},
    ]

def mock_fetch_crossref(doi):
    return {"message": f"crossref for {doi}"}

def mock_parse_crossref(x):
    return {
        "doi": x["message"].split()[-1],
        "title": "Test Title",
        "year": 2021,
        "authors": [{"given": "Jane", "family": "Doe"}],
        "references": [{"doi": "refdoi", "raw": "Ref Article"}],
        "warnings": [],
        "raw_message": x,
    }

def mock_build_record(parsed):
    return {
        "doi": parsed["doi"],
        "title": parsed["title"],
        "abstract": "Abstract",
        "year": parsed["year"],
        "authors": parsed["authors"],
        "references": parsed["references"],
        "openalex_id": None,
        "countries": [],
        "author_genders": "",
        "country_detection_method": "no_country_detected",
        "provenance": {"source": "crossref"},
        "metadata_errors": [],
    }

def test_process_all_valid_and_invalid(monkeypatch, input_rows, input_errors):
    monkeypatch.setattr(pipeline, "fetch_crossref", mock_fetch_crossref)
    monkeypatch.setattr(pipeline, "parse_crossref_response", mock_parse_crossref)
    monkeypatch.setattr(pipeline, "build_canonical_record", mock_build_record)
    monkeypatch.setattr(pipeline, "assemble_row", assemble_row)

    results = pipeline.process_all(input_rows, input_errors)
    assert len(results) == len(input_rows)
    assert results[0]["doi"] == "10.1234/validdoi1"
    assert results[0]["title"] == "Test Title"
    assert results[0]["year"] == 2021
    assert "Jane" in results[0]["author_first_names"]
    assert results[1]["doi"] == ""
    assert "blank_or_invalid_doi at line 2" in results[1]["metadata_errors"]
    assert results[2]["doi"] == ""
    assert "blank_or_invalid_doi at line 3" in results[2]["metadata_errors"]
    assert results[3]["doi"] == "10.5678/validdoi2"
    assert results[3]["title"] == "Test Title"

    expected_keys = (
        "doi", "title", "abstract", "year", "author_first_names",
        "author_last_names", "author_genders", "countries_research",
        "references_list", "metadata_errors"
    )
    for row in results:
        for k in expected_keys:
            assert k in row

def test_process_all_crossref_failure(monkeypatch):
    monkeypatch.setattr(pipeline, "fetch_crossref", lambda doi: (_ for _ in ()).throw(Exception("Test failure")))
    monkeypatch.setattr(pipeline, "assemble_row", assemble_row)
    input_rows = [{"original": "10.9999/validdoi", "normalized": "10.9999/validdoi"}]
    input_errors = []
    results = pipeline.process_all(input_rows, input_errors)
    assert results[0]["doi"] == "10.9999/validdoi"
    assert "crossref_pipeline_failure: Test failure" in results[0]["metadata_errors"]