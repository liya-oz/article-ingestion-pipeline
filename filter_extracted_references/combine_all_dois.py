import csv

doi_set = set()

# Collect DOIs from doi_references.csv
doi_refs_path = "cache/references/doi_references.csv"
with open(doi_refs_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        doi = row['doi'].strip()
        if doi:
            doi_set.add(doi)

# Collect DOIs from references_with_dois.csv
refs_with_dois_path = "cache/references/references_with_dois.csv"
with open(refs_with_dois_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        doi = row['found_doi'].strip()
        if doi:
            doi_set.add(doi)

# Write all unique DOIs, one per line, no header, no 'doi:' prefix
target_path = "cache/references/combined_all_dois.csv"
with open(target_path, 'w', encoding='utf-8') as f:
    for doi in sorted(doi_set):
        f.write(doi + '\n')

print(f"Combined {len(doi_set)} unique DOIs written to {target_path} (one per line, no header, no prefix)")
