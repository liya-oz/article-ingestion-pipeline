# Copilot Chat Conversation Export: | API | Data Fields Covered

**User:** @liya-oz
**Thread URL:** https://github.com/copilot/c/67a1416c-f08d-4dc4-95dc-b2364bc22169

## @liya-oz

I’m building an MVP Python pipeline: input = CSV of 20 DOIs; output = `step1.xlsx` with with one row per article: metadata (title, abstract, year, authors, author gender, countries of research, full reference list). Must be reproducible end-to-end using publicly available APIs; handle missing/incomplete metadata. I want a design suitable as a future input to a Graph RAG system like stable IDs, normalized fields.

List the main technical sub-problems I need to solve. Please group them by pipeline stage (input normalization, retrieval, enrichment, parsing, output formatting, QA/validation) and call out likely edge cases per stage.

## Copilot

## 1) Input normalization (CSV → canonical DOI list)

### Sub-problems
- **CSV ingestion & schema detection**
  - Detect which column contains DOIs (or accept a configured column name).
  - Support headers/no-headers, varying delimiters, quoting, UTF-8/Windows-1252.
- **DOI extraction & cleanup**
  - Extract DOI tokens from messy strings (URLs, prefixes, “doi:”, whitespace).
  - Normalize to a canonical form (typically lowercase, stripped).
- **Deduplication & stable ID assignment**
  - Deduplicate after normalization.
  - Assign stable internal IDs for reproducibility and graph linking (e.g., `article_id = "doi:" + normalized_doi`).
- **Input audit trail**
  - Preserve the original raw string, source row index, and normalization actions.

### Likely edge cases
- DOI presented as:
  - `https://doi.org/10.xxxx/yyy`, `doi:10.xxxx/yyy`, or embedded in text.
- Trailing punctuation: `10.1000/xyz.`, `10.1000/xyz)`.
- Multiple DOIs in one cell, or DOI split across fields.
- Non-DOI identifiers mistaken as DOI.
- Duplicate DOIs differing only by case or URL form.

---

## 2) Retrieval (public APIs → baseline metadata, reproducible)

### Sub-problems
- **Source selection & fallback strategy (multi-provider)**
  - Primary DOI resolver/metadata: Crossref is common for bibliographic metadata.
  - Abstract availability: often limited in Crossref; may need OpenAlex, PubMed (when applicable), or publisher endpoints (when open).
  - References: Crossref may include reference lists for some items; otherwise OpenAlex or Semantic Scholar can help when permitted.
- **Deterministic request plan**
  - For each DOI, define an ordered list of APIs to query, with clear “stop conditions.”
  - Record which source won each field (provenance) and when it was fetched.
- **Resilience & rate limiting**
  - Retries with exponential backoff, timeouts, circuit-breaking.
  - Respect API rate limits; optionally cache responses to disk.
- **Reproducibility controls**
  - Store raw JSON responses (or hashes + timestamps).
  - Pin your own pipeline version; make output deterministic given stored raw inputs.

### Likely edge cases
- DOI not found in one API but present in another.
- Retracted items, corrections, or “posted-content” / preprints.
- Multiple works mapped to a DOI (rare but happens due to metadata merges/errors).
- Rate-limited (429), transient failures (5xx), slow endpoints.
- Inconsistent licensing/terms: some APIs may not return abstracts or references for certain items.

---

## 3) Enrichment (normalize fields + infer missing attributes)

### Sub-problems
- **Field normalization for “graph-ready” entities**
  - **Stable IDs** for core entities:
    - Work: `doi:<doi>` (primary) plus secondary IDs (OpenAlex ID, PMID, etc.).
    - Author: ORCID when available; else derive a stable pseudo-ID (careful: collisions).
    - Institution / Country: use standardized IDs where possible (ROR for institutions; ISO-3166 for countries).
  - **Normalized strings**: title case handling, Unicode normalization, whitespace cleanup.
- **Year normalization**
  - Decide precedence: published-online vs published-print vs issued date.
  - Output both `year` and the full normalized date fields when possible.
- **Author normalization**
  - Parse author list to structured fields: given/family, full name, ORCID, affiliation.
  - Create consistent author ordering and “et al.” handling.
- **Gender inference (author gender)**
  - Pick a method that is:
    - Reproducible (same input → same output),
    - Transparent (store confidence and method),
    - Ethically cautious (allow “unknown/ambiguous”).
  - Usually requires a name-to-gender service or dataset; if you must stay purely public, ensure the API is publicly accessible and document limitations.
- **Country inference (“countries of research”)**
  - Define what this means operationally:
    - Author affiliation countries?
    - Corresponding author only?
    - Study location (rarely in metadata)?
  - Implement extraction from affiliation strings and/or institution identifiers → country mapping.

### Likely edge cases
- Authors with only initials, mononyms, non-Latin scripts.
- Missing affiliations; affiliations only as free text.
- ORCID absent or malformed.
- Gender inference failure for:
  - Initials-only names,
  - Uncommon names,
  - Cross-cultural ambiguity.
- “Countries of research” ambiguous when:
  - Multi-country collaborations,
  - Affiliations missing,
  - Institutions are global/virtual.

---

## 4) Parsing (abstracts + references + text fields into structured forms)

### Sub-problems
- **Abstract parsing**
  - Abstracts may arrive as:
    - Plain text,
    - HTML,
    - JATS XML fragments (common in Crossref abstracts),
    - Missing entirely.
  - Implement cleaning and a canonical “abstract_text” output.
- **Reference list parsing & normalization**
  - References may be:
    - Already structured (author/year/journal/DOI),
    - Semi-structured strings,
    - Missing, partial, or noisy.
  - Normalize to a consistent schema per reference:
    - `ref_index`, `ref_raw`, `ref_doi`, `ref_title`, `ref_year`, `ref_venue`, etc.
  - Decide how to represent the full reference list in Excel:
    - Single cell as JSON/text block, or
    - Separate sheet (often better for 1-to-many).
- **Identifier extraction from references**
  - Extract DOIs, PMIDs, arXiv IDs from reference strings when present.
- **De-HTML / de-XML and entity decoding**
  - Handle italics, superscripts, special characters safely.

### Likely edge cases
- Abstract returned as JATS with tags like `<jats:p>`; nested formatting.
- Reference list truncation limits in some APIs.
- References with no DOI; books, reports, datasets, websites.
- Duplicate references, inconsistent numbering, or missing order.
- Non-ASCII punctuation and encoding artifacts.

---

## 5) Output formatting (to `step1.xlsx`, one row per article)

### Sub-problems
- **Define the output schema (graph-friendly)**
  - Use consistent, explicit column names and types, e.g.:
    - `work_id`, `doi`, `title`, `abstract`, `publication_year`
    - `authors` (JSON), `author_ids`, `author_genders` (JSON with confidence)
    - `countries` (ISO codes list), `institutions` (ROR list)
    - `references` (JSON) or a separate `references` sheet keyed by `work_id`
    - `source_provenance` (per-field source map), `retrieved_at`
- **Excel constraints**
  - Cell size limits (very long abstracts/reference JSON may exceed practical limits).
  - Newlines and JSON escaping for readability.
- **Deterministic ordering**
  - Keep output row order stable (e.g., same as input CSV order).
- **Missingness representation**
  - Use `NA`/empty consistently; avoid mixing `None`, `null`, blank, “Unknown”.

### Likely edge cases
- Extremely long abstracts or reference lists causing Excel bloat or truncated display.
- Unicode characters not rendering in some Excel environments.
- One-to-many fields (authors, references) awkward in a single-row format—may require additional sheets for normalization.

---

## 6) QA / validation (trustworthiness + completeness + reproducibility)

### Sub-problems
- **Schema validation**
  - Check required columns present; enforce types (year is int, DOI matches pattern).
- **Field-level quality checks**
  - Title not empty (unless truly missing).
  - Year within plausible range.
  - DOI round-trip check: normalized DOI resolves (optional).
- **Provenance & audit logs**
  - For each work and each field: record which API provided it, confidence, and raw payload location/hash.
- **Coverage reporting**
  - Summaries: % with abstracts, % with references, % with affiliation countries, % with gender inferred.
- **Re-run determinism**
  - Caching: if you cache raw API responses, re-running should reproduce the same `step1.xlsx` exactly (unless you intentionally refresh).
- **Error handling policy**
  - Per-DOI failures should not stop the run; produce a row with error fields populated.

### Likely edge cases
- Conflicting metadata between providers (two different titles/years).
- Partial updates over time (metadata changes in Crossref/OpenAlex).
- Provider outages causing uneven results unless cached.
- Silent parsing failures (e.g., malformed XML in abstract field).
- Gender/country inference producing low-confidence outputs—need thresholds and “unknown” fallback.

---

### One design choice to decide early (affects many stages)
Because you want **one row per article** *and* you need **full reference lists and authors (both one-to-many)**, decide whether to:
- keep them as **JSON-in-cell** (fast MVP, less “Excel-native”), or
- create **additional sheets** (`authors`, `references`, `affiliations`) keyed by `work_id` (more graph-ready and scalable).

If you tell me which public APIs you prefer (e.g., Crossref + OpenAlex + Semantic Scholar, or “Crossref only”), I can propose a concrete field schema for `step1.xlsx` and a deterministic “source priority” plan.

## @liya-oz

Same project context. I need APIs that can resolve DOIs to: title, abstract, year, authors and references. Propose open APIs

## Copilot

## Recommended open/public APIs (DOI → title, abstract, year, authors, references)

### 1) Crossref REST (best baseline for bibliographic metadata; references sometimes)
- **What you reliably get:** title, publication year/date fields, authors (often), journal/venue, publisher, type, sometimes references.
- **Abstract:** occasionally present, but coverage is limited (and often in JATS/XML when present).
- **References:** included for some publishers/items as `reference[]` (often partial; may lack DOIs).
- **How to query by DOI:** `GET https://api.crossref.org/works/{doi}`
- **Pros:** open, no key required, DOI-native, good metadata coverage.
- **Cons:** abstracts and references are not guaranteed.

### 2) OpenAlex (strong for author/institution metadata; references/citations; abstracts via inverted index when available)
- **What you reliably get:** title, year, authorship list (with institutions), work IDs, concepts, and **references (as linked OpenAlex Work IDs)**.
- **Abstract:** sometimes available as an **inverted index**; not universal. You must reconstruct the text.
- **References:** strong as a graph (IDs), and you can fetch metadata for referenced works.
- **How to query by DOI:** `GET https://api.openalex.org/works/https://doi.org/{doi}` (also accepts `doi:{doi}` in filters)
- **Pros:** very graph-friendly (stable IDs for works/authors/institutions), excellent for “countries of research” via institutions.
- **Cons:** abstract coverage varies; references are IDs (you may need extra calls to get formatted strings/DOIs).

### 3) Semantic Scholar Graph API (good abstracts and references where available; DOI supported)
- **What you reliably get:** title, year, authors; often **abstract**; strong **reference lists** (as paper graph objects).
- **References:** generally good coverage; returns structured references with IDs and often DOIs.
- **How to query by DOI:** `GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=...`
- **Pros:** often better abstract + references coverage than Crossref alone; returns a coherent paper graph.
- **Cons:** may require an API key for higher throughput; field availability varies by paper; licensing/coverage differs from Crossref/OpenAlex.

### 4) Europe PMC (biomedical-focused; good abstracts + references for PubMed Central)
- **What you reliably get (when in scope):** title, authors, year, abstract (often), and references for full-text / PMC items.
- **How to query by DOI:** search endpoint by DOI; then fetch full record.
- **Pros:** excellent for life sciences; strong full-text-derived metadata when available.
- **Cons:** domain-limited (not general across all DOIs).

### 5) PubMed / NCBI E-utilities (biomedical; DOI → PMID mapping, metadata, abstract)
- **What you reliably get:** for papers indexed in PubMed: title, authors, year, abstract.
- **References:** not generally available in PubMed records themselves (references are more of a PMC/full-text thing).
- **How to query:** use DOI in search (`esearch`) then `efetch`.
- **Pros:** authoritative biomedical metadata.
- **Cons:** limited to PubMed-indexed items; references not a strength.

---

## Practical “MVP” combination that meets your fields best

### Option A (most general + graph-ready): **Crossref + OpenAlex + Semantic Scholar**
Use a deterministic priority per field:
- **Title / year / basic bibliographic:** Crossref first, fallback to OpenAlex, then Semantic Scholar
- **Abstract:** Semantic Scholar first (often best), fallback OpenAlex (reconstruct inverted index), fallback Crossref (rare)
- **Authors:** OpenAlex (best IDs + affiliations) or Crossref (good ordering), reconcile with Semantic Scholar if missing
- **References:** Semantic Scholar (structured refs) OR OpenAlex (reference graph) as fallback; Crossref references when present

This is the most reliable way to hit *all* of: title, abstract, year, authors, references across many disciplines.

### Option B (strictly “no key needed” and very open): **Crossref + OpenAlex**
- You’ll still get title/year/authors well.
- References are usually available via OpenAlex links.
- Abstract coverage may be the weakest part (depends on OpenAlex availability for your DOIs); you can’t count on having an abstract for all 20.

### Option C (biomedical-heavy DOI list): **Crossref + Europe PMC (+ PubMed utilities as needed)**
- Very good abstracts; references if you can land in full-text/PMC.
- Not appropriate if your DOI set is broad outside biomed.

---

## Notes on “open” and reproducibility
- All of the above are **publicly accessible** APIs. Some (notably Semantic Scholar) may push you toward an API key for stable throughput, but the endpoints are still publicly documented and reproducible.
- For reproducibility, whichever you choose, store:
  - the **raw JSON response** per DOI per provider (or at least a content hash),
  - `retrieved_at`,
  - the **provider + endpoint + query** used.

