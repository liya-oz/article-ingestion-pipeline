"""MVP pipeline: read DOI CSV and output result.xlsx.

This script reads a list of DOIs from a CSV file, queries
public APIs (e.g., Crossref and OpenAlex), and writes a
Graph RAG–friendly Excel file (result.xlsx) with one row per DOI.

Usage example:
    python pipeline.py --input ./doi_list.csv
                       --output ./result.xlsx
"""

import argparse
import hashlib
import json
import logging
import os
import time
from typing import Optional, Iterable, List, Dict

import requests

try:
    import openpyxl
    from openpyxl import Workbook
except Exception:  # pragma: no cover - optional dependency for dry runs
    openpyxl = None  # type: ignore[assignment]
    Workbook = None  # type: ignore[assignment]

# Per instructions: default input path and output name
DEFAULT_INPUT = "./doi_list.csv"
DEFAULT_OUTPUT = "result.xlsx"

# Per instructions: cache directories
CACHE_DIRS = [
    "cache/crossref",
    "cache/openalex",
    "cache/genderize",
]


def normalize_doi(value: Optional[str]) -> str:
    """Normalize a DOI string according to minimal rules.

    - Accepts None or a string and always returns a string.
    - Returns "" for None or empty/whitespace-only input.
    - Trims leading/trailing whitespace.
    - Removes at most one leading "doi:" prefix (case-insensitive).
    - Lowercases the final result without changing internal characters.
    """

    if value is None:
        return ""

    s = value.strip()
    if not s:
        return ""

    if s.lower().startswith("doi:"):
        s = s[len("doi:") :]

    return s.lower()


