"""
How to get filtered DOI references:

1. Ensure you have all_references.csv in cache/references/.
2. Run the following command in your terminal:
    python3 step2_prepare_references.py --filteronly --allrefs cache/references/all_references.csv --doirefs cache/references/doi_references.csv
3. The filtered DOIs will be saved in cache/references/doi_references.csv.
"""

import pandas as pd
import csv


def extract_and_filter_references(input_excel, all_refs_csv, doi_refs_csv):
    # ...existing code...
    df = pd.read_excel(input_excel)
    all_references = []
    for refs in df["references_list"]:
        if pd.isna(refs):
            continue
        if isinstance(refs, str):
            split_refs = refs.split(";")
            all_references.extend([r.strip() for r in split_refs if r.strip()])
        elif isinstance(refs, list):
            all_references.extend(refs)
    with open(all_refs_csv, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["reference"])
        for ref in all_references:
            writer.writerow([ref])

def filter_dois_from_csv(all_refs_csv, doi_refs_csv):
    """
    Reads all_references.csv and writes only DOIs (starting with '10.') to doi_references.csv.
    """
    doi_list = []
    with open(all_refs_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ref = row["reference"]
            # Split by newlines in case multi-line cell
            lines = ref.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("10."):
                    doi_list.append(line)
    with open(doi_refs_csv, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["doi"])
        for doi in doi_list:
            writer.writerow([doi])



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract and filter references from Excel file or filter DOIs from CSV.")
    parser.add_argument("--input", help="Input Excel file (e.g., step1.xlsx)")
    parser.add_argument("--allrefs", help="Output CSV for all references")
    parser.add_argument("--doirefs", required=True, help="Output CSV for DOI references")
    parser.add_argument("--filteronly", action="store_true", help="Only filter DOIs from all_references.csv")
    args = parser.parse_args()
    if args.filteronly:
        if not args.allrefs:
            parser.error("--allrefs is required when --filteronly is used.")
        filter_dois_from_csv(args.allrefs, args.doirefs)
    else:
        if not args.input or not args.allrefs:
            parser.error("--input and --allrefs are required unless --filteronly is used.")
        extract_and_filter_references(args.input, args.allrefs, args.doirefs)