---

## Recommended next step (so I can tailor the exact plan)
Tell me which constraint you prefer:
1) **No API keys at all**, even if abstract coverage drops, or  
2) **Keys allowed** (still public APIs), maximizing abstract/reference completeness.

If you choose (2), I can give you an exact `fields=` specification for Semantic Scholar and a deterministic merge strategy for conflicts.

## @liya-oz

Compare. summarize in a compact table:
data fields covered well vs poorly (abstract, references, etc.)
API key needed? 
rate limits / reliability considerations
typical failure modes/ gaps
why its a good fit for this task:
Crossref REST API
 3.50.1 
/swagger-docs
Welcome to the Crossref REST API. This page contains basic information about the API, including details about available endpoints and request parameters, and options to try requests yourself. You can find additional information on our documentation website.

On this page
Request parameters
Filters
Queries
Retrieving large result sets
Selecting response fields
Facets
Sorting
Response types
Current status and errors
Endpoints
Works
Journals
Funders
Members
Prefixes
Types
Licenses
Request parameters
The request parameters available for each endpoint are given below for each endpoint. Here we provide more details about parameters with specific functionality:

Filters
Filters allow you to select items based on specific criteria and return a list. Multiple filters may be used in the same request. There are many filters available, especially for /works routes. They are described fully on our documentation website. For example:

/works?filter=from-created-date:2023-01-01T12:00:00,until-created-date:2023-01-01T13:00:00

Queries
Search queries can be made to look for the presence of one or more words in any field. For example,

/members?query=association+library

Some queries look only in one or several fields. For example,

/works?query.bibliographic=Richard+Feynmann

only incorporates fields used when referencing the content item (title, authors, volume, journal name, etc.).

Select response fields
For works endpoints, if you only need a few elements from the schema use the select parameter. For example:

/works?select=DOI,prefix,title

Retrieving large result sets
List requests return up to 1000 items in a single request. Paginating through multiple pages of results is possible using the cursor parameter. To retrieve multiple pages:

Add cursor=* to a request (and rows > 0).
The response will include a next-cursor value.
Use cursor=[next-cursor] in your next request to obtain the following page of results.
Stop sending requests when the number of items in the response is less than the number of rows requested.
Cursors expire after 5 minutes if not used.

You can also use offset:n for an integer n up to 10,000 to return results starting at the the nth record of the result set. We recommend using cursors rather than offset, since there are no page limitations and results are returned faster.

Facets
For works endpoints, retrieve summary statistics by providing a facet parameter along with the type of information, and maximum number of returned values which can be up to 1000. Use * to retrieve the maximum allowed number of values. The request format follows this example:

/works?facet=type-name:*

Note that facet counts are approximate and may differ from exact counts obtained using filters. Note that records with the same relationships two or more times are counted multiple times (e.g., records with two published corrections).

Sorting
Results on the works endpoints can be sorted. sort sets the field by which results will be sorted. order sets the result ordering, either asc or desc (the default is desc). The following example sorts results by order of publication, beginning with the oldest:

/works?query=josiah+carberry&sort=published&order=asc

Response types
Responses are in JSON format with the mime-type application/vnd.crossref-api-message+json. If you access the API via a browser, we recommend using a JSON formatter plugin. Other formats can be retrieved for singleton requests using content negotiation.

There are three types of responses:

Singleton: The metadata record of a single object. Retrieving metadata for a specific identifier (e.g., DOI, ISSN, funder identifier) returns a singleton. For example:

https://api.crossref.org/works/10.5555%2F12345678

Headers only: Use an HTTP HEAD requests to quickly determine existence of a singleton without fetching any metadata. It returns headers and an HTTP status code (200=exists, 404=does not exist). For example (in a terminal):

curl --head "https://api.crossref.org/members/98"

List: Requests with queries or filters returns a list that can contain multiple content items. The maximum number of items returned is defined by the rows parameter, which can be set to 0 to retrieve only summary information. For example:

https://api.crossref.org/funders?rows=5

Response codes
We ask that users monitor the HTTP response code for requests. We use standard codes: 200 for successful requests, 4XX for errors in the request, and 5XX for server-side errors. Some records redirect and will return a 301 response, see changing or deleting DOIs. If you see a 429 or 403 response it means you have been temporarily or permanently blocked, in which case check the response text for details on how to proceed.

Current status and errors
The current status of the API is available on our status page and social media feeds. If you see an issue that is not noted, please contact us via our community forum or directly through our support team.


Crossref - Website
Send email to Crossref
Works
Endpoints that expose works related data



GET
/works/{doi}
Returns metadata for the specified Crossref DOI, as an example use DOI 10.5555/12345678

Parameters
Cancel
Name	Description
doi *
string
(path)
The DOI identifier of the content item.

doi:10.1007/s10671-016-9199-2
Execute
Clear
Responses
Response content type

application/json
Curl

curl -X 'GET' \
  'https://api.crossref.org/works/doi%3A10.1007%2Fs10671-016-9199-2' \
  -H 'accept: application/json'
