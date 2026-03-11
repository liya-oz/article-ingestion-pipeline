# Academic Article Metadata Pipeline

Extract, enrich, and export academic article metadata using public APIs. Designed for reproducibility and robust error handling.

## Features

- Fetches metadata from Crossref and OpenAlex
- Author gender enrichment (Genderize.io)
- Research country detection
- Caching for reproducibility
- Excel export with provenance tracking

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure cache directories exist:

- cache/crossref/
- cache/openalex/
- cache/genderize/

## Usage

Run:

```bash
python pipeline.py --input <input_csv> --output <output_excel>
```

## Contributing

Open issues or submit pull requests for improvements.

## License

MIT License

### 3. Extract References and Filter DOIs (Step 2)

#### Task 1: Extract References and Filter DOIs from Excel

```
python3 step2_prepare_references.py --input step1.xlsx --allrefs cache/references/all_references.csv --doirefs cache/references/doi_references.csv
```

- Reads the `references_list` column from `step1.xlsx`.
- Writes all reference strings to `all_references.csv`.
- Filters and writes only DOIs (those starting with "10.") to `doi_references.csv`.

The file `doi_references.csv` is used as input for further metadata enrichment and filtering.

To run Unit test: pytest -q

#### Task 2: Filter DOIs Only (If you already have `all_references.csv`)

```
python3 step2_prepare_references.py --filteronly --allrefs cache/references/all_references.csv --doirefs cache/references/doi_references.csv
```

- Reads existing `all_references.csv`.
- Filters and writes only DOIs to `doi_references.csv`.

---

### Result

After running these commands, you will have:

- `step1.xlsx` — Metadata for the 20 target articles.
- `cache/references/all_references.csv` — All references extracted.
- `cache/references/doi_references.csv` — Only DOIs, ready for further steps.
- `doi_from_references_with_metadata.xlsx` — Metadata for DOIs found in references (after enrichment step).
- `doi_from_references_with_metadata_filtered_2016plus_5refs_5countries.xlsx` — Filtered articles by year, reference count, and country (from step2_filter_doi_metadata.py).

---

For more details, see [architecture_plan.md](architecture_plan.md), [canonical_article_record.md](canonical_article_record.md), and [excel_schema.md](excel_schema.md).
