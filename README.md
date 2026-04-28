# Research Data Pipeline

An automated system for transforming fragmented scholarly metadata into a structured, analysis-ready dataset. Built on publicly available APIs, the pipeline emphasizes reproducibility, transparency, and fault-tolerant design.

At its core, this project is a research data automation pipeline: it ingests a minimal input (a list of DOIs) and produces a consistent, enriched dataset suitable for quantitative analysis and downstream computational workflows.

It replaces a traditionally manual, error-prone process with a deterministic and repeatable system.

---

The workflow begins with a simple CSV file containing DOIs. From this input, the pipeline executes a fully automated sequence:

* **Metadata aggregation** from Crossref, OpenAlex, and Semantic Scholar  
* **Field standardization** across heterogeneous sources  
* **Data enrichment**, including probabilistic gender inference and geographic extraction  
* **Robust handling of incomplete or inconsistent records**  
* **Export to a structured Excel dataset with full provenance tracking**

The result is a single, coherent table where each row represents an article and each column is normalized, interpretable, and ready for analysis.

---

## Why

Scholarly metadata is widely available but poorly standardized across sources. This pipeline addresses that gap by:

* minimizing dependency complexity while leveraging complementary APIs  
* applying explicit fallback strategies across multiple sources  
* encoding assumptions and limitations transparently  

The outcome is a **practical, reproducible approach to metadata integration**, aligned with the needs of modern computational research.

---

## Research Applications

The generated dataset enables immediate exploration of:

* geographic distribution of research activity  
* gender patterns in authorship  
* temporal publication trends  
* citation structures and reference networks  

Because the pipeline standardizes and enriches metadata, it supports both **descriptive analysis** and **integration into larger computational frameworks**.

---

## Adapted for Data-Driven Research

Beyond standalone analysis, the output serves as a **data ingestion layer** for:

* statistical modeling and machine learning  
* retrieval-augmented generation (RAG) systems  
* knowledge graph construction  
* interactive dashboards and visualization tools  

---

## Reproducibility and Provenance

A key design principle is **reproducibility**:

* all API responses are cached  
* identical inputs yield identical outputs  
* each field retains clear source attribution  

---

## Architecture

**ETL pipeline:**

* **Extract** → Crossref, OpenAlex, Semantic Scholar  
* **Transform** → normalization and enrichment  
* **Load** → Excel dataset 

---

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
python3 step2_prepare_references.py --input result.xlsx --allrefs cache/references/all_references.csv --doirefs cache/references/doi_references.csv
```

- Reads the `references_list` column from `result.xlsx`.
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

- `result.xlsx` — Metadata for the 20 target articles.
- `cache/references/all_references.csv` — All references extracted.
- `cache/references/doi_references.csv` — Only DOIs, ready for further steps.
- `doi_from_references_with_metadata.xlsx` — Metadata for DOIs found in references (after enrichment step).
- `doi_from_references_with_metadata_filtered_2016plus_5refs_5countries.xlsx` — Filtered articles by year, reference count, and country (from step2_filter_doi_metadata.py).

---

For more details, see [architecture_plan.md](architecture_plan.md), [canonical_article_record.md](canonical_article_record.md), and [excel_schema.md](excel_schema.md).