def read_input(csv_path: str):
    """Read DOIs from a text/CSV file: one DOI per line, no header.

    Returns:
        rows: list of dicts with keys:
            - 'original': original string from the file
            - 'normalized': normalized DOI, or None if invalid/blank
        metadata_errors: list of dicts describing invalid/blank rows:
            - 'line': line number (1-based)
            - 'original': the original line content
            - 'error': 'blank_or_invalid_doi'
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    rows: List[dict] = []
    metadata_errors: List[dict] = []

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            # Remove trailing newline characters, keep the rest as-is
            original = raw_line.rstrip("\r\n")
            normalized = normalize_doi(original)

            if not normalized:
                # Blank or invalid DOI
                logging.warning(
                    "Row %d: empty or invalid DOI: %r", line_number, original
                )
                metadata_errors.append(
                    {
                        "line": line_number,
                        "original": original,
                        "error": "blank_or_invalid_doi",
                    }
                )
                rows.append({"original": original, "normalized": None})
            else:
                rows.append({"original": original, "normalized": normalized})

    return rows, metadata_errors

def ensure_cache_dirs() -> None:
    """Ensure that required cache directories exist.

    Creates:
    - cache/crossref
    - cache/openalex
    - cache/genderize
    """
    for d in CACHE_DIRS:
        os.makedirs(d, exist_ok=True)


def fetch_crossref(doi: str) -> Dict:
    """Fetch Crossref metadata for a single DOI with disk caching.

    - Normalizes the DOI.
    - Derives a cache path using the SHA-256 hash of the normalized DOI:
      cache/crossref/{sha256}.json
    - Returns immediately from cache if the file already exists.
    - Otherwise queries the Crossref API (up to 3 attempts), saves the raw
      JSON to cache on success, and returns the parsed dict.
    - Raises the last exception if all retries fail and no cache is available.
    """
    normalized_doi = normalize_doi(doi)
    if not normalized_doi:
        raise ValueError("DOI is blank or invalid")

    ensure_cache_dirs()

    doi_hash = hashlib.sha256(normalized_doi.encode("utf-8")).hexdigest()
    cache_path = os.path.join("cache", "crossref", f"{doi_hash}.json")

    # 1) Cache hit: return immediately without a network call
    if os.path.exists(cache_path):
        logging.info(f"[Crossref] Cache hit for DOI {normalized_doi}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 2) Cache miss: query Crossref with up to 3 attempts
    url = f"https://api.crossref.org/works/{normalized_doi}"
    last_exc: Optional[Exception] = None

    for attempt in range(3):
        try:
            logging.info(f"[Crossref] Fetching from API (attempt {attempt+1}) for DOI {normalized_doi}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data: Dict = response.json()

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"[Crossref] Cached API response for {normalized_doi}")

            return data
        except requests.RequestException as e:
            last_exc = e
            logging.warning(f"[Crossref] API error for DOI {normalized_doi} (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(1)

    # 3) All retries failed; raise last error (no stale cache available)
    if last_exc is not None:
        logging.error(f"[Crossref] All attempts failed for DOI {normalized_doi}")
        raise last_exc

    raise RuntimeError("Failed to fetch Crossref data and no cache available.")


def fetch_openalex(doi: str) -> Dict:
    """Fetch OpenAlex metadata for a single DOI with disk caching.

    - Normalizes the DOI.
    - Derives a cache path using the SHA-256 hash of the normalized DOI:
      cache/openalex/{sha256}.json
    - Returns immediately from cache if the file already exists.
    - Otherwise queries the OpenAlex API (up to 3 attempts), saves the raw
      JSON to cache on success, and returns the parsed dict.
    - Raises the last exception if all retries fail and no cache is available.
    """
    normalized_doi = normalize_doi(doi)
    if not normalized_doi:
        raise ValueError("DOI is blank or invalid")

    ensure_cache_dirs()

    doi_hash = hashlib.sha256(normalized_doi.encode("utf-8")).hexdigest()
    cache_path = os.path.join("cache", "openalex", f"{doi_hash}.json")

    # 1) Cache hit: return immediately without a network call
    if os.path.exists(cache_path):
        logging.info(f"[OpenAlex] Cache hit for DOI {normalized_doi}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 2) Cache miss: query OpenAlex with up to 3 attempts
    url = f"https://api.openalex.org/works/https://doi.org/{normalized_doi}"
    last_exc: Optional[Exception] = None

    for attempt in range(3):
        try:
            logging.info(f"[OpenAlex] Fetching from API (attempt {attempt+1}) for DOI {normalized_doi}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data: Dict = response.json()

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"[OpenAlex] Cached API response for {normalized_doi}")

            return data
        except requests.RequestException as e:
            last_exc = e
            logging.warning(f"[OpenAlex] API error for DOI {normalized_doi} (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(1)

    # 3) All retries failed; raise last error (no stale cache available)
    if last_exc is not None:
        logging.error(f"[OpenAlex] All attempts failed for DOI {normalized_doi}")
        raise last_exc

    raise RuntimeError("Failed to fetch OpenAlex data and no cache available.")


def fetch_genderize(name: str) -> Dict:
    """Fetch gender prediction for a first name using Genderize API with disk caching.

    - Lowercases the name and hashes it for cache key: cache/genderize/{sha256}.json
    - Returns immediately from cache if available.
    - Otherwise queries Genderize (up to 3 attempts), saves JSON to cache, and returns dict.
    - If all retries fail and no cache is available, raises the last exception.
    - If name is empty, returns a default dict without any HTTP request.
    """
    if not name or not name.strip():
        return {"name": name, "gender": None, "probability": 0.0, "count": 0}

    ensure_cache_dirs()

    name_lc = name.strip().lower()
    name_hash = hashlib.sha256(name_lc.encode("utf-8")).hexdigest()
    cache_path = os.path.join("cache", "genderize", f"{name_hash}.json")

    # 1) Cache hit: return immediately without a network call
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # If cache is corrupted, fall through to refetch

    # 2) Cache miss: query Genderize with up to 3 attempts
    url = f"https://api.genderize.io?name={requests.utils.quote(name_lc)}"
    last_exc: Optional[Exception] = None

    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Save to cache
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as exc:
            last_exc = exc
    # 3) All retries failed; raise last error (no stale cache available)
    if last_exc is not None:
        raise last_exc

    raise RuntimeError("Failed to fetch Genderize data and no cache available.")

def enrich_author_genders(record: Dict, threshold: float = 0.8) -> Dict:
    """
    Enrich authors in a canonical record with gender using Genderize API.

    - Uses first token of author['given'] as query.
    - Caches Genderize responses in-memory for this call.
    - Attaches 'gender' field to each author dict.
    - Updates record['author_genders'] as pipe-separated string.
    - On Genderize error, sets gender to 'unknown' and logs error in metadata_errors.
    """
    authors = record.get("authors", [])
    gender_cache = {}
    genders = []
    errors = record.get("metadata_errors", [])

    for author in authors:
        given = author.get("given", "").strip()
        first_token = given.split()[0] if given else ""
        name_lc = first_token.lower()

        # Check for empty or initials (single char or contains only dots)
        if not first_token or len(first_token) <= 1 or all(c in ". " for c in first_token):
            gender = "unknown"
        elif name_lc in gender_cache:
            genderize = gender_cache[name_lc]
            gender = (
                genderize.get("gender")
                if genderize.get("probability", 0.0) >= threshold and genderize.get("gender")
                else "unknown"
            )
        else:
            try:
                genderize = fetch_genderize(first_token)
                gender_cache[name_lc] = genderize
                gender = (
                    genderize.get("gender")
                    if genderize.get("probability", 0.0) >= threshold and genderize.get("gender")
                    else "unknown"
                )
            except Exception:
                gender = "unknown"
                errors.append(f"genderize_error: {first_token}")

        author["gender"] = gender
        genders.append(gender)

    record["author_genders"] = "|".join(genders)
    record["metadata_errors"] = errors
    return record


def write_header_excel(output_path: str) -> None:
    """Create an Excel file with the expected header row.

    Header columns (no data rows):
    doi,title,abstract,year,author_first_names,author_last_names,
    author_genders,countries_research,references_list,metadata_errors
    """
    headers = [
        "doi",
        "title",
        "abstract",
        "year",
        "author_first_names",
        "author_last_names",
        "author_genders",
        "countries_research",
        "references_list",
        "metadata_errors",
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "result"

    # Write header row
    ws.append(headers)

    wb.save(output_path)



def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="MVP pipeline: reads DOI CSV and outputs result.xlsx"
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Path to input CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Path to output Excel file (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args(list(argv) if argv is not None else None)

def parse_crossref_response(crossref_json: Dict) -> Dict:
    """Permissive Crossref parser: always returns dict with fields + warnings."""
    result = {
        "doi": "",
        "title": "",
        "year": None,
        "authors": [],
        "references": [],
        "warnings": [],
    }
    msg = crossref_json.get("message", {})

    # DOI extraction
    result["doi"] = msg.get("DOI", "") or ""

    # Title extraction
    title_list = msg.get("title", [])
    if title_list and isinstance(title_list, list):
        result["title"] = title_list[0] if title_list[0] else ""
    else:
        result["title"] = ""
        result["warnings"].append("missing_title")

    # Year extraction
    year = None
    issued = msg.get("issued", {})
    date_parts = issued.get("date-parts", [])
    if date_parts and isinstance(date_parts, list) and date_parts[0]:
        if isinstance(date_parts[0], list) and date_parts[0]:
            year = date_parts[0][0]
    if year is not None:
        result["year"] = year
    else:
        result["warnings"].append("missing_year")

    # Authors extraction
    authors = msg.get("author", [])
    if authors and isinstance(authors, list):
        for a in authors:
            given = a.get("given", "") if isinstance(a, dict) else ""
            family = a.get("family", "") if isinstance(a, dict) else ""
            result["authors"].append({"given": given, "family": family})
    else:
        result["warnings"].append("missing_authors")

    # References extraction
    references = msg.get("reference", [])
    if references and isinstance(references, list):
        for ref in references:
            if isinstance(ref, dict):
                raw = (
                    ref.get("unstructured", "")
                    or ref.get("article-title", "")
                    or ""
                )
                doi = ref.get("DOI", None)
                result["references"].append({"raw": raw, "doi": doi})
            else:
                result["references"].append({"raw": str(ref), "doi": None})
    else:
        result["warnings"].append("missing_references")

    return result


def parse_openalex_response(openalex_json: Dict) -> Dict:
    """Permissive OpenAlex parser: always returns dict with fields + warnings."""
    result = {
        "openalex_id": "",
        "title": "",
        "abstract": "",
        "year": None,
        "authors": [],
        "countries": [],
        "warnings": [],
    }

    # openalex_id
    result["openalex_id"] = openalex_json.get("id", "") or ""

    # title
    title = openalex_json.get("title", "")
    if title:
        result["title"] = title
    else:
        result["warnings"].append("missing_title")

    # abstract
    abstract = ""
    inverted_index = openalex_json.get("abstract_inverted_index")
    if inverted_index and isinstance(inverted_index, dict):
        # Reconstruct abstract from inverted index
        try:
            # Build a list of (position, word) pairs
            pos_word = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    pos_word.append((pos, word))
            # Sort by position and join words
            abstract_words = [w for _, w in sorted(pos_word)]
            abstract = " ".join(abstract_words)
        except Exception:
            abstract = ""
    if abstract:
        result["abstract"] = abstract
    else:
        result["warnings"].append("missing_abstract")

    # year
    year = openalex_json.get("publication_year")
    if isinstance(year, int):
        result["year"] = year
    else:
        result["warnings"].append("missing_year")

    # authors and countries
    authors = []
    countries = set()
    authorships = openalex_json.get("authorships", [])
    if authorships and isinstance(authorships, list):
        for auth in authorships:
            # Name parsing
            name = auth.get("author", {}).get("display_name", "") or ""
            given, family = "", ""
            if name:
                parts = name.split()
                if len(parts) == 1:
                    given = parts[0]
                elif len(parts) > 1:
                    given = " ".join(parts[:-1])
                    family = parts[-1]
            authors.append({"given": given, "family": family})

            # Country extraction
            institutions = auth.get("institutions", [])
            if institutions and isinstance(institutions, list):
                for inst in institutions:
                    country_code = inst.get("country_code")
                    if country_code:
                        countries.add(country_code)
    if authors:
        result["authors"] = authors
    else:
        result["warnings"].append("missing_authors")
    if countries:
        result["countries"] = list(sorted(countries))
    else:
        result["warnings"].append("missing_countries")

    return result


def merge_crossref_openalex(
    crossref_parsed: Dict,
    openalex_parsed: Optional[Dict]
) -> Dict:
    """Merge Crossref and OpenAlex parsed dicts into canonical record per field-level fallback rules."""
    # DOI: always from Crossref
    doi = crossref_parsed.get("doi", "")

    # Title
    crossref_title = crossref_parsed.get("title", "")
    openalex_title = (openalex_parsed or {}).get("title", "") if openalex_parsed else ""
    if not crossref_title or len(crossref_title.strip()) < 10:
        title = openalex_title or crossref_title
        provenance_title = "openalex" if openalex_title else ("crossref" if crossref_title else "missing")
    else:
        title = crossref_title
        provenance_title = "crossref"

    # Abstract
    crossref_abstract = crossref_parsed.get("abstract", "")
    openalex_abstract = (openalex_parsed or {}).get("abstract", "") if openalex_parsed else ""
    if (not crossref_abstract or len(crossref_abstract.strip()) < 200) and openalex_abstract:
        abstract = openalex_abstract
        provenance_abstract = "openalex"
    else:
        abstract = crossref_abstract
        provenance_abstract = "crossref" if crossref_abstract else "missing"

    # Year
    crossref_year = crossref_parsed.get("year", None)
    openalex_year = (openalex_parsed or {}).get("year", None) if openalex_parsed else None
    if crossref_year is None and openalex_year is not None:
        year = openalex_year
        provenance_year = "openalex"
    else:
        year = crossref_year
        provenance_year = "crossref" if crossref_year is not None else "missing"

    # Authors
    crossref_authors = crossref_parsed.get("authors", [])
    openalex_authors = (openalex_parsed or {}).get("authors", []) if openalex_parsed else []
    if not crossref_authors and openalex_authors:
        authors = openalex_authors
        provenance_authors = "openalex"
    else:
        authors = crossref_authors
        provenance_authors = "crossref" if crossref_authors else "missing"

    # References (MVP: Crossref only)
    references = crossref_parsed.get("references", [])
    provenance_references = "crossref" if references else "missing"

    # OpenAlex ID
    openalex_id = (openalex_parsed or {}).get("openalex_id", "") if openalex_parsed else ""
    provenance_openalex_id = "openalex" if openalex_id else "missing"

    # Countries
    crossref_countries = crossref_parsed.get("countries", []) or []
    openalex_countries = (openalex_parsed or {}).get("countries", []) if openalex_parsed else []
    if not crossref_countries and openalex_countries:
        countries = openalex_countries
        country_detection_method = "derived_from_affiliations"
        provenance_countries = "openalex"
    else:
        countries = crossref_countries
        country_detection_method = "no_country_detected"
        provenance_countries = "missing"

    # Author genders (MVP: always unknown)
    author_genders = "unknown"
    provenance_gender = "missing"

    # Metadata errors: merge warnings from both sources
    metadata_errors = []
    for w in crossref_parsed.get("warnings", []):
        if isinstance(w, str):
            metadata_errors.append(f"warning: {w}")
    if openalex_parsed:
        for w in openalex_parsed.get("warnings", []):
            if isinstance(w, str):
                metadata_errors.append(f"warning: {w}")

    # Provenance dict
    provenance = {
        "title": provenance_title,
        "abstract": provenance_abstract,
        "year": provenance_year,
        "authors": provenance_authors,
        "references": provenance_references,
        "openalex_id": provenance_openalex_id,
        "countries": provenance_countries,
        "author_genders": provenance_gender,
    }

    return {
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "year": year,
        "authors": authors,
        "references": references,
        "openalex_id": openalex_id,
        "countries": countries,
        "author_genders": author_genders,
        "country_detection_method": country_detection_method,
        "provenance": provenance,
        "metadata_errors": metadata_errors,
    }

def assemble_row(record: Dict, country_mapping: Dict[str, str] = None) -> Dict:
    """Flatten canonical record into Excel row dict with final schema."""
    authors = record.get("authors", [])
    references = record.get("references", [])
    provenance = record.get("provenance", {})
    metadata_errors = record.get("metadata_errors", [])
    # Handle author_genders: if missing or empty, fill with 'unknown' per author
    author_genders = record.get("author_genders", "")
    if not author_genders:
        if authors:
            author_genders = "|".join(["unknown"] * len(authors))
        else:
            author_genders = ""
    if country_mapping is None:
        country_mapping = load_country_mapping()
    countries_codes = record.get("countries", [])
    countries_names = [country_mapping.get(code, code) for code in countries_codes]
    return {
        "doi": record.get("doi", ""),
        "title": record.get("title", ""),
        "abstract": record.get("abstract", ""),
        "year": record.get("year", ""),
        "author_first_names": "|".join([a.get("given", "") for a in authors]) if authors else "",
        "author_last_names": "|".join([a.get("family", "") for a in authors]) if authors else "",
        "author_genders": author_genders,
        "countries_research": ";".join(countries_names) if countries_names else "",
        "references_count": len(references),
        "references_list": "\n".join(
            [r.get("doi") if r.get("doi") else r.get("raw", "") for r in references]
        ) if references else "",
        "openalex_id": record.get("openalex_id") or "",
        "country_detection_method": record.get("country_detection_method", ""),
        "provenance": json.dumps(provenance),
        "authors_json": json.dumps(authors),
        "references_json": json.dumps(references),
        "metadata_errors": "; ".join(metadata_errors) if metadata_errors else "",
    }

def build_canonical_record(parsed: Dict) -> Dict:
    """Build canonical article record from parsed Crossref data (skeleton).

    Args:
        parsed: Output from parse_crossref_response or similar:
            {
                "doi": str,
                "title": str,
                "year": Optional[int],
                "authors": List[{"given": str, "family": str}],
                "references": List[{"raw": str, "doi": Optional[str]}],
                "warnings": List[str],
                # optionally, the original Crossref 'message' under "raw_message"
            }

    Returns:
        Dict with canonical keys:
            doi, title, abstract, year, authors, references,
            openalex_id, countries, author_genders, country_detection_method,
            provenance, metadata_errors
    """
    title = parsed.get("title", "")
    year = parsed.get("year", None)
    authors = parsed.get("authors", [])
    references = parsed.get("references", [])

    provenance = {
        "title": "crossref" if title else "missing",
        "abstract": "missing",  # always missing for MVP
        "year": "crossref" if year is not None else "missing",
        "authors": "crossref" if authors else "missing",
        "references": "crossref" if references else "missing",
    }

    # Build metadata_errors: copy warnings, convert to human-readable, append for missing fields
    metadata_errors = []
    for w in parsed.get("warnings", []):
        if isinstance(w, str):
            metadata_errors.append(f"warning: {w}")

    if not title:
        metadata_errors.append("error: missing_title")
    if year is None:
        metadata_errors.append("error: missing_year")

    return {
        "doi": parsed.get("doi", ""),
        "title": title,
        "abstract": "",  # Crossref-only MVP: leave empty
        "year": year,
        "authors": authors,
        "references": references,
        "openalex_id": None,
        "countries": [],
        "author_genders": "unknown",
        "country_detection_method": "no_country_detected",
        "provenance": provenance,
        "metadata_errors": metadata_errors,
    }


_country_mapping_cache: Optional[Dict[str, str]] = None

def load_country_mapping(json_path: str = "country.json") -> Dict[str, str]:
    """
    Load the ISO 3166-1 alpha-2 → English name mapping from country.json.
    Returns a dict like {"US": "United States", ...}.
    Should read the file once and reuse it (simple module-level cache).
    """
    global _country_mapping_cache
    if _country_mapping_cache is not None:
        return _country_mapping_cache
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Country mapping file not found: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        _country_mapping_cache = json.load(f)
    return _country_mapping_cache


def build_country_name_index(country_mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Given {"US": "United States", ...}, return a dict mapping
    lowercase country name variants to ISO codes, e.g.:
    {
      "united states": "US",
      "united states of america": "US",
      "usa": "US",
      "us": "US",
      "kenya": "KE",
      ...
    }
    For MVP, it's enough to:
      - include the official name from country_mapping (lowercased),
      - add a few obvious extra variants for key countries (e.g. US/USA/United States, UK/United Kingdom).
    """
    index = {}
    for code, name in country_mapping.items():
        norm_name = name.lower()
        index[norm_name] = code

    # Add common variants for key countries
    # United States
    index["united states of america"] = "US"
    index["usa"] = "US"
    index["us"] = "US"
    # United Kingdom
    index["united kingdom"] = "GB"
    index["uk"] = "GB"
    # Russia
    index["russia"] = "RU"
    index["russian federation"] = "RU"
    # South Korea
    index["south korea"] = "KR"
    index["republic of korea"] = "KR"
    index["korea"] = "KR"
    # North Korea
    index["north korea"] = "KP"
    index["democratic people's republic of korea"] = "KP"
    # China
    index["china"] = "CN"
    index["people's republic of china"] = "CN"
    # Other common variants can be added as needed

    return index


