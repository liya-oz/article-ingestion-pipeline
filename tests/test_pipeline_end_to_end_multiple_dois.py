import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from pipeline import fetch_crossref, parse_crossref_response, build_canonical_record


def test_end_to_end_two_dois():
    dois = [
        "10.1038/nphys1170",
        "10.1103/PhysRevLett.78.390"
    ]

    records = []

    for doi in dois:
        raw = fetch_crossref(doi)
        assert raw is not None, f"Fetch failed for {doi}"

        parsed = parse_crossref_response(raw)
        assert isinstance(parsed, dict), "Parsed result must be dict"

        record = build_canonical_record(parsed)

        # Basic sanity checks
        assert record["doi"] != ""
        assert "provenance" in record
        assert "metadata_errors" in record
        assert isinstance(record["references"], list)

        records.append(record)

    # We should have 2 records
    assert len(records) == 2

    # Ensure records are serializable
    try:
        json.dumps(records)
    except Exception as e:
        assert False, f"Records not JSON serializable: {e}"