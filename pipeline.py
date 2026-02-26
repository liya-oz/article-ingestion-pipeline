#!/usr/bin/env python3
"""MVP pipeline: read DOI CSV and output step1.xlsx.

This script reads a list of DOIs from a CSV file, queries
public APIs (e.g., Crossref and OpenAlex), and writes a
Graph RAG–friendly Excel file (step1.xlsx) with one row per DOI.

Usage example:
    python pipeline.py --input ./doi_list_laterite_Jan2026.csv \
                       --output ./step1.xlsx
"""

import argparse
import csv
import logging
import os
import sys
from typing import Optional, Iterable, List

try:
    import openpyxl
    from openpyxl import Workbook
except Exception:  # pragma: no cover - optional dependency for dry runs
    openpyxl = None  # type: ignore[assignment]
    Workbook = None  # type: ignore[assignment]

# Per instructions: default input path and output name
DEFAULT_INPUT = "/Users/yuliiaozkan/Desktop/laterite_assessment/doi_list_laterite_Jan2026.csv"
DEFAULT_OUTPUT = "step1.xlsx"

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


def read_input(csv_path: str) -> List[str]:
    """Read DOIs from an input CSV file.

    Returns a list of *original* DOI strings (one per row).

    Strategy:
    - Use csv.DictReader.
    - If there is a 'doi' column (case-insensitive), use that.
    - Otherwise, fall back to the first column.
    """
    rows: List[str] = []

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        doi_col = None
        for name in fieldnames:
            if name.lower() == "doi":
                doi_col = name
                break

        for row in reader:
            if doi_col is not None:
                doi_val = row.get(doi_col, "")
            elif fieldnames:
                # Use first column as fallback
                doi_val = row.get(fieldnames[0], "")
            else:
                doi_val = ""

            rows.append(doi_val)

    return rows


def ensure_cache_dirs() -> None:
    """Ensure that required cache directories exist.

    Creates:
    - cache/crossref
    - cache/openalex
    - cache/genderize
    """
    for d in CACHE_DIRS:
        os.makedirs(d, exist_ok=True)


def write_header_excel(output_path: str) -> None:
    """Create an Excel file with the expected header row.

    Header columns (no data rows):
    doi,title,abstract,year,author_first_names,author_last_names,
    author_genders,countries_research,references_list,metadata_errors
    """
    if Workbook is None:
        raise RuntimeError(
            "openpyxl is not installed; cannot write Excel file. "
            "Install requirements with `pip install -r requirements.txt`."
        )

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
    ws.title = "step1"

    # Write header row
    ws.append(headers)

    wb.save(output_path)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="MVP pipeline: reads DOI CSV and outputs step1.xlsx"
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read input and print 'original → normalized' per DOI instead of writing Excel.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def run_pipeline(input_path: str, output_path: str, dry_run: bool) -> None:
    """Main orchestration logic.

    - Always ensure cache directories exist.
    - If dry_run: read input and print 'original → normalized' per DOI.
    - Else: create header-only Excel file.
    """
    ensure_cache_dirs()

    if dry_run:
        logging.info("Running in dry-run mode.")
        try:
            dois = read_input(input_path)
        except FileNotFoundError as e:
            logging.error(str(e))
            return

        if not dois:
            logging.warning("No rows found in input CSV.")
            return

        print("Dry run: original → normalized DOIs")
        for idx, original in enumerate(dois, start=1):
            normalized = normalize_doi(original)
            if not normalized:
                print(f"[SKIP] Row {idx}: invalid/empty DOI: {repr(original)}")
            else:
                print(f"Row {idx}: {repr(original)} → {repr(normalized)}")
    else:
        logging.info("Writing header-only Excel file.")
        write_header_excel(output_path)
        logging.info("Done.")


def main(argv: Optional[Iterable[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    args = parse_args(argv)
    run_pipeline(args.input, args.output, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())