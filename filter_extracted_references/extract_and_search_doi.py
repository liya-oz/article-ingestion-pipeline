import re
import csv
import requests
from time import sleep

def is_doi(line):
    # DOI pattern: starts with 10. and has a slash
    return bool(re.match(r"^10\.\S+/\S+", line.strip()))

def is_url(line):
    return line.strip().startswith("http")

def is_reference(line):
    # Heuristic: contains a year in parentheses and at least one comma (author, year, title, etc.)
    return bool(re.search(r"\(\d{4}\)", line)) and "," in line

def search_crossref(reference):
    url = "https://api.crossref.org/works"
    params = {"query.bibliographic": reference, "rows": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            items = r.json().get("message", {}).get("items", [])
            if items:
                return items[0].get("DOI", "")
    except Exception:
        pass
    return ""

def process_references(input_csv, output_csv):
    total = 0
    found = 0
    print(f"Processing references from: {input_csv}")
    print(f"DOI results will be stored in: {output_csv}")
    with open(input_csv, "r", encoding="utf-8") as infile, open(output_csv, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["reference", "found_doi"])
        for line in infile:
            line = line.strip()
            if not line or is_doi(line) or is_url(line):
                continue
            if is_reference(line):
                total += 1
                print(f"[{total}] Searching DOI for: {line[:80]}{'...' if len(line) > 80 else ''}")
                doi = search_crossref(line)
                if doi:
                    found += 1
                    print(f"    -> DOI found: {doi}")
                else:
                    print("    -> DOI not found")
                writer.writerow([line, doi])
                sleep(1)  # be polite to API
    print(f"\nDone. {found} DOIs found out of {total} references.")

if __name__ == "__main__":
    process_references(
        "/Users/yuliiaozkan/Desktop/data_pipeline/academic-article-ingestion-pipeline/cache/references/all_references.csv",
        "/Users/yuliiaozkan/Desktop/data_pipeline/academic-article-ingestion-pipeline/cache/references/references_with_dois.csv"
    )