Request URL
https://api.crossref.org/works/doi%3A10.1007%2Fs10671-016-9199-2
Server response
Code	Details
200	
Response body
Download
{
  "status": "ok",
  "message-type": "work",
  "message-version": "1.0.0",
  "message": {
    "indexed": {
      "date-parts": [
        [
          2025,
          2,
          21
        ]
      "date-time": "2025-02-21T11:27:48Z",
      "timestamp": 1740137268065,
      "version": "3.37.3"
    },
    "reference-count": 52,
    "publisher": "Springer Science and Business Media LLC",
    "issue": "2",
    "license": [
      {
        "start": {
          "date-parts": [
            [
              2016,
              11,
              3
            ]
          ],
          "date-time": "2016-11-03T00:00:00Z",
          "timestamp": 1478131200000
        },
        "content-version": "unspecified",
        "delay-in-days": 0,
        "URL": "http://www.springer.com/tdm"
      }
    ],
    "funder": [
      {
        "DOI": "10.13039/100004439",
        "name": "The William and Flora Hewlett Foundation",
        "doi-asserted-by": "crossref",
        "award": [
          "2011-6393"
        ],
        "award-info": [
          {
            "award-number": [
              "2011-6393"
            ]
          }
        ],
        "id": [
          {
            "id": "10.13039/100004439",
            "id-type": "DOI",
            "asserted-by": "crossref"
          }
        ]
      }
    ],
    "content-domain": {
      "domain": [
        "link.springer.com"
      ],
      "crossmark-restriction": false
    },
    "short-container-title": [
      "Educ Res Policy Prac"
    ],
    "published-print": {
      "date-parts": [
        [
          2017,
          6
        ]
      ]
    },
    "DOI": "10.1007/s10671-016-9199-2",
    "type": "journal-article",
    "created": {
      "date-parts": [
        [
          2016,
          11,
          3
        ]
      ],
      "date-time": "2016-11-03T16:05:18Z",
      "timestamp": 1478189118000
    },
    "page": "129-155",
    "update-policy": "https://doi.org/10.1007/springer_crossmark_policy",
    "source": "Crossref",
    "is-referenced-by-count": 1,
    "title": [
      "Learning barriers among Grade 6 pupils attending rural schools in Uganda: implications to policy and practice"
    ],
    "prefix": "10.1007",
    "volume": "16",
    "author": [
      {
        "given": "Njora",
        "family": "Hungi",
        "sequence": "first",
        "affiliation": []
      },
      {
        "given": "Moses",
        "family": "Ngware",
        "sequence": "additional",
        "affiliation": []
      },
      {
        "given": "Gerald",
        "family": "Mahuro",
        "sequence": "additional",
        "affiliation": []
      },
      {
        "given": "Nelson",
        "family": "Muhia",
        "sequence": "additional",
        "affiliation": []
      }
    ],
    "member": "297",
    "published-online": {
      "date-parts": [
        [
          2016,
          11,
          3
        ]
      ]
    },
    "reference": [
      {
        "doi-asserted-by": "publisher",
        "unstructured": "Acham, H., Kikafunda, J. K., Malde, M. K., Oldewage-Theron, W. H., & Egal, A. A. (2012). Breakfast, midday meals and academic achievement in rural primary schools in Uganda: Implications for education and school health policy. Food & Nutrition Research, 56, 1–12. Accessed June 23, 2016, from http://www.ncbi.nlm.nih.gov/pmc/articles/PMC3280795/ .",
        "key": "9199_CR1",
        "DOI": "10.3402/fnr.v56i0.11217"
      },
      {
        "issue": "3",
        "key": "9199_CR2",
        "doi-asserted-by": "crossref",
        "first-page": "291",
        "DOI": "10.1086/341159",
        "volume": "46",
        "author": "DP Baker",
        "year": "2002",
        "unstructured": "Baker, D. P., Goesling, B., & Letendre, G. K. (2002). Socioeconomic status, school quality, and national economic development: A cross-national analysis of the “Heyneman–Loxley effect” on mathematics and science achievement. Comparative Education Review, 46(3), 291–312.",
        "journal-title": "Comparative Education Review"
      },
      {
        "key": "9199_CR3",
        "volume-title": "Hierarchical linear models: Applications and data analysis methods",
        "author": "AS Bryk",
        "year": "1992",
        "unstructured": "Bryk, A. S., & Raudenbush, S. W. (1992). Hierarchical linear models: Applications and data analysis methods. Newbury Park, CA: Sage."
      },
      {
        "unstructured": "Byamugisha, A. (2010). Examining the effects of school environment factors on pupils’ learning achievement in Uganda primary schools. African Education Research Journal, 1, 110–133. Accessed June 20, 2016, from https://docs.google.com/file/d/0BxjnVLC402PwajdaT0xZbTZUNHVsN1BzLVRGaU1Bdw/edit .",
        "key": "9199_CR4"
      },
      {
        "unstructured": "Brophy, J. (2006). Grade repetition Education policy series 6. International Academic of Education & International Institute for Educational Planning.",
        "key": "9199_CR5"
      },
      {
        "key": "9199_CR6",
        "doi-asserted-by": "crossref",
        "first-page": "723",
        "DOI": "10.1177/016146816306400801",
        "volume": "64",
        "author": "JB Carroll",
        "year": "1963",
        "unstructured": "Carroll, J. B. (1963). A model of school learning. Teachers College Record, 64, 723–733.",
        "journal-title": "Teachers College Record"
      },
      {
        "unstructured": "Coleman, J. S., Campbell, E. Q., Hobson, C. J., McPartland, J., Mood, A. M., & Weinfield, F. D. 1966). Equality of educational opportunity. Washington, DC: National Center for Educational Statistics.",
        "key": "9199_CR7"
      },
      {
        "key": "9199_CR8",
        "volume-title": "The effective classroom",
        "author": "BPM Creemers",
        "year": "1994",
        "unstructured": "Creemers, B. P. M. (1994). The effective classroom. London: Cassell."
      },
      {
        "issue": "10",
        "key": "9199_CR9",
        "doi-asserted-by": "publisher",
        "first-page": "403",
        "DOI": "10.1108/03074800610702598",
        "volume": "107",
        "author": "VF Dent",
        "year": "2006",
        "unstructured": "Dent, V. F. (2006). Observations of school library impact at two rural Ugandan schools. New Library World, 107(10), 403–421.",
        "journal-title": "New Library World"
      },
      {
        "issue": "3",
        "key": "9199_CR10",
        "first-page": "149",
        "volume": "1",
        "author": "AJ Drajea",
        "year": "2014",
        "unstructured": "Drajea, A. J., & O’Sullivan, C. (2014). Influence of parental education and family income on children’s education in rural Uganda. Global Education Review, 1(3), 149–166.",
        "journal-title": "Global Education Review"
      },
      {
        "key": "9199_CR11",
        "doi-asserted-by": "publisher",
        "first-page": "1",
        "DOI": "10.1023/A:1009048817385",
        "volume": "13",
        "author": "XT Fan",
        "year": "2001",
        "unstructured": "Fan, X. T., & Chen, M. (2001). Parental involvement and students’ academic achievement: A meta-analysis. Educational Psychology Review, 13, 1–22.",
        "journal-title": "Educational Psychology Review"
      },
      {
        "unstructured": "Filmer, D., Molina, E., & Stacy, B. (2015). What goes on inside the classroom in Africa? Assessing the relationship between what teachers know, what happened in the classroom, and student performance. Accessed May 13 , 2016, from https://aefpweb.org/sites/default/files/webform/aefp40/Filmer%20Molina%20Stacy%20(2015)%20What%20Goes%20on%20Inside%20Classroom%20Africa.pdf .",
        "key": "9199_CR12"
      },
      {
        "key": "9199_CR13",
        "doi-asserted-by": "publisher",
        "first-page": "255",
        "DOI": "10.3102/00346543057003255",
        "volume": "57",
        "author": "B Fuller",
        "year": "1987",
        "unstructured": "Fuller, B. (1987). What school factors raise achievement in the developing world? Review of Educational Research, 57, 255–292.",
        "journal-title": "Review of Educational Research"
      },
      {
        "issue": "1",
        "key": "9199_CR14",
        "doi-asserted-by": "publisher",
        "first-page": "119",
        "DOI": "10.3102/00346543064001119",
        "volume": "64",
        "author": "B Fuller",
        "year": "1994",
        "unstructured": "Fuller, B., & Clarke, P. (1994). Raising school effects while ignoring culture? Local conditions, and the influence of classroom tools, rules, and pedagogy. Review of Educational Research, 64(1), 119–157.",
        "journal-title": "Review of Educational Research"
      },
      {
        "issue": "3",
        "key": "9199_CR15",
        "doi-asserted-by": "publisher",
        "first-page": "361",
        "DOI": "10.3102/00346543066003361",
        "volume": "66",
        "author": "R Greenwald",
        "year": "1996",
        "unstructured": "Greenwald, R., Hedges, L. V., & Laine, R. D. (1996). The effect of school resources on student achievement. Review of Educational Research, 66(3), 361–396.",
        "journal-title": "Review of Educational Research"
      },
      {
        "key": "9199_CR16",
        "doi-asserted-by": "publisher",
        "first-page": "481",
        "DOI": "10.1016/S0272-7757(03)00038-4",
        "volume": "22",
        "author": "EA Hanushek",
        "year": "2003",
        "unstructured": "Hanushek, E. A., & Luque, J. A. (2003). Efficiency and equity in schools around the world. Economics of Education Review, 22, 481–502.",
        "journal-title": "Economics of Education Review"
      },
      {
        "key": "9199_CR17",
        "volume-title": "Learning: A synthesis of over 800 meta-analysis relating to achievement",
        "author": "J Hattie",
        "year": "2009",
        "unstructured": "Hattie, J. (2009). Learning: A synthesis of over 800 meta-analysis relating to achievement. New York: Routledge."
      },
      {
        "doi-asserted-by": "publisher",
        "unstructured": "Heyneman, S. P. (1976). Influences on academic achievement: A comparison of results from Uganda and more industrialized societies. Sociology of Education, 49(3), 200–211. Accessed June 15, 2016, from http://www.vanderbilt.edu/peabody/heyneman/publications/197601.pdf .",
        "key": "9199_CR18",
        "DOI": "10.2307/2112231"
      },
      {
        "issue": "1",
        "key": "9199_CR19",
        "doi-asserted-by": "publisher",
        "first-page": "13",
        "DOI": "10.2307/2112607",
        "volume": "55",
        "author": "SP Heyneman",
        "year": "1982",
        "unstructured": "Heyneman, S. P., & Loxley, W. A. (1982). Influences on academic achievement across high and low income countries: A re-analysis of IEA data. Sociology of Education, 55(1), 13–21.",
        "journal-title": "Sociology of Education"
      },
      {
        "issue": "6",
        "key": "9199_CR20",
        "doi-asserted-by": "publisher",
        "first-page": "1162",
        "DOI": "10.1086/227799",
        "volume": "88",
        "author": "SP Heyneman",
        "year": "1983",
        "unstructured": "Heyneman, S. P., & Loxley, W. (1983). The effect of primary school quality on academic achievement across 29 high and low-income countries. American Journal of Sociology, 88(6), 1162–1194.",
        "journal-title": "American Journal of Sociology"
      },
      {
        "issue": "4",
        "key": "9199_CR21",
        "first-page": "161",
        "volume": "13",
        "author": "NE Hill",
        "year": "2004",
        "unstructured": "Hill, N. E., & Taylor, L. C. (2004). Parental school involvement and children’s academic achievement. American Psychological Society, 13(4), 161–164.",
        "journal-title": "American Psychological Society"
      },
      {
        "key": "9199_CR22",
        "volume-title": "Applied multilevel analysis",
        "author": "JJ Hox",
        "year": "1995",
        "unstructured": "Hox, J. J. (1995). Applied multilevel analysis. Amsterdam: TT-Publikaties."
      },
      {
        "issue": "3",
        "key": "9199_CR23",
        "doi-asserted-by": "publisher",
        "first-page": "155",
        "DOI": "10.1016/j.stueduc.2008.07.004",
        "volume": "33",
        "author": "N Hungi",
        "year": "2008",
        "unstructured": "Hungi, N. (2008). Examining differences in mathematics and reading achievement among Grade 5 students in Vietnam. Studies in Educational Evaluation, 33(3), 155–164.",
        "journal-title": "Studies in Educational Evaluation"
      },
      {
        "unstructured": "Hungi, N. (2011). Accounting for variation in quality of primary education. Working Paper 7. Paris: SACMEQ. Accessed June 25, 2015, from http://microdata.worldbank.org/index.php/catalog/1246/download/22688 .",
        "key": "9199_CR24"
      },
      {
        "key": "9199_CR25",
        "doi-asserted-by": "publisher",
        "first-page": "247",
        "DOI": "10.1016/j.ijedudev.2014.06.003",
        "volume": "39",
        "author": "N Hungi",
        "year": "2014",
        "unstructured": "Hungi, N., Ngware, M., & Abuya, B. A. (2014). Examining the impact of age on literacy achievement among grade 6 primary school pupils in Kenya. International Journal of Educational Development, 39, 247–259.",
        "journal-title": "International Journal of Educational Development"
      },
      {
        "key": "9199_CR26",
        "doi-asserted-by": "publisher",
        "first-page": "211",
        "DOI": "10.1007/s10671-009-9070-9",
        "volume": "8",
        "author": "N Hungi",
        "year": "2009",
        "unstructured": "Hungi, N., & Postlethwaite, N. T. (2009). The key factors affecting Grade 5 achievement in Laos: Emerging policy issues. Educational Research for Policy and Practice, 8, 211–230.",
        "journal-title": "Educational Research for Policy and Practice"
      },
      {
        "key": "9199_CR27",
        "doi-asserted-by": "publisher",
        "first-page": "33",
        "DOI": "10.1016/j.ijedudev.2009.05.001",
        "volume": "30",
        "author": "N Hungi",
        "year": "2010",
        "unstructured": "Hungi, N., & Thuku, F. W. (2010). Differences in student achievement in Kenya: Implications for policy and practice. International Journal of Educational Development, 30, 33–44.",
        "journal-title": "International Journal of Educational Development"
      },
      {
        "unstructured": "Japan International Cooperation Agency. (2012). Basic education sector analysis report. Kampala: JICA & IDCJ.",
        "key": "9199_CR28"
      },
      {
        "key": "9199_CR29",
        "volume-title": "Determinants of learning achievement in Uganda",
        "author": "I Kasirye",
        "year": "2009",
        "unstructured": "Kasirye, I. (2009). Determinants of learning achievement in Uganda. Kampala: Economic Policy Research Centre."
      },
      {
        "issue": "3",
        "key": "9199_CR30",
        "first-page": "69",
        "volume": "1",
        "author": "F Kasiisa",
        "year": "2013",
        "unstructured": "Kasiisa, F., & Tamale, M. B. (2013). Effect of teacher’s qualification on the pupils performance in primary school social studies: Implication on teacher quality in Uganda. International Journal of Innovative Education Research, 1(3), 69–75.",
        "journal-title": "International Journal of Innovative Education Research"
      },
      {
        "doi-asserted-by": "publisher",
        "unstructured": "Kiwanuka, H. N., Damme, J. V., Noortgate, W. V. D, Anumendem, D. N., & Namusisi, S. (2015). Factors affecting mathematics achievement of first-year secondary school students in Central Uganda. South Africa Journal of Education, 35(3), 1–16. Accessed June 25, 2016, from http://www.scielo.org.za/pdf/saje/v35n3/08.pdf .",
        "key": "9199_CR31",
        "DOI": "10.15700/saje.v35n3a1106"
      },
      {
        "issue": "3",
        "key": "9199_CR32",
        "first-page": "112",
        "volume": "1",
        "author": "ZK Mbugua",
        "year": "2011",
        "unstructured": "Mbugua, Z. K. (2011). Adequacy and the extend to which teaching and learning resources for mathematics are available and used for achievement in the subject in secondary school in Kenya. American International Journal of Contemporary Research, 1(3), 112–116.",
        "journal-title": "American International Journal of Contemporary Research"
      },
      {
        "key": "9199_CR33",
        "volume-title": "The effective provision of pre-school education (EPPE) project: Social/behavioural and cognitive development at 3–4 years in relation to family background",
        "author": "E Melhuish",
        "year": "2001",
        "unstructured": "Melhuish, E., Sylva, K., Sammons, P., Siraj-Blatchford, I., & Taggart, B. (2001). The effective provision of pre-school education (EPPE) project: Social/behavioural and cognitive development at 3–4 years in relation to family background. London: DfEE/Institute of Education, University of London."
      },
      {
        "key": "9199_CR34",
        "first-page": "370",
        "volume": "37",
        "author": "WT Miedel",
        "year": "1999",
        "unstructured": "Miedel, W. T., & Reynolds, A. J. (1999). Parents involvement in early intervention for disadvantaged children: Does it matter? School Psychology Quarterly, 37, 370–402.",
        "journal-title": "School Psychology Quarterly"
      },
      {
        "unstructured": "Ministry of Education and Sports. (1999). The Ugandan experience of universal primary education. Kampala: Ministry of Education and Sports.",
        "key": "9199_CR35"
      },
      {
        "unstructured": "Ministry of Education and Sports. (2005). Status of education for rural people in Uganda. Paper presented at the ministerial seminar on education for rural people in Africa: Policy lessons, options and priorities on 7–9 September 2005, Addis Ababa.",
        "key": "9199_CR36"
      },
      {
        "unstructured": "Ministry of Education and Sports. (2008). Revised education sector strategic plan 2007–2015. Kampala: Ministry of Education and Sports.",
        "key": "9199_CR37"
      },
      {
        "unstructured": "Ministry of Education and Sports. (2012). The education and sports sector annual performance report 2011–2012. Kampala: Ministry of Education and Sports.",
        "key": "9199_CR38"
      },
      {
        "unstructured": "Ministry of Education and Sports. (2013). Uganda end of decade education for all assessment 2001–2012. Kampala: Ministry of Education and Sports.",
        "key": "9199_CR39"
      },
      {
        "key": "9199_CR40",
        "first-page": "42",
        "volume": "15",
        "author": "J Muvawala",
        "year": "2012",
        "unstructured": "Muvawala, J. (2012). Determinants of learning outcomes for primary education: A case of Uganda. The African Statistical Journal, 15, 42–54.",
        "journal-title": "The African Statistical Journal"
      },
      {
        "key": "9199_CR41",
        "doi-asserted-by": "publisher",
        "DOI": "10.1596/978-0-8213-7056-8",
        "volume-title": "Education inputs in Uganda: An analysis of factors influencing learning achievement in Grade 6",
        "author": "H Nannyonjo",
        "year": "2007",
        "unstructured": "Nannyonjo, H. (2007). Education inputs in Uganda: An analysis of factors influencing learning achievement in Grade 6. Washington, DC: The World Bank."
      },
      {
        "issue": "5",
        "key": "9199_CR42",
        "doi-asserted-by": "publisher",
        "first-page": "85",
        "DOI": "10.5430/wje.v5n5p85",
        "volume": "5",
        "author": "JM Okurut",
        "year": "2015",
        "unstructured": "Okurut, J. M. (2015). Examining the effect of automatic promotion on students’ learning achievements in Uganda’s primary education. World Journal of Education, 5(5), 85–100.",
        "journal-title": "World Journal of Education"
      },
      {
        "key": "9199_CR43",
        "volume-title": "HLM 6",
        "author": "SW Raudenbush",
        "year": "2005",
        "unstructured": "Raudenbush, S. W., Bryk, A., & Congdon, R. (2005). HLM 6. Lincolnwood, IL: Scientific Software International."
      },
      {
        "key": "9199_CR44",
        "volume-title": "Hierarchical linear models: Applications and data analysis methods",
        "author": "SW Raudenbush",
        "year": "2002",
        "unstructured": "Raudenbush, S. W., & Bryk, A. S. (2002). Hierarchical linear models: Applications and data analysis methods (2nd ed.). Thousand Oaks, CA: Sage.",
        "edition": "2"
      },
      {
        "unstructured": "SACMEQ. (2010). SACMEQ III project results: Pupil achievement levels in reading and mathematics. Working Document Number 1. Paris: SACMEQ.",
        "key": "9199_CR45"
      },
      {
        "issue": "2",
        "key": "9199_CR46",
        "first-page": "1",
        "volume": "8",
        "author": "ME Ssentanda",
        "year": "2014",
        "unstructured": "Ssentanda, M. E. (2014). The Challenges of Teaching Reading in Uganda: Curriculum guidelines and language policy viewed from the classroom. Apples: Journal of Applied Language Studies, 8(2), 1–22.",
        "journal-title": "Apples: Journal of Applied Language Studies"
      },
      {
        "doi-asserted-by": "publisher",
        "unstructured": "Taniguchi, K., Ohashi, K., & Hirakawa, Y. (2013). Analysis of students’ mathematical achievement in grade 3 and 6 in Uganda: Factors affecting test scores and curriculum. Procedia-Social and Behavioral Science, 93, 2058–2062. Accessed June 20, 2016, from http://www.sciencedirect.com/science/article/pii/S1877042813036100 .",
        "key": "9199_CR47",
        "DOI": "10.1016/j.sbspro.2013.10.165"
      },
      {
        "unstructured": "UNEB. (2010). National Assessment of Progress in Education: The achievement of primary school pupils in Uganda in numeracy, literacy in English and local languages. Kampala: National Assessment of Progress in Education.",
        "key": "9199_CR48"
      },
      {
        "unstructured": "UNEB. (2012). National Assessment of Progress in Education: The achievement of primary school pupils in Uganda in numeracy and literacy in English. Kampala: National Assessment of Progress in Education.",
        "key": "9199_CR49"
      },
      {
        "unstructured": "Uwezo. (2013). Are Our Children Learning? Literacy and Numeracy Across East Africa: Narobi: Twaweza.",
        "key": "9199_CR50"
      },
      {
        "issue": "1",
        "key": "9199_CR51",
        "first-page": "83",
        "volume": "9",
        "author": "R Wamala",
        "year": "2013",
        "unstructured": "Wamala, R., & Seruwagi, G. (2013). Teacher competence and the academic achievement of sixth grade students in Uganda. Journal of International Education Research, 9(1), 83–90.",
        "journal-title": "Journal of International Education Research"
      },
      {
        "issue": "1",
        "key": "9199_CR52",
        "first-page": "113",
        "volume": "6",
        "author": "R Wamala",
        "year": "2013",
        "unstructured": "Wamala, R., Kizito, S. O., & Jjemba, E. (2013). Academic achivement of UgandaN sixth grade students: Influence of parental education levels. Contemporary Issues In Education Research, 6(1), 113–141.",
        "journal-title": "Contemporary Issues In Education Research"
      }
    ],
    "container-title": [
      "Educational Research for Policy and Practice"
    ],
    "original-title": [],
    "language": "en",
    "link": [
      {
        "URL": "http://link.springer.com/article/10.1007/s10671-016-9199-2/fulltext.html",
        "content-type": "text/html",
        "content-version": "vor",
        "intended-application": "text-mining"
      },
      {
        "URL": "http://link.springer.com/content/pdf/10.1007/s10671-016-9199-2.pdf",
        "content-type": "application/pdf",
        "content-version": "vor",
        "intended-application": "text-mining"
      },
      {
        "URL": "http://link.springer.com/content/pdf/10.1007/s10671-016-9199-2.pdf",
        "content-type": "application/pdf",
        "content-version": "vor",
        "intended-application": "similarity-checking"
      }
    ],
    "deposited": {
      "date-parts": [
        [
          2022,
          7,
          12
        ]
      ],
      "date-time": "2022-07-12T05:53:48Z",
      "timestamp": 1657605228000
    },
    "score": 1,
    "resource": {
      "primary": {
        "URL": "http://link.springer.com/10.1007/s10671-016-9199-2"
      }
    },
    "subtitle": [],
    "short-title": [],
    "issued": {
      "date-parts": [
        [
          2016,
          11,
          3
        ]
      ]
    },
    "references-count": 52,
    "journal-issue": {
      "issue": "2",
      "published-print": {
        "date-parts": [
          [
            2017,
            6
          ]
        ]
      }
    },
    "alternative-id": [
      "9199"
    ],
    "URL": "https://doi.org/10.1007/s10671-016-9199-2",
    "relation": {},
    "ISSN": [
      "1570-2081",
      "1573-1723"
    ],
    "issn-type": [
      {
        "type": "print",
        "value": "1570-2081"
      },
      {
        "type": "electronic",
        "value": "1573-1723"
      }
    ],
    "subject": [],
    "published": {
      "date-parts": [
        [
          2016,
          11,
          3
        ]
      ]
    }
  }
}
Response headers
 and Rate limits and authentication
The API uses simple, transparent pricing. Different endpoint types cost different amounts per request.

Endpoint pricing
Endpoint Type
Example
Cost per call
Cost per 1,000 calls
Singleton

/works/W123, /works/W123/ngrams

Free

Free

List

/works?filter=..., /autocomplete/works

$0.0001

$0.10

Search

/works?search=cancer, /works?search.semantic=...

$0.001

$1.00

Content

content.openalex.org/works/{id}.pdf

$0.01

$10.00

Text (Aboutness)

/text/topics?title=...

$0.01

$10.00

High-cost endpoints
Some endpoints cost significantly more than standard queries:

Endpoint
Cost per call
Daily limit (free)
Notes
Content downloads

$0.01

~100 files

PDF or TEI XML

Aboutness (/text)

$0.01

~100 requests

Topic classification

Planning bulk content downloads? Downloading all 60M available PDFs would cost ~$600,000. Contact us about enterprise pricing for large-scale projects.

Rate limits
Starting February 13, 2026, an API key is required to use the OpenAlex API. API keys are free—get yours here. See the announcement for details.

The limits are:

Without an API key: $0.01/day API budget (for testing and demos only)

With a free API key: $1/day API budget

All users: max 100 requests per second (regardless of cost)

For example, with a $1/day budget you can make:

Unlimited singleton requests (like /works/W123) — they're free!

10,000 list requests (like /works?filter=type:article), or

Any combination that adds up to $1

If you exceed your daily budget or make more than 100 requests per second, you'll get 429 errors instead of useful data.

Need a higher budget? Subscribe to OpenAlex Premium for significantly more. Academic researchers can often get increased limits for free—contact support@openalex.org.

Are you scrolling through a list of entities, calling the API for each? You can go way faster by squishing 50 requests into one using our OR syntax. Here's a tutorial showing how.

Rate limit headers
Every API response includes headers showing your current rate limit status:

Header
Description
X-RateLimit-Limit-USD

Your total daily API budget in USD

X-RateLimit-Remaining-USD

Budget remaining for today in USD

X-RateLimit-Cost-USD

Cost of this request in USD

X-RateLimit-Prepaid-Remaining-USD

Prepaid balance remaining in USD

X-RateLimit-Reset

Seconds until your budget resets (midnight UTC)

Check your rate limit status
You can check your current rate limit status at any time using the /rate-limit endpoint (requires an API key):


Copy
GET https://api.openalex.org/rate-limit?api_key=YOUR_API_KEY
Response:


Copy
{
  "api_key": "abc...xyz",
  "rate_limit": {
    "daily_budget_usd": 1.0,
    "daily_used_usd": 0.1234,
    "daily_remaining_usd": 0.8766,
    "prepaid_balance_usd": 0,
    "prepaid_remaining_usd": 0,
    "prepaid_expires_at": null,
    "resets_at": "2026-02-19T00:00:00.000Z",
    "resets_in_seconds": 43200,
    "endpoint_costs_usd": {
      "singleton": 0,
      "list": 0.0001,
      "search": 0.001,
      "semantic": 0.001,
      "content": 0.01,
      "text": 0.01
    }
  }
}
Authentication
An API key is required to use the OpenAlex API. The good news: API keys are free! Here's how to get one:

Create a free account at openalex.org

Go to openalex.org/settings/api to get your key

Add api_key=YOUR_KEY to your API calls

Example:

https://api.openalex.org/works?api_key=YOUR_KEY

Without an API key, you're limited to just $0.01/day—enough for quick tests, but not for real work. With a free API key, you get $1/day of API budget.

Premium users get even higher budgets and access to special filters like from_updated_date.

Usage tips
Calling the API in your browser
Because the API is all GET requests without fancy authentication, you can view any request in your browser. This is a very useful and pleasant way to explore the API and debug scripts; we use it all the time.

However, this is much nicer if you install an extension to pretty-print the JSON; JSONVue (Chrome) and JSONView (Firefox) are popular, free choices. Here's what an API response looks like with one of these extensions enabled:


A lot prettier than cURL
{"id":"https://openalex.org/W2492449078","doi":"https://doi.org/10.1080/01900692.2016.1201839","title":"Are School Committees a Source of Empowerment? Insights from Tanzania","display_name":"Are School Committees a Source of Empowerment? Insights from Tanzania","publication_year":2016,"publication_date":"2016-07-22","ids":{"openalex":"https://openalex.org/W2492449078","doi":"https://doi.org/10.1080/01900692.2016.1201839","mag":"2492449078"},"language":"en","primary_location":{"id":"doi:10.1080/01900692.2016.1201839","is_oa":false,"landing_page_url":"https://doi.org/10.1080/01900692.2016.1201839","pdf_url":null,"source":{"id":"https://openalex.org/S39541053","display_name":"International Journal of Public Administration","issn_l":"0190-0692","issn":["0190-0692","1532-4265"],"is_oa":false,"is_in_doaj":false,"is_core":true,"host_organization":"https://openalex.org/P4310320547","host_organization_name":"Taylor & Francis","host_organization_lineage":["https://openalex.org/P4310320547"],"host_organization_lineage_names":["Taylor & Francis"],"type":"journal"},"license":null,"license_id":null,"version":"publishedVersion","is_accepted":true,"is_published":true,"raw_source_name":"International Journal of Public Administration","raw_type":"journal-article"},"type":"article","indexed_in":["crossref"],"open_access":{"is_oa":false,"oa_status":"closed","oa_url":null,"any_repository_has_fulltext":false},"authorships":[{"author_position":"first","author":{"id":"https://openalex.org/A5089148132","display_name":"Orest Sebastian Masue","orcid":"https://orcid.org/0000-0002-7100-3116"},"institutions":[{"id":"https://openalex.org/I15846685","display_name":"Mzumbe University","ror":"https://ror.org/02qrvdj69","country_code":"TZ","type":"education","lineage":["https://openalex.org/I15846685"]}],"countries":["TZ"],"is_corresponding":true,"raw_author_name":"Orest Sebastian Masue","raw_affiliation_strings":["School of Public Administration and Management, Mzumbe University, Mzumbe, Morogoro, United Republic of Tanzania"],"affiliations":[{"raw_affiliation_string":"School of Public Administration and Management, Mzumbe University, Mzumbe, Morogoro, United Republic of Tanzania","institution_ids":["https://openalex.org/I15846685"]}]},{"author_position":"last","author":{"id":"https://openalex.org/A5033263227","display_name":"Steinar Askvik","orcid":null},"institutions":[{"id":"https://openalex.org/I4432739","display_name":"University of Bergen","ror":"https://ror.org/03zga2b32","country_code":"NO","type":"education","lineage":["https://openalex.org/I4432739"]}],"countries":["NO"],"is_corresponding":false,"raw_author_name":"Steinar Askvik","raw_affiliation_strings":["Department of Administration and Organisation Theory, University of Bergen, Administration and Organization Theory, Bergen, Norway"],"affiliations":[{"raw_affiliation_string":"Department of Administration and Organisation Theory, University of Bergen, Administration and Organization Theory, Bergen, Norway","institution_ids":["https://openalex.org/I4432739"]}]}],"institutions":[],"countries_distinct_count":2,"institutions_distinct_count":2,"corresponding_author_ids":["https://openalex.org/A5089148132"],"corresponding_institution_ids":["https://openalex.org/I15846685"],"apc_list":null,"apc_paid":null,"fwci":1.01266397,"has_fulltext":false,"cited_by_count":6,"citation_normalized_percentile":{"value":0.84714359,"is_in_top_1_percent":false,"is_in_top_10_percent":false},"cited_by_percentile_year":{"min":89,"max":96},"biblio":{"volume":"40","issue":"9","first_page":"780","last_page":"791"},"is_retracted":false,"is_paratext":false,"is_xpac":false,"primary_topic":{"id":"https://openalex.org/T11556","display_name":"Poverty, Education, and Child Welfare","score":0.9804999828338623,"subfield":{"id":"https://openalex.org/subfields/3311","display_name":"Safety Research"},"field":{"id":"https://openalex.org/fields/33","display_name":"Social Sciences"},"domain":{"id":"https://openalex.org/domains/2","display_name":"Social Sciences"}},"topics":[{"id":"https://openalex.org/T11556","display_name":"Poverty, Education, and Child Welfare","score":0.9804999828338623,"subfield":{"id":"https://openalex.org/subfields/3311","display_name":"Safety Research"},"field":{"id":"https://openalex.org/fields/33","display_name":"Social Sciences"},"domain":{"id":"https://openalex.org/domains/2","display_name":"Social Sciences"}},{"id":"https://openalex.org/T10674","display_name":"School Choice and Performance","score":0.927299976348877,"subfield":{"id":"https://openalex.org/subfields/3304","display_name":"Education"},"field":{"id":"https://openalex.org/fields/33","display_name":"Social Sciences"},"domain":{"id":"https://openalex.org/domains/2","display_name":"Social Sciences"}},{"id":"https://openalex.org/T10987","display_name":"Microfinance and Financial Inclusion","score":0.925599992275238,"subfield":{"id":"https://openalex.org/subfields/2002","display_name":"Economics and Econometrics"},"field":{"id":"https://openalex.org/fields/20","display_name":"Economics, Econometrics and Finance"},"domain":{"id":"https://openalex.org/domains/2","display_name":"Social Sciences"}}],"keywords":[{"id":"https://openalex.org/keywords/tanzania","display_name":"Tanzania","score":0.8994107246398926},{"id":"https://openalex.org/keywords/empowerment","display_name":"Empowerment","score":0.8876053094863892},{"id":"https://openalex.org/keywords/public-relations","display_name":"Public relations","score":0.4970994293689728},{"id":"https://openalex.org/keywords/sociology","display_name":"Sociology","score":0.38930389285087585},{"id":"https://openalex.org/keywords/political-science","display_name":"Political science","score":0.3491813540458679},{"id":"https://openalex.org/keywords/socioeconomics","display_name":"Socioeconomics","score":0.18473964929580688},{"id":"https://openalex.org/keywords/law","display_name":"Law","score":0.09424608945846558}],"concepts":[{"id":"https://openalex.org/C2779357621","wikidata":"https://www.wikidata.org/wiki/Q655495","display_name":"Tanzania","level":2,"score":0.8994107246398926},{"id":"https://openalex.org/C20555606","wikidata":"https://www.wikidata.org/wiki/Q868575","display_name":"Empowerment","level":2,"score":0.8876053094863892},{"id":"https://openalex.org/C39549134","wikidata":"https://www.wikidata.org/wiki/Q133080","display_name":"Public relations","level":1,"score":0.4970994293689728},{"id":"https://openalex.org/C144024400","wikidata":"https://www.wikidata.org/wiki/Q21201","display_name":"Sociology","level":0,"score":0.38930389285087585},{"id":"https://openalex.org/C17744445","wikidata":"https://www.wikidata.org/wiki/Q36442","display_name":"Political science","level":0,"score":0.3491813540458679},{"id":"https://openalex.org/C45355965","wikidata":"https://www.wikidata.org/wiki/Q1643441","display_name":"Socioeconomics","level":1,"score":0.18473964929580688},{"id":"https://openalex.org/C199539241","wikidata":"https://www.wikidata.org/wiki/Q7748","display_name":"Law","level":1,"score":0.09424608945846558}],"mesh":[],"locations_count":2,"locations":[{"id":"doi:10.1080/01900692.2016.1201839","is_oa":false,"landing_page_url":"https://doi.org/10.1080/01900692.2016.1201839","pdf_url":null,"source":{"id":"https://openalex.org/S39541053","display_name":"International Journal of Public Administration","issn_l":"0190-0692","issn":["0190-0692","1532-4265"],"is_oa":false,"is_in_doaj":false,"is_core":true,"host_organization":"https://openalex.org/P4310320547","host_organization_name":"Taylor & Francis","host_organization_lineage":["https://openalex.org/P4310320547"],"host_organization_lineage_names":["Taylor & Francis"],"type":"journal"},"license":null,"license_id":null,"version":"publishedVersion","is_accepted":true,"is_published":true,"raw_source_name":"International Journal of Public Administration","raw_type":"journal-article"},{"id":"pmh:oai:RePEc:taf:lpadxx:v:40:y:2017:i:9:p:780-791","is_oa":false,"landing_page_url":"http://hdl.handle.net/10.1080/01900692.2016.1201839","pdf_url":null,"source":{"id":"https://openalex.org/S4306401271","display_name":"RePEc: Research Papers in Economics","issn_l":null,"issn":null,"is_oa":false,"is_in_doaj":false,"is_core":false,"host_organization":"https://openalex.org/I77793887","host_organization_name":"Federal Reserve Bank of St. Louis","host_organization_lineage":["https://openalex.org/I77793887"],"host_organization_lineage_names":[],"type":"repository"},"license":null,"license_id":null,"version":"submittedVersion","is_accepted":false,"is_published":false,"raw_source_name":null,"raw_type":"article"}],"best_oa_location":null,"sustainable_development_goals":[{"score":0.6800000071525574,"display_name":"Gender equality","id":"https://metadata.un.org/sdg/5"}],"awards":[],"funders":[],"has_content":{"grobid_xml":false,"pdf":false},"content_urls":null,"referenced_works_count":32,"referenced_works":["https://openalex.org/W574722219","https://openalex.org/W1515810707","https://openalex.org/W1914972138","https://openalex.org/W1963501656","https://openalex.org/W1970559816","https://openalex.org/W1990248849","https://openalex.org/W2011604835","https://openalex.org/W2016546390","https://openalex.org/W2024664227","https://openalex.org/W2034173786","https://openalex.org/W2046367910","https://openalex.org/W2057393635","https://openalex.org/W2067616162","https://openalex.org/W2076620228","https://openalex.org/W2104556088","https://openalex.org/W2126171876","https://openalex.org/W2127195890","https://openalex.org/W2132912961","https://openalex.org/W2161081582","https://openalex.org/W2166826583","https://openalex.org/W2168391307","https://openalex.org/W2169250924","https://openalex.org/W2170830154","https://openalex.org/W2182116093","https://openalex.org/W2289406838","https://openalex.org/W3123010330","https://openalex.org/W3125818220","https://openalex.org/W3148367176","https://openalex.org/W4230480985","https://openalex.org/W4231454964","https://openalex.org/W4291417370","https://openalex.org/W4300703720"],"related_works":["https://openalex.org/W2748952813","https://openalex.org/W2754697109","https://openalex.org/W4390038797","https://openalex.org/W4238742044","https://openalex.org/W2481494875","https://openalex.org/W2065780911","https://openalex.org/W610123486","https://openalex.org/W3150127134","https://openalex.org/W4250334497","https://openalex.org/W3180336185"],"abstract_inverted_index":{"Studies":[0],"on":[1,22,56,90],"user":[2],"committees":[3,12,25],"often":[4],"critique":[5],"the":[6,43,65,71,76],"claim":[7],"that":[8,49],"membership":[9,34,50,74],"to":[10,28,60,75,87],"these":[11],"empowers":[13],"people.":[14],"In":[15],"this":[16],"article,":[17],"we":[18],"use":[19],"survey":[20],"data":[21],"empowerment":[23,39],"school":[24,32,77,91],"in":[26,51],"Tanzania":[27],"find":[29],"out":[30],"whether":[31],"committee":[33,78],"is":[35,79],"a":[36],"source":[37],"of":[38,40,68,73],"people":[41],"at":[42],"local":[44],"levels.":[45],"Our":[46],"findings":[47],"suggest":[48],"itself":[52],"has":[53],"limited":[54],"impact":[55],"empowerment,":[57],"while":[58],"access":[59],"information":[61,89],"and":[62],"gender":[63],"are":[64],"major":[66],"sources":[67],"empowerment.":[69],"However,":[70],"role":[72],"significant":[80],"insofar":[81],"as":[82],"it":[83],"can":[84],"expose":[85],"members":[86],"critical":[88],"issues.":[92]},"counts_by_year":[{"year":2024,"cited_by_count":1},{"year":2023,"cited_by_count":1},{"year":2022,"cited_by_count":1},{"year":2021,"cited_by_count":1},{"year":2017,"cited_by_count":2}],"updated_date":"2025-11-06T03:46:38.306776","created_date":"2025-10-10T00:00:00"}


## Copilot

| API | Fields covered well | Fields covered poorly / gaps | API key needed? | Rate limits / reliability considerations | Typical failure modes / gaps | Why it’s a good fit for your MVP (20 DOIs → step1.xlsx) |
|---|---|---|---|---|---|---|
| **Crossref REST** | **Title:** strong; **Year/date:** strong (issued / published-online/print); **Authors:** usually good (names, order; affiliations often missing); **References:** *sometimes* good (publisher-deposited `reference[]`, may include DOI + unstructured) | **Abstract:** often missing; **Affiliations/countries:** sparse; **References:** coverage inconsistent across publishers; reference items often unstructured/partial | **No key** (best practice: include a `mailto=` in User-Agent / contact) | Generally reliable; subject to polite use / throttling; can return **429/403** if you hammer it; metadata quality depends on publisher deposits | DOI exists but record incomplete; missing abstract; references-count present but `reference[]` absent; inconsistent author fields; occasional redirects/format quirks for DOIs | Best “ground truth” DOI-centric metadata baseline; simplest singleton lookup per DOI; good provenance (publisher-deposited) and stable DOI identifiers |
| **OpenAlex API** | **Title:** strong; **Year:** strong (`publication_year`); **Authors:** strong and **graph-ready** (author IDs, ORCID sometimes, institutions with **ROR + country_code**); **References:** strong as a **linked list of referenced work IDs** (`referenced_works`) | **Abstract:** variable; when present it’s an **inverted index** (needs reconstruction); **Formatted reference strings:** not the focus (you may need to fetch referenced works to build full citations); some works may have sparse metadata | **Yes (starting 2026-02-13): key required for real use** (per your note). Without key: demo-only budget | Budget-based limits (USD/day) + **429** when budget exceeded; also global cap (e.g., 100 req/s). Singleton work fetches are free-cost, but you still need a key for usable daily budget | DOI not matched (especially odd DOI formats); abstract missing or only inverted-index; references only as IDs requiring extra calls; daily budget exhaustion if you naively fetch each referenced work one-by-one | Excellent for your “future Graph RAG” goal: stable entity IDs (works/authors/institutions), normalized affiliations and countries; strong references graph for building citation edges |
| **Semantic Scholar Graph API** | **Abstract:** often good when available; **References:** often good and structured (paper graph); **Title/Year/Authors:** generally good; can return DOIs for references when known | Coverage varies by discipline/publisher; not every DOI resolves; affiliation/country data not as consistently normalized as OpenAlex; references may be incomplete for some papers | **Sometimes**: workable without key for light use, but **API key commonly needed** for sustained/production throughput and reliability | Rate-limited; can return **429**; occasional transient 5xx; fields may be missing even when paper exists | DOI not found / mismatched; abstract missing due to licensing/coverage; references truncated/partial; author disambiguation differences vs Crossref/OpenAlex | Best “filler” source for **abstract + reference list** when Crossref/OpenAlex lack them; good for MVP completeness (esp. abstracts) while keeping the pipeline public and reproducible |

**Suggested MVP strategy (deterministic merge):**
- **Crossref** as the canonical DOI metadata base (title/year/authors + references when present).
- **OpenAlex** for **author/institution normalization + countries** and a robust **references graph**.
- **Semantic Scholar** as a targeted fallback for **abstract** and **references** when missing/weak elsewhere.

If you want, I can propose an explicit “field priority matrix” (per column in `step1.xlsx`) plus a minimal-call plan that stays within OpenAlex budget (e.g., only singleton work lookups + optional batched OR queries for referenced works).

## @liya-oz

Given the candidate stacks recommend one primary approach + one fallback approach.

Explain the decision in terms of: coverage for abstracts and references, stability/reproducibility, implementation complexity, and risk. Also list backup options I could switch to if the primary approach underperforms.

Keep it concise but explicit (I want to be able to defend the choice in my narrative).

## Copilot

## Primary approach (recommended): **Crossref + OpenAlex** (deterministic merge; OpenAlex key)

### Why this is the best default
- **Coverage (abstracts + references)**
  - **References:** strong overall because OpenAlex reliably provides `referenced_works` (graph edges) even when Crossref doesn’t include `reference[]`.
  - **Abstracts:** *moderate*—OpenAlex abstracts are not universal, but when present you can reconstruct from `abstract_inverted_index`. Crossref abstracts are rare, so abstracts remain the main coverage risk in this stack.
- **Stability / reproducibility**
  - **Very good**: DOI is your stable work ID; OpenAlex adds stable IDs for authors/institutions (ORCID/ROR when present) which is ideal for “Graph RAG-ready” normalization.
  - Both are well-documented, widely used; you can store raw JSON + retrieval timestamps to make runs repeatable.
- **Implementation complexity**
  - **Moderate**: Crossref is straightforward; OpenAlex requires:
    - API key management (now effectively required),
    - reconstructing abstract text from inverted index,
    - optionally resolving referenced work IDs into full citations (extra calls).
- **Risk**
  - **Main risk:** abstract completeness. Many DOIs will not have OpenAlex abstract text.
  - **Secondary risk:** OpenAlex budget/rate limits if you fetch all referenced works individually; mitigate by (a) outputting reference IDs/DOIs first, (b) batching lookups, (c) limiting reference expansion in MVP.

**Positioning / narrative defense:** “We chose Crossref for authoritative DOI-centric bibliographic metadata and OpenAlex for graph-normalized entities (author/institution IDs, countries) and robust reference linkage, yielding a reproducible, Graph RAG-friendly dataset with stable identifiers.”

---

## Fallback approach (if abstract/reference completeness is not adequate): **Crossref + Semantic Scholar** (use S2 mainly for abstract + reference list)

### Why this fallback
- **Coverage (abstracts + references)**
  - **Abstracts:** often better than OpenAlex/Crossref alone.
  - **References:** often returned as structured lists; good for “full reference list” requirement.
- **Stability / reproducibility**
  - **Good but less “canonical”** than OpenAlex for institutions/countries and graph IDs; you still anchor everything on DOI to keep stable IDs.
  - You must be careful about version drift; store raw responses.
- **Implementation complexity**
  - **Moderate**: fewer graph normalization features than OpenAlex, but easier to get “one call gives abstract + references” for many papers.
- **Risk**
  - **Coverage variability & policy risk:** some DOIs won’t resolve; rate limits may require an API key; field availability differs across papers.

**Narrative defense:** “We use Semantic Scholar as a pragmatic completeness fallback because it frequently supplies abstracts and reference lists when publisher-deposited metadata is absent.”

---

## Backup options you can switch to (if primary underperforms)

1) **Add Semantic Scholar as a *selective* third source** (recommended “escape hatch”)
- Keep Crossref + OpenAlex as base; call S2 only when `abstract` or `references` are missing/too sparse.
- Minimizes rate-limit exposure while improving completeness.

