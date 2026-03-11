import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline import merge_crossref_openalex

def test_merge_crossref_openalex_priority_and_fallbacks():
    crossref = {
        "doi": "10.1234/abc",
        "title": "Short",
        "abstract": "",
        "year": None,
        "authors": [],
        "references": [{"raw": "ref1", "doi": "10.5678/def"}],
        "countries": [],
        "warnings": ["missing_title", "missing_year"]
    }
    openalex = {
        "openalex_id": "OA1",
        "title": "A much longer and better title from OpenAlex",
        "abstract": "OpenAlex abstract is long enough to be used.",
        "year": 2022,
        "authors": [{"given": "Alice", "family": "Smith"}],
        "countries": ["US"],
        "warnings": ["missing_abstract"]
    }

    merged = merge_crossref_openalex(crossref, openalex)
    # Title should come from OpenAlex because Crossref title is too short
    assert merged["title"] == openalex["title"]
    # Abstract should come from OpenAlex because Crossref is empty
    assert merged["abstract"] == openalex["abstract"]
    # Year should come from OpenAlex because Crossref is None
    assert merged["year"] == openalex["year"]
    # Authors should come from OpenAlex because Crossref is empty
    assert merged["authors"] == openalex["authors"]
    # References should come from Crossref (MVP logic)
    assert merged["references"] == crossref["references"]
    # OpenAlex ID should be present
    assert merged["openalex_id"] == openalex["openalex_id"]
    # Countries should come from OpenAlex
    assert merged["countries"] == openalex["countries"]
    # Author genders should always be "unknown"
    assert merged["author_genders"] == "unknown"
    # Countries source should be "affiliations"
    assert merged["country_detection_method"] == "derived_from_affiliations"
    # Provenance should reflect correct sources
    assert merged["provenance"]["title"] == "openalex"
    assert merged["provenance"]["abstract"] == "openalex"
    assert merged["provenance"]["year"] == "openalex"
    assert merged["provenance"]["authors"] == "openalex"
    assert merged["provenance"]["references"] == "crossref"
    assert merged["provenance"]["openalex_id"] == "openalex"
    assert merged["provenance"]["countries"] == "openalex"
    assert merged["provenance"]["author_genders"] == "missing"
    # Metadata errors should include warnings from both
    assert "warning: missing_title" in merged["metadata_errors"]
    assert "warning: missing_year" in merged["metadata_errors"]
    assert "warning: missing_abstract" in merged["metadata_errors"]

def test_merge_crossref_openalex_crossref_only():
    crossref = {
        "doi": "10.1234/abc",
        "title": "A valid Crossref Title",
        "abstract": "Crossref abstract is long enough." * 20,
        "year": 2020,
        "authors": [{"given": "Bob", "family": "Jones"}],
        "references": [],
        "countries": [],
        "warnings": []
    }
    merged = merge_crossref_openalex(crossref, None)
    # All fields should come from Crossref
    assert merged["title"] == crossref["title"]
    assert merged["abstract"] == crossref["abstract"]
    assert merged["year"] == crossref["year"]
    assert merged["authors"] == crossref["authors"]
    assert merged["references"] == crossref["references"]
    assert merged["openalex_id"] == ""
    assert merged["countries"] == []
    assert merged["author_genders"] == "unknown"
    assert merged["country_detection_method"] == "no_country_detected"
    assert merged["provenance"]["title"] == "crossref"
    assert merged["provenance"]["abstract"] == "crossref"
    assert merged["provenance"]["year"] == "crossref"
    assert merged["provenance"]["authors"] == "crossref"
    assert merged["provenance"]["references"] == "missing"
    assert merged["provenance"]["openalex_id"] == "missing"
    assert merged["provenance"]["countries"] == "missing"
    assert merged["provenance"]["author_genders"] == "missing"
    assert merged["metadata_errors"] == []