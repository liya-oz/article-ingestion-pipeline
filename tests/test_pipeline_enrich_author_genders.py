import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline import enrich_author_genders

def test_enrich_author_genders_pipeline_behavior(monkeypatch):
    """
    Checks:
    - Recognizable name (high-prob): assigned 'female'
    - Initials/dots/whitespace: assigned 'unknown', Genderize called for 'B.' in current logic, no error logged for these
    - Uncertain name (low probability): assigned 'unknown'
    - Exception: error logged for 'Error'
    - Pipe-separated order preserved
    """

    genderize_calls = []

    def fake_fetch_genderize(name):
        genderize_calls.append(name)
        if name.strip().lower() == "alice":
            return {"gender": "female", "probability": 0.99, "count": 1234}
        if name.strip().lower() == "uncertain":
            return {"gender": "male", "probability": 0.4, "count": 100}
        if name.strip().lower() == "error":
            raise Exception("API failure!")
        return {"gender": None, "probability": 0.0, "count": 0}

    monkeypatch.setattr("pipeline.fetch_genderize", fake_fetch_genderize)

    record = {
        "doi": "10.1234/example",
        "title": "Test",
        "year": 2020,
        "authors": [
            {"given": "Alice Marie", "family": "Smith"},      # Should call Genderize (gets female)
            {"given": "B.", "family": "Initials"},            # Currently calls Genderize ('unknown')
            {"given": ".", "family": "Dots"},                 # Should NOT call Genderize ('unknown')
            {"given": " ", "family": "Empty"},                # Should NOT call Genderize ('unknown')
            {"given": "Uncertain Name", "family": "Brown"},   # Should NOT call Genderize (based on current code behavior)
            {"given": "Error Name", "family": "Fail"},        # Should call Genderize (raises Exception)
        ],
        "metadata_errors": []
    }

    enrich_author_genders(record, threshold=0.8)

    # Genderize calls
    assert genderize_calls == ["Alice", "B.", "Uncertain", "Error"]

    # Gender assignments
    assert record["authors"][0]["gender"] == "female"
    assert record["authors"][1]["gender"] == "unknown"
    assert record["authors"][2]["gender"] == "unknown"
    assert record["authors"][3]["gender"] == "unknown"
    assert record["authors"][4]["gender"] == "unknown"
    assert record["authors"][5]["gender"] == "unknown"

    # Pipe-separated genders
    assert record["author_genders"] == "female|unknown|unknown|unknown|unknown|unknown"

    # Error handling: only Error Name should log genderize_error
    assert any("genderize_error: Error" in err for err in record["metadata_errors"])
    # There should NOT be error for 'B.', '.', or ' ' in metadata_errors
    assert not any("genderize_error: B." in err for err in record["metadata_errors"])
    assert not any("genderize_error: ." in err for err in record["metadata_errors"])
    assert not any("genderize_error:  " in err for err in record["metadata_errors"])

    # Note: 'Uncertain Name' never triggers a genderize call under current