def detect_countries_from_text(title: str, abstract: str, name_index: Dict[str, str]) -> List[str]:
    """
    Given title and abstract strings, and a mapping of lowercase country name variants → ISO codes,
    return a list of unique ISO codes detected in the combined text.
    """
    text = (title or "") + " " + (abstract or "")
    text_lc = text.lower()
    matched_codes = set()
    for name_variant, iso_code in name_index.items():
        if name_variant in text_lc:
            matched_codes.add(iso_code)
    return sorted(matched_codes)


def detect_countries_from_record(record: Dict) -> Dict:
    """
    Update record['countries'], record['country_detection_method'], and record['provenance']['countries']
    based on title/abstract text and any existing affiliation-derived countries.
    """
    try:
        mapping = load_country_mapping()
        name_index = build_country_name_index(mapping)
        text_countries = detect_countries_from_text(
            record.get("title", ""), record.get("abstract", ""), name_index
        )
    except Exception as exc:
        msg = f"country_mapping_error: {str(exc)}"
        if "metadata_errors" in record and isinstance(record["metadata_errors"], list):
            record["metadata_errors"].append(msg)
        else:
            record["metadata_errors"] = [msg]
        if not record.get("countries"):
            record["countries"] = []
        if not record.get("country_detection_method"):
            record["country_detection_method"] = "no_country_detected"
        if "provenance" in record and isinstance(record["provenance"], dict):
            record["provenance"]["countries"] = "no_country_detected"
        else:
            record["provenance"] = {"countries": "no_country_detected"}
        return record

    if text_countries:
        # Case A: text match found
        record["countries"] = sorted(set(text_countries))
        record["country_detection_method"] = "detected_in_text"
        if "provenance" in record and isinstance(record["provenance"], dict):
            record["provenance"]["countries"] = "detected_in_text"
        else:
            record["provenance"] = {"countries": "detected_in_text"}
        return record

    if record.get("countries"):
        # Case B: no text match, but countries already present (affiliations/OpenAlex)
        if not record.get("country_detection_method") or record.get("country_detection_method") == "no_country_detected":
            record["country_detection_method"] = "derived_from_affiliations"
        if "provenance" in record and isinstance(record["provenance"], dict):
            record["provenance"]["countries"] = "openalex"
        else:
            record["provenance"] = {"countries": "openalex"}
        return record

    # Case C: nothing found
    record["countries"] = []
    record["country_detection_method"] = "no_country_detected"
    if "provenance" in record and isinstance(record["provenance"], dict):
        record["provenance"]["countries"] = "no_country_detected"
    else:
        record["provenance"] = {"countries": "no_country_detected"}
    return record