2) **Biomedical-heavy DOI set → Europe PMC (+ PubMed E-utilities)**
- If many DOIs are in PubMed/PMC, this can dramatically improve abstract coverage and sometimes references (via full text).
- Domain-limited; not a general solution.

3) **Publisher full-text endpoints when open (Unpaywall + OA location → fetch JATS/HTML/PDF)**
- Highest potential abstract/reference completeness, but **complexity and risk** rise (parsing, heterogeneous formats, access constraints).
- Good “Phase 2” if you later accept more engineering effort.

If you tell me your DOI mix (mostly biomedical? mostly social science? mostly Elsevier/Springer?) and whether you can use API keys, I can lock the decision and propose a very explicit decision tree (per DOI: which API calls happen, in what order, and when to stop).

## @liya-oz

Context: I’m building an MVP Python pipeline that takes a CSV of DOIs (e.g., 10.1007/s10671-016-9199-2, 10.1080/01900692.2016.1201839, 10.4018/IJICTE.2017070104) and outputs step1.xlsx.

For step1.xlsx file propose an explicit schema: exact column names, data types and how to represent multi-valued fields (multiple authors, genders, countries, references).

Constraints:

One row per input DOI
Must be easy to ingest later into a database / Graph RAG pipeline.
Avoid ambiguous free-text where possible; include stable identifiers where available
Deliver:

