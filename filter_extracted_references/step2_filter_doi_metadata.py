import argparse

import pandas as pd


TARGET_COUNTRIES = ["Nigeria", "Kenya", "Ethiopia", "Tanzania", "Rwanda"]


def filter_metadata(input_excel: str, output_excel: str) -> None:
    """Filter rows based on year, references_count, and focus countries.

    Conditions:
    - year >= 2016
    - references_count >= 5
    - countries_research includes at least one of TARGET_COUNTRIES
    """
    df = pd.read_excel(input_excel)

    # Ensure numeric types for filtering
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["references_count"] = pd.to_numeric(df["references_count"], errors="coerce").fillna(0)

    mask_year = df["year"] >= 2016
    mask_refs = df["references_count"] >= 5

    # Countries: match if any of the focus countries appears in countries_research
    countries_series = df["countries_research"].fillna("").astype(str).str.lower()
    mask_country = False
    for country in TARGET_COUNTRIES:
        mask_country |= countries_series.str.contains(country.lower())

    filtered = df[mask_year & mask_refs & mask_country]

    # Write filtered result to a new Excel file
    filtered.to_excel(output_excel, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Filter doi_from_references_with_metadata.xlsx to articles "
            "published from 2016 onwards, with at least 5 references, "
            "and focused on Nigeria, Kenya, Ethiopia, Tanzania, or Rwanda."
        )
    )
    parser.add_argument(
        "--input",
        default="doi_from_references_with_metadata.xlsx",
        help="Input Excel file with metadata (default: doi_from_references_with_metadata.xlsx)",
    )
    parser.add_argument(
        "--output",
        default="doi_from_references_with_metadata_filtered_2016plus_5refs_5countries.xlsx",
        help=(
            "Output Excel file for filtered data "
            "(default: doi_from_references_with_metadata_filtered_2016plus_5refs_5countries.xlsx)"
        ),
    )

    args = parser.parse_args()
    filter_metadata(args.input, args.output)


if __name__ == "__main__":
    main()