def process_all(doi_rows: List[Dict], input_errors: List[Dict]) -> List[Dict]:
    """Process all DOI rows and input errors, returning assembled Excel row dicts.

    - Iterates over DOI rows in input order.
    - For invalid/blank DOIs: creates minimal canonical record with metadata_errors from input_errors.
    - For valid DOIs: wraps per-DOI pipeline in try/except, merges all errors into metadata_errors.
    - Optionally uses OpenAlex as a secondary source for abstract enrichment.
    - Returns list of assembled row dicts.
    """
    result = []
    country_mapping = load_country_mapping()
    total = len(doi_rows)
    for idx, row in enumerate(doi_rows):
        normalized = row.get("normalized")
        original = row.get("original")
        log_prefix = f"[DOI {idx+1}/{total}]"
        if normalized is None:
            logging.info(f"{log_prefix} Skipping invalid/blank DOI: '{original}'")
            # Handle invalid/blank DOI
            error_entry = next(
                (err for err in input_errors if err.get("line") == idx + 1), None
            )
            metadata_errors = []
            if error_entry:
                metadata_errors.append(
                    f"{error_entry.get('error', '')} at line {error_entry.get('line', '')}"
                )
            canonical_record = {
                "doi": "",
                "title": "",
                "abstract": "",
                "year": "",
                "authors": [],
                "references": [],
                "openalex_id": "",
                "countries": [],
                "author_genders": "",
                "country_detection_method": "",
                "provenance": {},
                "metadata_errors": metadata_errors,
            }
            # Enrich author genders (no-op for empty authors)
            canonical_record = enrich_author_genders(canonical_record)
            row_dict = assemble_row(canonical_record, country_mapping)
            result.append(row_dict)
        else:
            logging.info(f"{log_prefix} Processing DOI: {normalized}")
            # Handle valid DOI with Crossref and optional OpenAlex enrichment
            metadata_errors = []
            canonical_record = None
            crossref_parsed = None
            openalex_parsed = None
            openalex_error = None
            try:
                crossref_json = fetch_crossref(normalized)
                crossref_parsed = parse_crossref_response(crossref_json)
            except Exception as exc:
                logging.error(f"{log_prefix} Crossref fetch/parse failed: {exc}")
                # Fallback canonical record with error
                metadata_errors.append(f"crossref_pipeline_failure: {str(exc)}")
                canonical_record = {
                    "doi": normalized,
                    "title": "",
                    "abstract": "",
                    "year": "",
                    "authors": [],
                    "references": [],
                    "openalex_id": "",
                    "countries": [],
                    "author_genders": "",
                    "country_detection_method": "",
                    "provenance": {},
                    "metadata_errors": metadata_errors,
                }
                # Merge input_errors for this row
                error_entry = next(
                    (err for err in input_errors if err.get("line") == idx + 1), None
                )
                if error_entry:
                    canonical_record["metadata_errors"].append(
                        f"{error_entry.get('error', '')} at line {error_entry.get('line', '')}"
                    )
                # Enrich author genders (no-op for empty authors)
                canonical_record = enrich_author_genders(canonical_record)
                row_dict = assemble_row(canonical_record, country_mapping)
                result.append(row_dict)
                continue

            # Decide whether to call OpenAlex based on Crossref abstract
            crossref_abstract = crossref_parsed.get("abstract", "")
            if not crossref_abstract or len(crossref_abstract.strip()) < 200:
                try:
                    logging.info(f"{log_prefix} Fetching OpenAlex for DOI: {normalized}")
                    openalex_json = fetch_openalex(normalized)
                    openalex_parsed = parse_openalex_response(openalex_json)
                except Exception as exc:
                    openalex_parsed = None
                    openalex_error = f"openalex_error: {str(exc)}"
                    logging.warning(f"{log_prefix} OpenAlex fetch/parse failed: {exc}")
            else:
                openalex_parsed = None

            # Merge Crossref and OpenAlex
            canonical_record = merge_crossref_openalex(crossref_parsed, openalex_parsed)

            # Append OpenAlex error if any
            if openalex_error:
                canonical_record["metadata_errors"].append(openalex_error)

            # Merge input_errors for this row
            error_entry = next(
                (err for err in input_errors if err.get("line") == idx + 1), None
            )
            if error_entry:
                canonical_record["metadata_errors"].append(
                    f"{error_entry.get('error', '')} at line {error_entry.get('line', '')}"
                )
            # Enrich author genders 
            canonical_record = enrich_author_genders(canonical_record)
            # Enrich country detection with error handling
            canonical_record.setdefault("metadata_errors", [])
            try:
                canonical_record = detect_countries_from_record(canonical_record)
            except Exception as exc:
                canonical_record["metadata_errors"].append(f"country_detection_error: {str(exc)}")
                logging.warning(f"{log_prefix} Country detection failed: {exc}")
            row_dict = assemble_row(canonical_record, country_mapping)
            result.append(row_dict)
    return result

