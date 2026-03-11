# MVP Architecture Plan

## 1. Objective

**Input:** CSV with ~20 DOIs  
**Output:** `step1.xlsx` with one row per article containing:

- Article Title
- Abstract
- Year Published
- Author first name(s)
- Author last name(s)
- Author gender(s)
- Countries where the research took place
- Complete list of references from the article

**Constraints:** Reproducible, publicly available APIs only, graceful handling of missing data.

---

## 2. Data Sources

### Primary APIs (2 sources only)

1. **Crossref API** – title, year, authors, references
2. **OpenAlex API** – abstract, affiliations, backup metadata

### Enrichment Services

3. **Genderize.io** – author gender inference (cached)

**Rationale:** Minimal API surface reduces failure modes while maximizing field coverage.

---

## 3. Field Extraction Strategy

| Field           | Primary Source  | Fallback     | Notes                           |
| --------------- | --------------- | ------------ | ------------------------------- |
| Title           | Crossref        | OpenAlex     | Store as-is                     |
| Year            | Crossref        | OpenAlex     | Integer only                    |
| Abstract        | OpenAlex        | Crossref     | Reconstruct from inverted index |
| Authors (names) | Crossref        | OpenAlex     | Keep given/family separate      |
| Author gender   | Genderize       | —            | Probabilistic; threshold 0.8    |
| Countries       | Text extraction | Affiliations | See §4                          |
| References      | Crossref        | OpenAlex     | DOI + unstructured              |

---

## 4. Operationalized Definitions

### 4.1 Author Gender

- Use first given name only
- If initials only or probability < 0.8 → `unknown`
- Cache all API responses locally for reproducibility

### 4.2 Countries of Research

**Two-stage approach:**

1. **Primary:** Extract country names from title + abstract using dictionary matching
   - ISO 3166-1 alpha-2 codes
   - Handle variants (US/USA/United States)

2. **Fallback:** Use author affiliation countries from OpenAlex

**Output:** Report both; use text-based if available, else affiliations.

### 4.3 References

- Store DOI if available
- Store unstructured string as fallback
- Count must match actual list length

---

## 5. Excel Output Schema

### Required Columns (Human-Readable)

1. `doi` – normalized input DOI
2. `title`
3. `abstract`
4. `year`
5. `author_first_names` – pipe-separated
6. `author_last_names` – pipe-separated
7. `author_genders` – pipe-separated (e.g., `female|male|unknown`)
8. `countries_research` – semicolon-separated ISO codes
9. `references_count`
10. `references_list` – newline-separated

### Provenance Columns (Future-Proof)

11. `openalex_id`
12. `countries_method` – `text|affiliations|missing`
13. `references_dois` – semicolon-separated
14. `metadata_errors` – error messages

---

## 6. Pipeline Architecture

```
[Input: CSV]
    ↓
[Step 1: Load & Normalize DOIs]
    ↓
[Step 2: Fetch Metadata (Crossref + OpenAlex)] ← cache enabled
    ↓
[Step 3: Extract Core Fields] → provenance tracking
    ↓
[Step 4: Enrich Author Gender] ← Genderize cache
    ↓
[Step 5: Detect Research Countries] → text + affiliation
    ↓
[Step 6: Export to step1.xlsx]
```

---

## 7. Implementation Steps

### Step 1: Setup

- Install dependencies: `pandas`, `requests`, `openpyxl`, `pycountry`
- Create cache directories: `cache/crossref/`, `cache/openalex/`, `cache/genderize/`

### Step 2: Data Fetching

```python
def fetch_crossref(doi):
    # GET https://api.crossref.org/works/{doi}
    # Cache to cache/crossref/{hash}.json

def fetch_openalex(doi):
    # GET https://api.openalex.org/works/https://doi.org/{doi}
    # Cache to cache/openalex/{hash}.json
```

### Step 3: Field Extraction