A table of columns: column_name, type, description, example
A short example of how one row would look (with multi-valued fields in JSON string,
Any normalization rules (we need DOI lowercasing, trimming, unknown rules, what if publication year different?)

## Copilot

### `step1.xlsx` schema (one row per input DOI)

Multi-valued / nested fields are stored as **JSON strings** (UTF-8) in a single cell to keep the “one row per DOI” constraint while staying database/graph-ingest friendly. Use consistent keys + stable IDs where available.

| column_name | type | description | example |
|---|---|---|---|
| `input_row` | int | 0-based row index from the input CSV (auditability; preserves original order). | `0` |
| `input_doi_raw` | string | Raw DOI cell value from CSV before parsing/cleanup. | `"  https://doi.org/10.1007/S10671-016-9199-2 "` |
| `doi` | string | **Normalized DOI** (lowercase, no `doi:` prefix, no URL wrapper). Primary key for the row. | `"10.1007/s10671-016-9199-2"` |
| `work_id` | string | Stable internal work identifier for graph ingestion. | `"doi:10.1007/s10671-016-9199-2"` |
| `doi_url` | string | Canonical DOI URL. | `"https://doi.org/10.1007/s10671-016-9199-2"` |
| `retrieved_at_utc` | string (ISO-8601) | When this DOI was processed (end of retrieval/merge step). | `"2026-02-26T19:21:04Z"` |
| `sources_json` | string (JSON) | Per-provider request metadata and which provider “won” key fields. | `{"crossref":{"status":200},"openalex":{"status":200},"field_winners":{"title":"crossref","abstract":"openalex"}}` |
| `title` | string | Best merged title (single string). | `"Learning barriers among Grade 6 pupils attending rural schools in Uganda: implications to policy and practice"` |
| `title_language` | string \| null | Language code if available (BCP-47-ish; often `en`). | `"en"` |
| `abstract` | string \| null | Best merged abstract as plain text (tags stripped). Null if unavailable. | `"In this article we use survey data…"` |
| `abstract_source` | string \| null | Provider that supplied `abstract` (e.g., `openalex`, `semanticscholar`, `crossref`). | `"openalex"` |
| `publication_year` | int \| null | Single chosen year used for downstream grouping. | `2016` |
| `publication_year_source` | string \| null | Provider/field used to choose the year. | `"crossref:issued"` |
| `published_date` | string \| null | Best-known publication date (`YYYY-MM-DD` if possible; else `YYYY-MM` or `YYYY`). | `"2016-11-03"` |
| `published_date_precision` | string | One of: `day`, `month`, `year`, `unknown`. | `"day"` |
| `container_title` | string \| null | Journal / proceedings / book title if available. | `"Educational Research for Policy and Practice"` |
| `publisher` | string \| null | Publisher name if available. | `"Springer Science and Business Media LLC"` |
| `type` | string \| null | Work type normalized (e.g., `journal-article`, `proceedings-article`, `book-chapter`, `posted-content`). | `"journal-article"` |
| `open_access_json` | string (JSON) | OA signals if available (don’t scrape full text; just record OA state/URLs). | `{"is_oa":false,"oa_status":"closed","best_oa_url":null}` |
| `authors_json` | string (JSON array) | Ordered author list with stable IDs when present (ORCID/OpenAlex). | `[{"ordinal":1,"name":"Njora Hungi","given":"Njora","family":"Hungi","orcid":null,"openalex_id":null},{"ordinal":2,"name":"Moses Ngware","given":"Moses","family":"Ngware","orcid":null,"openalex_id":null}]` |
| `author_count` | int | Count of authors (len of `authors_json`). | `4` |
| `authors_orcid_count` | int | Number of authors with ORCID present. | `0` |
| `author_genders_json` | string (JSON array) | Gender inference output aligned to authors by `ordinal` (store uncertainty + method). | `[{"ordinal":1,"gender":"unknown","prob":null,"method":"none"},{"ordinal":2,"gender":"male","prob":0.86,"method":"name_api_v1"}]` |
| `institutions_json` | string (JSON array) | Unique institutions extracted from author affiliations (prefer ROR). | `[{"ror":"https://ror.org/03zga2b32","name":"University of Bergen","country_code":"NO","source":"openalex"}]` |
| `countries_json` | string (JSON array) | Unique country codes (ISO-3166-1 alpha-2) derived from affiliations/institutions; include provenance. | `[{"country_code":"UG","source":"affiliation_text"},{"country_code":"NO","source":"openalex_institution"}]` |
| `reference_count_reported` | int \| null | Reference count if provider reports it even when list missing. | `52` |
| `references_json` | string (JSON array) | Full reference list (as available). Each ref is a structured object; keep `raw` for lossless storage but prefer IDs. | `[{"ref_ordinal":1,"doi":"10.3402/fnr.v56i0.11217","work_id":"doi:10.3402/fnr.v56i0.11217","unstructured":"Acham, H., …"},{"ref_ordinal":2,"doi":"10.1086/341159","work_id":"doi:10.1086/341159","unstructured":"Baker, D. P., …"}]` |
| `references_source` | string \| null | Provider used for `references_json` (e.g., `crossref`, `openalex`, `semanticscholar`). | `"crossref"` |
| `errors_json` | string (JSON array) | Non-fatal errors/warnings (missing fields, parse failures) for QA. | `[{"stage":"retrieval","provider":"crossref","level":"warning","message":"abstract missing"}]` |

Notes:
- For Excel: all JSON fields are stored as **string cells** containing JSON (no pretty-printing, no newlines) to reduce quoting/line-break issues.
- If you later normalize into DB tables, you can explode `authors_json`, `institutions_json`, `references_json` by `work_id`.

---

## One-row example (illustrative)

(Shown as a Python-like dict for readability; in Excel each key is a column, and JSON fields are strings.)

```text name=step1_row_example.txt
{
  "input_row": 0,
  "input_doi_raw": "10.1080/01900692.2016.1201839",
  "doi": "10.1080/01900692.2016.1201839",
  "work_id": "doi:10.1080/01900692.2016.1201839",
  "doi_url": "https://doi.org/10.1080/01900692.2016.1201839",
  "retrieved_at_utc": "2026-02-26T19:21:04Z",
  "sources_json": "{\"crossref\":{\"status\":200},\"openalex\":{\"status\":200},\"field_winners\":{\"title\":\"openalex\",\"abstract\":\"openalex\",\"references\":\"openalex\"}}",
  "title": "Are School Committees a Source of Empowerment? Insights from Tanzania",
  "title_language": "en",
  "abstract": "Studies on user committees often critique the claim that membership to these empowers people. In this article, we use survey data ...",
  "abstract_source": "openalex",
  "publication_year": 2016,
  "publication_year_source": "openalex:publication_year",
  "published_date": "2016-07-22",
  "published_date_precision": "day",
  "container_title": "International Journal of Public Administration",
  "publisher": "Taylor & Francis",
  "type": "journal-article",
  "open_access_json": "{\"is_oa\":false,\"oa_status\":\"closed\",\"best_oa_url\":null}",
  "authors_json": "[{\"ordinal\":1,\"name\":\"Orest Sebastian Masue\",\"given\":\"Orest Sebastian\",\"family\":\"Masue\",\"orcid\":\"https://orcid.org/0000-0002-7100-3116\",\"openalex_id\":\"https://openalex.org/A5089148132\"},{\"ordinal\":2,\"name\":\"Steinar Askvik\",\"given\":\"Steinar\",\"family\":\"Askvik\",\"orcid\":null,\"openalex_id\":\"https://openalex.org/A5033263227\"}]",
  "author_count": 2,
  "authors_orcid_count": 1,
  "author_genders_json": "[{\"ordinal\":1,\"gender\":\"male\",\"prob\":0.93,\"method\":\"name_api_v1\"},{\"ordinal\":2,\"gender\":\"male\",\"prob\":0.99,\"method\":\"name_api_v1\"}]",
  "institutions_json": "[{\"ror\":\"https://ror.org/02qrvdj69\",\"name\":\"Mzumbe University\",\"country_code\":\"TZ\",\"source\":\"openalex\"},{\"ror\":\"https://ror.org/03zga2b32\",\"name\":\"University of Bergen\",\"country_code\":\"NO\",\"source\":\"openalex\"}]",
  "countries_json": "[{\"country_code\":\"TZ\",\"source\":\"openalex_institution\"},{\"country_code\":\"NO\",\"source\":\"openalex_institution\"}]",
  "reference_count_reported": 32,
  "references_json": "[{\"ref_ordinal\":1,\"doi\":null,\"work_id\":\"https://openalex.org/W574722219\",\"unstructured\":null},{\"ref_ordinal\":2,\"doi\":null,\"work_id\":\"https://openalex.org/W1515810707\",\"unstructured\":null}]",
  "references_source": "openalex",
  "errors_json": "[]"
}
```

In this example, `references_json` is OpenAlex-style: you may have `work_id` without DOI unless you additionally resolve each referenced work.

---

## Normalization rules (explicit)

### DOI normalization
1. Trim whitespace.
2. Extract DOI from common wrappers:
   - `https://doi.org/<doi>`, `http://dx.doi.org/<doi>`, `doi:<doi>`
3. Lowercase the DOI.
4. Strip trailing punctuation `).,;` and surrounding quotes.
5. Validate against a conservative DOI regex; if invalid, set:
   - `doi = null`, `errors_json += invalid_doi`, still keep the row keyed by `input_row` (but you’ll lose the “one row per DOI” uniqueness guarantee). Prefer failing fast if you truly require DOI.

### Stable IDs
- `work_id = "doi:" + doi` when `doi` is present.
- For authors:
  - Prefer ORCID (`https://orcid.org/...`) if present.
  - Else keep provider IDs (e.g., OpenAlex author ID) in `authors_json`.
  - Avoid generating “synthetic author IDs” from names unless you accept collision risk.

### Missing / unknown conventions
- Use **JSON null** inside JSON fields, and empty cell / null in scalar columns.
- Gender:
  - allowed values: `male`, `female`, `nonbinary`, `unknown`
  - if no inference: `gender="unknown", prob=null, method="none"`

### Publication year conflict resolution
Store *one* `publication_year` but make the rule deterministic:
1. Prefer Crossref `issued.date-parts` year if present (often closest to “official” publication).
2. Else prefer OpenAlex `publication_year`.
3. Else Semantic Scholar year.
Also:
- If Crossref has both `published-online` and `published-print`, choose the earliest **non-null** year unless you explicitly want print precedence (document which you chose).
- Record `publication_year_source` so you can defend/trace it.

### References representation
- `references_json` is an **array ordered by appearance** (`ref_ordinal`).
- Each reference object should include, when available:
  - `doi` (normalized, lowercase)
  - `work_id` (`doi:<doi>` if DOI known, else provider work ID if you have one)
  - `unstructured` (string) only when you can’t fully structure it (kept for lossless capture)
- If you only have reference IDs (OpenAlex), it’s acceptable in MVP to set `unstructured=null` and keep `work_id`; you can expand later.

---

If you tell me whether you plan to **expand OpenAlex referenced works into full citations in MVP** (yes/no), I can tighten the `references_json` schema accordingly (either “IDs-only” vs “resolved refs with DOI/title/year”).

## @liya-oz

Define validation checks I should implement after extraction to ensure step1.xlsx is consistent and audit-friendly

## Copilot

### Post-extraction validation checks for `step1.xlsx` (consistency + auditability)

Implement these as a deterministic “validation report” step that produces (a) a list of row-level issues and (b) summary stats. Classify findings as **ERROR** (row is not usable / violates constraints) vs **WARN** (usable but incomplete).

---

## 1) File-level / run-level checks

1. **Row count matches input**
   - **ERROR** if `len(output_rows) != len(input_dois)` (since you require one row per input DOI).
2. **Input order preserved**
   - **ERROR** if `input_row` is not exactly `0..N-1` with no gaps.
3. **Schema completeness**
   - **ERROR** if any required column is missing.
   - **WARN** if any optional column missing (if you allow schema evolution).
4. **Column type sanity (Excel-friendly)**
   - **ERROR** if columns expected to be scalar contain non-scalars (e.g., `authors_json` accidentally stored as a Python repr instead of JSON).
5. **Deterministic run metadata present**
   - **WARN/ERROR** depending on strictness if `retrieved_at_utc` or `sources_json` absent.
   - (Optional but recommended) record a `pipeline_version` and `config_hash` somewhere (either a hidden sheet or added columns).

---

## 2) Key / identity checks (Graph-ready invariants)

6. **DOI normalization validity**
   - **ERROR** if `doi` is null/empty for any row (if DOI is mandatory).
   - **ERROR** if `doi` does not match a DOI pattern (conservative regex) after normalization.
   - **WARN** if `doi` contains uppercase letters (should be lowercase).
7. **Uniqueness**
   - **ERROR** if duplicated `doi` values exist (after normalization).
   - **ERROR** if duplicated `work_id` values exist.
8. **Work ID correctness**
   - **ERROR** if `work_id != "doi:" + doi` (when DOI is present).
   - **WARN** if `doi_url != "https://doi.org/" + doi` (can be corrected automatically).

---

## 3) Provenance / audit checks

9. **`sources_json` is valid JSON**
   - **ERROR** if JSON parsing fails.
10. **Field winners refer to known providers**
   - **WARN** if `sources_json.field_winners.*` contains an unknown provider string.
11. **Required provenance for key derived fields**
   - **WARN** if `abstract` is non-null but `abstract_source` is null.
   - **WARN** if `publication_year` non-null but `publication_year_source` null.
   - **WARN** if `references_json` non-empty but `references_source` null.
12. **Error reporting completeness**
   - **ERROR** if a provider call failed (tracked in `sources_json`) but `errors_json` is empty.
   - **WARN** if `errors_json` is invalid JSON or not an array.

---

## 4) Scalar field consistency checks

13. **Title presence**
   - **WARN** if `title` is empty/null (a work without a title is usually a retrieval failure).
14. **Language code sanity**
   - **WARN** if `title_language` present but not a plausible language tag (e.g., not 2–3 letters).
15. **Publication year plausibility**
   - **ERROR** if `publication_year` is non-null and not an integer.
   - **WARN** if `publication_year` < 1600 or > current_year+1 (configurable).
16. **Published date + precision consistency**
   - **WARN** if `published_date_precision="day"` but date is not `YYYY-MM-DD`.
   - **WARN** if `published_date_precision="month"` but date is not `YYYY-MM`.
   - **WARN** if `published_date_precision="year"` but date is not `YYYY`.
17. **Type controlled vocabulary**
   - **WARN** if `type` not in an allowed set (you can maintain a mapping table).

---

## 5) JSON field structure checks (authors, genders, institutions, countries, references)

### A) `authors_json`
18. **Valid JSON array**
   - **ERROR** if not valid JSON or not a list.
19. **Author ordinal integrity**
   - **ERROR** if any author missing `ordinal`.
   - **ERROR** if ordinals are not `1..author_count` with no gaps/duplicates.
20. **Author name integrity**
   - **WARN** if `name` empty for any author.
   - **WARN** if both `given` and `family` are missing (name parsing failure).
21. **ORCID format**
   - **WARN** if `orcid` present but not a valid ORCID URL or checksum format.
22. **`author_count` matches**
   - **ERROR** if `author_count != len(authors_json)`.

### B) `author_genders_json`
23. **Alignment with authors**
   - **ERROR** if not a JSON array.
   - **WARN/ERROR** if it contains ordinals not present in `authors_json`.
   - **WARN** if any author ordinal missing from gender list (if you require full alignment).
24. **Gender controlled values**
   - **WARN** if gender not in `{male, female, nonbinary, unknown}`.
25. **Probability sanity**
   - **WARN** if `prob` present and not in `[0,1]`.
   - **WARN** if `method="none"` but `prob` is non-null (inconsistent).

### C) `institutions_json`
26. **Valid JSON array + uniqueness**
   - **WARN** if duplicates by `ror` or normalized `name`.
27. **ROR URL sanity**
   - **WARN** if `ror` present but not `https://ror.org/<id>`.
28. **Country code sanity**
   - **WARN** if `country_code` present but not ISO-3166-1 alpha-2.

### D) `countries_json`
29. **Valid JSON array + uniqueness**
   - **WARN** if duplicates.
30. **ISO country code validation**
   - **WARN** if any `country_code` not in ISO alpha-2 list (keep a local allowlist).
31. **Provenance field present**
   - **WARN** if missing `source` for any entry (auditability).

### E) `references_json`
32. **Valid JSON array**
   - **ERROR** if not valid JSON or not a list (if you claim references present).
33. **Reference ordinal integrity**
   - **WARN** if ordinals missing or not sequential (some sources don’t guarantee order—decide strictness).
34. **Reference DOI normalization**
   - **WARN** if `doi` present and not lowercase / not valid pattern.
   - **WARN** if `work_id` present but inconsistent with `doi` (should be `doi:<doi>`).
35. **Reference count consistency**
   - **WARN** if `reference_count_reported` exists and differs a lot from `len(references_json)` (allow mismatch because sources can disagree; treat as QA signal).
36. **At least one of (doi/work_id/unstructured)**
   - **WARN** if a reference object has none of these populated (useless reference).

---

## 6) Cross-field coherence checks (spot silent merges/parsing bugs)

37. **Abstract must be plain text**
   - **WARN** if `abstract` contains obvious XML/HTML tags (`<jats:p>`, `<p>`, etc.)—indicates cleaning failed.
38. **Container title presence for journal-articles**
   - **WARN** if `type="journal-article"` and `container_title` null (possible missing metadata).
39. **Publisher plausibility**
   - **WARN** if publisher is present but extremely short (e.g., 1–2 chars) or numeric (parse issue).
40. **OA consistency**
   - **WARN** if `open_access_json` says `is_oa=true` but `best_oa_url` null (depending on your rules).

---

## 7) Output artifacts for audit-friendliness (recommended)

Produce two extra outputs (doesn’t violate “step1.xlsx one row per DOI”):
1. **`validation_report.xlsx` or `validation_report.jsonl`**
   - One record per issue: `doi`, `work_id`, `severity`, `check_id`, `message`, `details`.
2. **`run_manifest.json`**
   - Pipeline version, config, list of input DOIs (normalized), timestamps, provider endpoints, and counts.

If you must keep everything inside `step1.xlsx`, add:
- `qa_status` (string: `ok`/`warn`/`error`)
- `qa_issues_json` (JSON array of check IDs/messages)

---

## Minimal “must-have” checks (if you only implement 8)
1) row count matches input; 2) `input_row` 0..N-1; 3) `doi` valid + lowercase; 4) unique `doi`; 5) `work_id` matches; 6) JSON columns parseable; 7) author ordinals + `author_count` consistent; 8) provenance present for abstract/year/references when those fields are present.