def run_pipeline(input_path: str, output_path: str) -> bool:
    """Main orchestration logic.

    - Reads input CSV for DOI rows and input errors.
    - Processes all DOIs using process_all.
    - Writes header and all rows to Excel in a single batch.
    - Logs summary statistics (DOIs processed, errors, etc.).
    - Robust error handling: failures for any DOI do not stop pipeline.
    """
    logging.info("Starting pipeline")
    if not os.path.exists(input_path):
        logging.error("Input CSV not found: %s", input_path)
        return False

    ensure_cache_dirs()
    doi_rows, metadata_errors = read_input(input_path)
    if not doi_rows:
        logging.warning("No rows found in input CSV.")
        return False

    assembled_rows = process_all(doi_rows, input_errors=metadata_errors)

    # Define header columns (16 columns from excel_schema_decisions.md)
    headers = [
        "doi",
        "title",
        "abstract",
        "year",
        "author_first_names",
        "author_last_names",
        "author_genders",
        "countries_research",
        "references_count",
        "references_list",
        "openalex_id",
        "country_detection_method",
        "provenance",
        "authors_json",
        "references_json",
        "metadata_errors",
    ]

    # Write Excel file (overwrite if exists)
    wb = Workbook()
    ws = wb.active
    ws.title = "result"
    ws.append(headers)
    for row in assembled_rows:
        ws.append([row.get(col, "") for col in headers])
    wb.save(output_path)
    logging.info(f"Excel file written to {output_path} with {len(assembled_rows)} rows.")
    return True


def main(argv: Optional[Iterable[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    args = parse_args(argv)
    success = run_pipeline(args.input, args.output)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())