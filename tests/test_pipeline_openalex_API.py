import sys
import os
import json
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import shutil
import pytest
import requests
from pipeline import fetch_openalex, normalize_doi

def _cache_path_for_openalex(doi: str) -> str:
    """Return the expected cache/openalex path for a given DOI (mirrors pipeline logic)."""
    normalized = normalize_doi(doi)
    doi_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return os.path.join("cache", "openalex", f"{doi_hash}.json")

TEST_DOI = "doi:10.1007/s10671-016-9199-2"
CACHE_DIR = "cache/openalex"

def test_fetch_openalex_cache_behavior():
    # Clean cache before test
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)

    # First call (should hit network and create cache)
    data1 = fetch_openalex(TEST_DOI)

    assert os.path.exists(CACHE_DIR)
    files = os.listdir(CACHE_DIR)
    assert len(files) == 1

    # Second call (should load from cache if implemented that way)
    data2 = fetch_openalex(TEST_DOI)

    assert data1 == data2

def test_fetch_openalex_retries_and_raises_without_cache(monkeypatch):
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)

    call_count = {"n": 0}

    def fake_get(*args, **kwargs):
        call_count["n"] += 1
        raise requests.exceptions.Timeout("simulated timeout")

    monkeypatch.setattr("pipeline.requests.get", fake_get)
    monkeypatch.setattr("pipeline.time.sleep", lambda _seconds: None)

    test_doi = "doi:10.1234/timeout-test"
    cache_path = _cache_path_for_openalex(test_doi)

    if os.path.exists(cache_path):
        os.remove(cache_path)

    with pytest.raises(requests.exceptions.Timeout):
        fetch_openalex(test_doi)

    assert call_count["n"] == 3
    assert not os.path.exists(cache_path)

def test_fetch_openalex_uses_cache_on_network_failure(monkeypatch):
    """Cache-first: a pre-populated cache must be returned without any network calls."""
    os.makedirs(CACHE_DIR, exist_ok=True)

    test_doi = "doi:10.5678/cache-fallback"
    normalized = normalize_doi(test_doi)
    cache_path = _cache_path_for_openalex(test_doi)

    cached_payload = {"source": "cache", "doi": normalized}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cached_payload, f)

    call_count = {"n": 0}

    def fake_get(*args, **kwargs):
        call_count["n"] += 1
        raise requests.exceptions.ConnectionError("simulated connection error")

    monkeypatch.setattr("pipeline.requests.get", fake_get)
    monkeypatch.setattr("pipeline.time.sleep", lambda _seconds: None)

    data = fetch_openalex(test_doi)

    # Cache hit occurs before any network attempt — requests.get must not be called
    assert call_count["n"] == 0
    assert data == cached_payload