If you tell me whether you’ll treat **missing abstract** as acceptable (WARN) or unacceptable (ERROR), I can mark severities accordingly and suggest thresholds (e.g., “≥70% of rows have abstracts” for a run-level WARN).

## @liya-oz

the most uncertain fields are likely author gender and countries where the research took place and possibly full list of references. propose solution according best practices. what limitations I should explicitly write in my narrative document

## Copilot

## Best-practice approach for the uncertain fields (gender, countries, references)

### 1) Author gender (high uncertainty; treat as *probabilistic* enrichment)

**Recommended solution**
- **Make gender inference explicitly optional and non-blocking.** Your pipeline should always succeed without it.
- Store gender as a **prediction object**, not a single label:
  - `gender` in a controlled set: `male | female | nonbinary | unknown`
  - `prob` (0–1) and `method` (e.g., `name_api_v1`, `none`)
  - `evidence` (what was used): usually given name + locale hint (if any)
- Prefer inference **only when you have a usable given name**:
  - Skip (set `unknown`) when author is initials-only, organization author, or the given name is missing.
- Use conservative thresholds:
  - If confidence below threshold (e.g., `prob < 0.8`), output `unknown` (or keep label but flag `low_confidence=true`; I’d prefer `unknown` for downstream safety).
- Keep outputs **aligned to author ordinals** (`ordinal`) so you can audit which author got which label.
- For reproducibility:
  - Version your inference method/dataset and record it (e.g., `gender_model_version` in `sources_json`).
  - Cache raw responses from the gender service (or store only hashed + timestamp if policy requires).

