### Canonical Article Record (MVP)

| Field name                 | Type           | Purpose / Notes                                                                 |
| -------------------------- | -------------- | ------------------------------------------------------------------------------- |
| `doi`                      | str            | Normalized DOI (primary key for the row).                                       |
| `title`                    | str            | Article title (Crossref now; OpenAlex can override later).                      |
| `abstract`                 | str            | Abstract text (empty for now; filled from OpenAlex later).                      |
| `year`                     | Optional[int]  | Year of publication; `None` if not parseable.                                   |
| `authors`                  | List[Dict]     | `{"given": str, "family": str}` from Crossref; later can add `gender`.          |
| `references`               | List[Dict]     | `{"raw": str, "doi": Optional[str]}` as parsed from Crossref.                   |
| `openalex_id`              | Optional[str]  | `None` for now; set from OpenAlex later.                                        |
| `countries`                | List[str]      | ISO-like country codes; empty for now (will use text+affiliations).             |
| `author_genders`           | str            | Derived from `authors` + enrichment later (`unknown` for now).                  |
| `country_detection_method` | str            | `"no_country_detected"` , `"detected_in_text"` , `"derived_from_affiliations"`. |
| `provenance`               | Dict[str, str] | Per-field source, e.g. `{"title": "crossref", "abstract": "missing"}`.          |
| `metadata_errors`          | List[str]      | Per DOI: includes parser `warnings`, fetch errors, etc.                         |

---

**Notes and Future Extension:**

- No separate `references_dois` or `references_count` fields; compute from `references` if/when needed.
- No extra nested provenance per field beyond a flat `provenance` dict for now.
- No OpenAlex-specific fields yet beyond `openalex_id` (future: add affiliations, abstract, etc.).

**Handling Parser Warnings:**

- The `parse_crossref_response` function returns `warnings: List[str]`.
- In your canonical record construction, always copy these to `metadata_errors`, and append further errors as needed (e.g., `"crossref_fetch_failed: ..."`).
