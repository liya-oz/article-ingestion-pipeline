# Excel Output Schema – for `result.xlsx` schema

## 1. Goals

- Satisfy rubric (title, abstract, year, authors, author gender, countries, references).
- Keep the schema minimal but future-proof.
- Separate **human-readable** columns from **technical/JSON** columns.
- Make provenance and errors explicit for auditability.

---

## 2. Final Column Set

A single sheet with one row per DOI is used. All columns are present for every row (may be empty).

### 2.1 Human-Readable Columns

1. **doi**
   - Normalized DOI.
   - Primary key for the row.

2. **title**
   - Article title from Crossref (OpenAlex may override later).
   - Plain text, human-readable.

3. **abstract**
   - Abstract text.
   - Empty for now; will be filled from OpenAlex in a later step.

4. **year**
   - Year of publication.
   - Integer or blank if missing/not parseable.

5. **author_first_names**
   - Pipe-separated given names, e.g. `Alice|Bob`.
   - Derived from `record["authors"]`.

6. **author_last_names**
   - Pipe-separated family names, e.g. `Smith|Jones`.

7. **author_genders**
   - Pipe-separated values, e.g. `unknown|unknown`.
   - For MVP: all `"unknown"`; later will use Genderize.

8. **countries_research**
   - Semicolon-separated ISO country codes, e.g. `KE;UG`.
   - Empty for now; later filled via text + affiliation detection.

9. **references_count**
   - Integer number of references.
   - Computed as `len(record["references"])`.

10. **references_list**
    - Newline-separated references.
    - Prefer DOI when present; otherwise use the best available raw string.
    - One reference per line.

---

### 2.2 Technical / Provenance / JSON Columns

11. **openalex_id**
    - OpenAlex work ID.
    - `None`/empty for now; will be set when OpenAlex is integrated.

12. **country_detection_method**
    - Provenance for the country field.
    - Values: `"detected_in_text"`, `"affderived_from_affiliations"`, or `"no_country_detected"`.

13. **provenance**
    - JSON string of the per-field provenance dict.
    - Example: `{"title": "crossref", "abstract": "missing", "authors": "crossref", "references": "crossref"}`.

14. **authors_json**
    - JSON string representing the full `authors` list.
    - Each author: `{"given": str, "family": str}` (later may add `gender` etc.).

15. **references_json**
    - JSON string representing the full `references` list.
    - Each reference: `{"raw": str, "doi": Optional[str]}`.

16. **metadata_errors**
    - Semicolon-separated error/warning messages.
    - Combines input validation issues, Crossref fetch problems, and parser warnings.

---

## 3. Mapping from Canonical Record

Canonical record fields (MVP):

- `doi: str`
- `title: str`
- `abstract: str`
- `year: Optional[int]`
- `authors: List[Dict{"given","family"}]`
- `references: List[Dict{"raw","doi"}]`
- `openalex_id: Optional[str]`
- `countries: List[str]`
- `author_genders: str` (conceptually from authors; MVP uses `"unknown"`)
- `: str`
- `provenance: Dict[str, str]`
- `metadata_errors: List[str]`

Excel row mapping:

- `doi` ← `record["doi"]`
- `title` ← `record["title"]`
- `abstract` ← `record["abstract"]`
- `year` ← `record["year"]` (blank if `None`)
- `author_first_names` ← pipe-join of all `author["given"]`
- `author_last_names` ← pipe-join of all `author["family"]`
- `author_genders` ← pipe-join of `'unknown'` (one per author) in MVP
- `countries_research` ← semicolon-join of `record["countries"]` (empty list → empty string)
- `references_count` ← `len(record["references"])`
- `references_list` ← newline-join of each reference: `doi` if present else `raw`
- `openalex_id` ← `record["openalex_id"] or ""`
- `country_detection_method` ← `record["country_detection_method"]`
- `provenance` ← `json.dumps(record["provenance"])`
- `authors_json` ← `json.dumps(record["authors"])`
- `references_json` ← `json.dumps(record["references"])`
- `metadata_errors` ← `"; ".join(record["metadata_errors"])`

---

## 4. Rationale

- **Grading:** All fields are clearly visible and easy to inspect.
- **MVP simplicity:** No extra columns beyond what we need for scoring and a small, well-justified set of technical fields.
- **Future-proofing:** JSON columns (`authors_json`, `references_json`) and `provenance` make it straightforward to:
  - Add OpenAlex data (abstracts, affiliations),
  - Add Genderize enrichment,
  - Add country detection,
  - And later build graph/RAG structures without changing the Excel schema.
- **Transparency:** `metadata_errors` clearly surfaces data quality and robustness to the reviewers.

This schema will directly drive the implementation of `assemble_row(record: Dict) -> Dict` and the structure of `result.xlsx`.