**Key design principle**
- Treat this as “gender *from name*” not “gender identity.” Use it only for aggregate-level exploratory analysis unless validated.

---

### 2) Countries “where the research took place” (ambiguous; define operationally)

This field is often underspecified in metadata. Best practice is to **separate two concepts**:

1) **`countries_authors_affiliations`** (what you can infer reliably)
- Derive from author affiliation/institution metadata:
  - Use OpenAlex institutions (`country_code`) and/or ROR if present.
  - If only free-text affiliations exist, parse cautiously and map to ISO-3166-1 alpha-2 (with low confidence).
- Output as JSON objects with provenance:
  - `country_code`, `source` (`openalex_institution`, `ror`, `affiliation_text`), and optional `count_authorships`.

2) **`countries_study_context`** (what you *usually can’t* infer reliably from APIs)
- Only populate when explicitly available from a trusted structured field (rare) or from full-text NLP (out of MVP scope).
- For MVP, default to **null/empty** and state it explicitly.

**Recommended solution (MVP)**
- In `countries_json`, document that it represents **countries of contributing institutions** (affiliation-based), not study location.
- If you must keep the wording “countries of research,” clarify in the narrative: *“operationalized as affiliation countries.”*

---

### 3) Full list of references (coverage + completeness vary by provider)

**Recommended solution**
- Implement a **tiered references strategy** with provenance:
  1. **Crossref `reference[]`** when present (often closest to publisher-deposited reference list; may be unstructured).
  2. **OpenAlex `referenced_works`** as fallback (excellent coverage as IDs; may require expansion calls to get citation strings/DOIs).
  3. Optional: **Semantic Scholar** as a targeted fallback when you need structured refs and OpenAlex/Crossref are thin.
- Represent each reference entry with:
  - `ref_ordinal`
  - `work_id` (prefer `doi:<doi>` if DOI known; else OpenAlex/S2 ID)
  - `doi` (normalized) when available
  - `unstructured` string when you have it (Crossref often)
  - `source` per reference or a row-level `references_source`
- Decide and document what “full reference list” means in MVP:
  - **Best practice:** “full list as provided by the chosen provider,” not a guarantee of completeness vs the PDF.
  - Include `reference_count_reported` vs `len(references_json)` to surface mismatches.

**Operational guardrails**
- Do not fail the row if references are missing; emit:
  - `references_json = []`
  - add a WARN to `errors_json` like `references_missing`.

---

## Limitations to state explicitly in your narrative (recommended wording themes)

### Gender
- **Not ground truth:** “Gender is inferred from names and may not reflect gender identity.”
- **Coverage bias:** “Many authors cannot be classified (initials-only, non-Western names, organization authors), leading to `unknown`.”
- **Model bias:** “Name-to-gender tools encode cultural/linguistic bias and have unequal accuracy across regions and name origins.”
- **Binary limitation:** “Most public name-based services are binary; we map outputs conservatively and include `unknown`/`nonbinary` only when explicitly supported.”
- **Reproducibility caveat:** “Even with caching, upstream services/datasets can change; we version the method and timestamp retrieval.”

### Countries
- **Operational definition:** “Countries are derived from author affiliation/institution locations (contributors’ countries), not necessarily where the study took place.”
- **Missing affiliations:** “If affiliations are absent or unstructured, country inference is incomplete and may be wrong.”
- **Multi-country ambiguity:** “Collaborations produce multiple countries; we represent a set with provenance rather than a single ‘country of research’.”
- **Institution resolution limits:** “Institution identifiers (ROR/OpenAlex) are not always available; string-based geocoding is heuristic and may misclassify.”

### References
- **Not guaranteed complete:** “Reference lists depend on what the provider has indexed or what publishers deposited; they may be partial compared to the article PDF.”
- **Unstructured refs:** “Some references are only available as unstructured strings; DOIs may be missing.”
- **Provider disagreement:** “Different sources disagree on counts and composition; we record the source and keep the raw reference payload when available.”
- **Graph vs citation text:** “OpenAlex provides references as linked IDs; generating formatted citations may require additional calls and can introduce mismatch with the publisher’s reference formatting.”

### General (helps defensibility)
- **Source provenance:** “Each field is traced to a provider (‘field winner’) and raw responses are cached for audit.”
- **Non-blocking enrichment:** “Uncertain enrichments (gender, countries, references) never block extraction; missing values are explicit.”
- **Ethics/privacy:** “We only use publicly available metadata; no personal data beyond published author names and public identifiers (e.g., ORCID).”

---

If you want, I can propose a small set of **confidence scoring rules** (e.g., `country_confidence: high/medium/low`, `gender_confidence`) and exactly when to downgrade to `unknown`, so your narrative can describe a clear, reproducible policy rather than ad hoc decisions.

## @liya-oz

Ok, so here is my plan: Build a reproducible Python pipeline: CSV of DOIs → step1.xlsx (one row per DOI), structured for future Graph RAG use.

For the MVP, I going to use both Crossref  and OpenAlex. why? because Crossref is strong for DOI-centric bibliographic metadata (title, publication year/date, authors), while OpenAlex adds graph-ready identifiers and better normalization for authorship, institutions, and affiliation-derived country codes. 

DOIs should be lowercased and cleaned and each paper is assigned a stable `work_id = "doi:" + doi` with provenance captured so each field can be traced back to its source.

Key limitations are that the abstracts and reference lists are not guaranteed to be available in the source, countries where the research took place is operationalized as affiliation/institution countries (not necessarily the study site), and author gender is at best a cautious..

Analiz and evaluate.

*System: User retried message*

## Copilot

Your plan is coherent and defensible for an MVP, and it’s aligned with “graph-ready” design. Below is an evaluation of what’s strong, what’s underspecified, and a few concrete tweaks that will make the narrative and implementation harder to critique.

## What’s strong / defensible

1. **Source pairing makes sense**
   - **Crossref** as the DOI-native bibliographic baseline (title, issued/published dates, author order).
   - **OpenAlex** for *graph normalization*: stable IDs for works/authors/institutions and affiliation-derived country codes (plus referenced works graph).
   - This division of labor is a widely accepted pattern.

2. **Reproducibility and auditability are addressed**
   - DOI normalization + a deterministic `work_id = doi:<doi>` is exactly the kind of stable anchor you want for downstream Graph RAG ingestion.
   - Calling out provenance per field is the right narrative move; it explains disagreements and future re-runs.

3. **Limitations are honestly stated**
   - Abstract/reference availability is an inherent limitation of metadata-only pipelines.
   - Operationalizing “countries of research” as affiliation countries is appropriate for MVP—*as long as you state it clearly* (you do).
   - Treating gender inference as cautious is correct.

## Gaps / ambiguity to fix (so reviewers can’t poke holes easily)

1. **Define deterministic merge rules (critical)**
   You say provenance is captured, but you also need to state *how the pipeline decides* which source populates each field when they differ.
   - Example narrative snippet:  
     “For each field we apply a deterministic priority order and record the `field_winner` (e.g., title: Crossref → OpenAlex; affiliations/countries: OpenAlex → Crossref). Conflicts are not manually resolved.”

2. **Abstract handling needs a concrete policy**
   With Crossref+OpenAlex, abstract coverage may be patchy.
   - State:  
     - which provider you prefer for abstract,
     - how you convert OpenAlex `abstract_inverted_index` to text,
     - how you validate it (e.g., strip tags; reject if it still looks like XML).