```python
def extract_metadata(crossref_data, openalex_data):
    return {
        'title': crossref_data.get('title')[0] or openalex_data.get('title'),
        'year': parse_year(crossref_data or openalex_data),
        'authors': extract_authors(crossref_data, openalex_data),
        'abstract': reconstruct_abstract(openalex_data) or crossref_data.get('abstract'),
        'references': extract_references(crossref_data, openalex_data),
        # ... provenance fields
    }
```

### Step 4: Gender Enrichment

```python
def enrich_gender(authors, threshold=0.8):
    for author in authors:
        first_name = author['given'].split()[0]
        gender_data = genderize_cached(first_name)
        if gender_data['probability'] >= threshold:
            author['gender'] = gender_data['gender']
        else:
            author['gender'] = 'unknown'
```

### Step 5: Country Detection

```python
def detect_countries(title, abstract, affiliations):
    # Dictionary match on title + abstract
    text_countries = extract_countries_from_text(title + ' ' + abstract)

    if text_countries:
        return text_countries, 'text'

    # Fallback to affiliations
    affil_countries = [a['country_code'] for a in affiliations if a.get('country_code')]
    return affil_countries or [], 'affiliations' if affil_countries else 'missing'
```

### Step 6: Excel Export

```python
df = pd.DataFrame(processed_articles)
df.to_excel('step1.xlsx', index=False, engine='openpyxl')
```

---

## 8. Error Handling

- **Per-DOI try/except:** Never fail entire run for one bad DOI
- **Missing data:** Use empty string for text fields, empty list for arrays
- **Track errors:** Populate `metadata_errors` column with messages
- **API failures:** Use cached data if available; mark as error if not

---

### Crossref + OpenAlex Fallback Policy (MVP)

- The pipeline uses Crossref as the primary metadata source, with OpenAlex as a secondary backup for explicit per-field fallbacks.
- Fields that can be sourced from OpenAlex include: title, abstract, year, authors, countries, and openalex_id.
- For each field, only one source is chosen (never mixed); the provenance dict records the source, and any issues or fallbacks are tracked in the metadata_errors column.
- This approach ensures clear, reproducible provenance for every field and robust handling of missing or incomplete data.

---

#### Country Vocabulary Source

For country detection, I use a standardized mapping of ISO 3166-1 alpha‑2 codes to English country names taken directly from the [`umpirsky/country-list`](https://github.com/umpirsky/country-list) repository.

- It provides a dict of the form:

  ```json
  {
    "AF": "Afghanistan",
    "AX": "Åland Islands",
    "AL": "Albania",
    "DZ": "Algeria",
    "AS": "American Samoa",
    "AD": "Andorra",
    "AO": "Angola",
    ...
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VU": "Vanuatu",
    "VA": "Vatican City",
    "VE": "Venezuela",
    "VN": "Vietnam",
    "WF": "Wallis & Futuna",
    "EH": "Western Sahara",
    "YE": "Yemen",
    "ZM": "Zambia",
    "ZW": "Zimbabwe"
  }
  ```

- This mapping is used as the canonical country vocabulary for:
  - matching country names in title/abstract text, and
  - normalizing country codes from affiliations (e.g., OpenAlex `country_code` fields).

Using this list ensures that all country names and codes are based on a well‑known, publicly available source and remain reproducible across runs.

---

## 9. Reproducibility Requirements

1. **Cache all API responses** with timestamp
2. **Pin dependencies** in `requirements.txt`
3. **Single command execution:** `python pipeline.py --input dois.csv --output step1.xlsx`
4. **Deterministic output:** Same input order preserved in Excel

---

## 10. Known Limitations

- **Gender:** Probabilistic inference from first names; not verified
- **Countries:** Operationalized as text mentions (primary) or affiliations (fallback); not ground truth research location
- **References:** Completeness depends on API metadata availability
- **Abstract:** May be missing for older articles or certain publishers

---

## 11. Success Criteria (Scoring Focus)

✓ All 8 required fields present  
✓ Handles missing data gracefully  
✓ Reproducible from DOI list  
✓ Clear provenance/methodology  
✓ Professional Excel output

**Risk mitigation:** Two-source strategy + explicit fallbacks maximize field coverage.