3. **References: clarify what “full reference list” means in MVP**
   Right now your narrative implies “full reference list”, but the providers may only have partial lists.
   - Make it explicit:  
     “References are captured as provided by Crossref (publisher-deposited `reference[]`) when available; otherwise OpenAlex referenced work IDs are stored. Completeness vs the publisher PDF is not guaranteed.”
   - Include both `reference_count_reported` and `references_extracted_count` so users can see gaps.

4. **OpenAlex key requirement / rate-limit risk should be acknowledged**
   OpenAlex now effectively requires an API key for real use and has budget-based limits. Even with 20 DOIs, you should mention this in the risk section:
   - “OpenAlex requires an API key and enforces daily budget limits; we minimize calls by using singleton lookups and caching.”

5. **Gender statement should be completed and framed precisely**
   You ended with “at best a cautious..” — finish it as a specific limitation:
   - “Author gender is an optional, probabilistic enrichment inferred from given names; it does not represent gender identity; results include `unknown` when confidence is low or names are ambiguous.”

## Risk assessment (quick)

- **Coverage risk (medium):** abstracts and references will be missing for some DOIs; mitigated by explicit nulls + provenance + completeness metrics.
- **Implementation complexity (low–medium):** manageable; the main tricky parts are OpenAlex abstract reconstruction and reference representation.
- **Reproducibility risk (low if cached):** metadata can change over time; mitigate by caching raw JSON responses and recording retrieval timestamps + pipeline version.
- **Ethical risk (medium for gender):** mitigate by making it optional, conservative thresholds, and clear disclaimer.

## Small narrative upgrades (high leverage)

Add 4 explicit sentences (these make the design “review-proof”):
1. **Deterministic merge:** “Each field uses a deterministic source priority; conflicts are resolved by rule, not by manual editing.”
2. **Provenance:** “For every populated field, we store the source provider and retrieval timestamp; raw API payloads are cached for audit.”
3. **References definition:** “Reference lists are ‘as available in metadata sources’ and may be incomplete relative to full text.”
4. **Country definition:** “Country is operationalized as affiliation/institution country codes, not study location.”

## Optional but recommended: define a fallback
Even if you don’t implement it now, mention:  
“If abstract/reference coverage is insufficient, we will add Semantic Scholar as a targeted fallback source only for missing fields.”

If you want, paste your intended `step1.xlsx` column schema (or the draft you have), and I’ll point out any places where provenance/normalization/conflict rules are still ambiguous.

## @liya-oz

Ok, so here is my plan: Build a reproducible Python pipeline: CSV of DOIs → step1.xlsx (one row per DOI), structured for future Graph RAG use.

For the MVP, I going to use both Crossref  and OpenAlex. why? because Crossref is strong for DOI-centric bibliographic metadata (title, publication year/date, authors), while OpenAlex adds graph-ready identifiers and better normalization for authorship, institutions, and affiliation-derived country codes. 

DOIs should be lowercased and cleaned and each paper is assigned a stable `work_id = "doi:" + doi` with provenance captured so each field can be traced back to its source.

Key limitations are that the abstracts and reference lists are not guaranteed to be available. I will use "unknown".

Analiz and evaluate.

*System: User retried message*

## Copilot

Your plan is directionally strong and defensible for an MVP—especially for “graph-ready” outputs with stable IDs and provenance. A few points need tightening to be technically accurate, reproducible, and narratively consistent.

## What’s solid
- **Provider choice logic is coherent:** Crossref as DOI-centric baseline; OpenAlex as graph-normalized enrichment (author/institution IDs, country codes).
- **Stable IDs:** `work_id = "doi:" + doi` is a good, deterministic primary key for downstream DB/Graph ingestion.
- **Provenance-first mindset:** essential when sources disagree or fields are missing.
- **Explicitly acknowledging missingness:** correct—abstracts and complete references are the main weak points of metadata-only pipelines.

## Gaps / corrections to make your narrative and implementation stronger

### 1) “Use ‘unknown’” needs to be type-specific
- For **scalar strings** (e.g., abstract, title), prefer **null/blank** rather than the literal string `"unknown"`—it’s easier for databases and avoids conflating “unknown” with a real textual value.
- For **controlled vocab fields** (e.g., gender), `"unknown"` is appropriate.
- For **lists** (authors, countries, references), prefer `[]` (empty list) plus an audit flag in `errors_json`.

**Narrative adjustment:** say “missing values are represented explicitly as null/empty lists; controlled vocab fields use `unknown`.”

### 2) Abstract and references: be precise about what you can/can’t guarantee
- Crossref **rarely** has abstracts; OpenAlex sometimes has abstracts (in inverted index form). So “not guaranteed” is correct, but you should add that **coverage is dataset-dependent** and not under your control.
- References:
  - Crossref `reference[]` may be absent even when `reference-count` exists.
  - OpenAlex often has `referenced_works` IDs, but that’s not the same as a “publisher-formatted full reference list.”

**Narrative adjustment:** define your MVP “references” output as *“reference links/identifiers when available (DOI/OpenAlex IDs) plus unstructured strings when provided by Crossref.”*

### 3) Reproducibility: you need one more commitment
If you truly want “reproducible end-to-end,” add at least one of:
- **raw response caching** (per DOI per provider, write JSON to disk), or
- a **run manifest** (timestamps + provider versions/URLs + pipeline git commit hash).

Without caching, you can still be deterministic given the APIs at run time, but results may drift as metadata updates upstream.

**Narrative adjustment:** “We cache raw API responses and record retrieval timestamps + pipeline version to support audit and reruns.”

### 4) Handle conflicts explicitly (publication year/date especially)
Crossref and OpenAlex can disagree on year/date. Your narrative should specify a deterministic tie-break rule, e.g.:
1) Crossref `issued` year, else
2) Crossref `published-online` / `published-print`, else
3) OpenAlex `publication_year`.

And record `publication_year_source`.

**Narrative adjustment:** “When sources disagree, we select fields using a documented precedence order and record the winner per field.”

### 5) OpenAlex operational risk: API key requirement + budget limits
Given your earlier OpenAlex notes: OpenAlex now effectively requires an API key for real usage and has budget-based limits. This is not a blocker for 20 DOIs, but it *is* a risk you should mention.

**Narrative addition:** “OpenAlex requires an API key and imposes budget-based rate limits; for MVP scale this is manageable.”

## What I’d change in one paragraph (suggested tightened narrative)
- Replace “I will use ‘unknown’” with: “Missing values are represented as null/empty lists; uncertain categorical enrichments use `unknown` and include provenance.”

## Minimal evaluation criteria (so you can defend success/failure)
Define quantitative MVP acceptance checks (even informal), e.g.:
- ≥95% rows have `title` and `publication_year`
- authors present for ≥90%
- abstracts present for ≥X% (your DOI set-dependent; set expectation low)
- references present as IDs/strings for ≥X%
- 100% rows have `work_id`, valid normalized `doi`, and non-empty `sources_json`

If you want, paste your intended column schema and I’ll point out where “unknown vs null” and provenance fields should go to make the dataset maximally database/Graph-RAG ingestible.

## @liya-oz

Here’s MVP plan: (i use 2 public API: Crossref + OpenAlex):

Build a reproducible pipeline: CSV of DOIs - step1.xlsx (one row per DOI), Graph RAG–friendly (stable IDs + provenance).
1. Normalize DOI (extract/trim/lowercase) and set work_id = "doi:" + doi.
2. Crossref = baseline bibliographic metadata; OpenAlex = graph IDs + author/institution normalization + affiliation-derived country codes.
3. Missing data handling: null/blank for scalar fields, [] for lists, and unknown only for controlled vocab (e.g., gender). Never fail the run for a single DOI; log status/errors per row.
4. References: store what Crossref/OpenAlex provide (Crossref may give unstructured refs + DOIs; OpenAlex may give referenced work IDs).
5. Document limitations: abstract/reference coverage is not guaranteed; “countries” is affiliation-based proxy; gender is cautious .

Request: Please critique this plan on (1) technical correctness, (2) reproducibility/auditability, and (3) likelihood of meeting task Step1 scoring: 
Step 1 (60% of score)
Your task is to use Python and any publicly available APIs to extract the following information about these journal articles into a structured Excel output:
Article Title
Abstract
Year Published
Author first name(s)
Author last name(s)
Author gender(s)
Countries where the research took place
Complete list of references from the article

Deliverable: Excel spreadsheet of the extracted data. Name this file “step1.xlsx”.

. Then propose the minimum set of changes I should adopt (still MVP-simple)

Keep the response concise and specific.

*System: User retried message*

## Copilot

## Critique

### (1) Technical correctness
- **DOI normalization / work_id**: correct and graph-friendly.
- **Crossref baseline + OpenAlex enrichment**: technically sound. OpenAlex is well-suited for stable author/institution IDs and affiliation country codes.
- **Missing data policy**: good (null/[]/controlled `unknown`). Make sure you distinguish “missing” vs “not attempted”.
- **References strategy**: correct *as a capture strategy*, but it may not satisfy “complete list of references from the article” if interpreted literally as “as in the PDF”.
- **Big technical gap vs rubric**: **abstract and “complete references” coverage**. Crossref often lacks abstracts; OpenAlex abstracts are present for some but not all (inverted index). References: OpenAlex gives IDs; Crossref gives unstructured refs for some publishers only.

### (2) Reproducibility / auditability
- Strong start with per-row errors.
- Missing pieces to make it defensible as “reproducible end-to-end”:
  - **Record raw API payloads** (or at least hashes) and the **exact endpoints/params** used per DOI.
  - **Record field-level provenance** (which source supplied each final field), not just “Crossref baseline / OpenAlex enrichment”.
  - **Versioning**: pipeline version + run timestamp + API key presence (OpenAlex) should be captured.
  - **Deterministic merge rules**: define exact precedence for year/title/authors and document it (otherwise runs can vary when providers disagree).

### (3) Likelihood of meeting the Step1 scoring (60%)
Field-by-field risk assessment with your current plan:

- **Title**: high likelihood (Crossref/OpenAlex both strong).
- **Year published**: high likelihood (both strong; minor conflicts).
- **Author first/last names**: high likelihood (Crossref is usually good; OpenAlex also).
- **Abstract**: **medium-to-low** likelihood of full coverage across arbitrary DOIs (many will be missing).
- **Author genders**: **medium** (you can always output `unknown`, but scoring likely expects non-trivial coverage; also needs a public method/data source—your plan doesn’t specify one).
- **Countries where the research took place**: **low** if interpreted as study location; **medium** if graders accept affiliation-country proxy. Your plan correctly calls it a proxy, but scoring text says “took place”.
- **Complete list of references**: **medium-to-low**. For many DOIs, Crossref will not have full references; OpenAlex provides referenced work IDs but not necessarily the exact reference strings “from the article”.

Net: the plan is solid engineering-wise, but **at risk on abstracts + complete references + interpretation of “countries of research”**.

---

## Minimum set of changes (still MVP-simple, but improves score + defensibility)

1) **Add explicit field-level provenance columns**
- Add: `field_winners_json` (or embed in `sources_json`) recording source for `title`, `abstract`, `year`, `authors`, `countries`, `references`.
- Why: auditability + easy narrative defense.

2) **Cache raw responses per DOI per provider**
- Save `crossref_{doi}.json` and `openalex_{doi}.json` (or one JSONL file with both payloads).
- Add `crossref_status`, `openalex_status`, and optionally `payload_sha256` columns.
- Why: makes “reproducible end-to-end” credible, and helps debug missing fields.

3) **Define deterministic merge rules (write them down + enforce)**
- Example: title/year/authors precedence order (Crossref vs OpenAlex) + tie-breakers.
- Why: avoids silent drift and inconsistent outputs.

4) **Abstract handling improvement (still within Crossref+OpenAlex)**
- Implement OpenAlex abstract reconstruction from `abstract_inverted_index`.
- If abstract missing in both: leave null, but log `abstract_missing`.
- Why: maximizes abstract coverage without adding new APIs.

5) **References: make output usable even when “complete” isn’t available**
- Keep your current approach, but:
  - Ensure `references_json` is always an ordered array with `ref_ordinal`.
  - For OpenAlex-only references, include `work_id` for each referenced work and (optionally) do a **single batched OpenAlex OR query** to resolve DOIs/titles for referenced works up to a cap (e.g., first 50) to improve “complete list” appearance without exploding API calls.
  - Add `references_completeness_note` (or a flag) when `reference_count_reported` > `len(references_json)` or when refs are IDs-only.
- Why: raises practical completeness while staying MVP.

6) **Countries: rename/clarify in the spreadsheet (or add a second column)**
- Add `countries_affiliation_json` (your current one) and optionally `countries_research_location_json` (leave empty for MVP).
- If you must keep one column named like the rubric, add `countries_definition` column or a `countries_method` value = `affiliation_proxy`.
- Why: reduces ambiguity and narrative risk.

7) **Gender: make it explicitly “unknown” unless you have a public inference method**
- If you haven’t picked a public gender method, don’t half-implement it. Either:
  - (A) ship MVP with all `unknown` + very explicit limitation (risk: scoring), or
  - (B) add a lightweight public name-to-gender step with confidence + opt-out rules, and record `method` + `version`.
- Minimum change: add `author_genders_json` schema + `gender_method` even if mostly unknown, so the pipeline is ready and auditable.

---

### One sentence you can use in your narrative (defensible)
“We prioritize provenance and reproducibility by caching raw Crossref/OpenAlex responses, applying deterministic merge rules, and explicitly labeling uncertain enrichments (gender, affiliation-based countries, and reference completeness) rather than emitting ambiguous free text.”

If you tell me whether you’re allowed to add **one more public API** (e.g., Semantic Scholar only for abstracts/references), I can give you an even smaller change-set that materially increases Step1 coverage—but the above stays within your stated two-API constraint.
