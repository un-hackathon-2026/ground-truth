# Front-End Integration Guide — Agentic Commons Pipeline

Everything the front-end needs to call the backend and render results.
Branch: `agentic-commons`. All paths under `src/`.

---

## The flow (two calls)

```
user types a question
        │
        ▼
get_candidates_agentic(query)   ── Phase 1: returns the choices to show
        │
   user picks one (or several)
        │
        ▼
evaluate_agentic(query, picked) ── Phase 2: returns the trust report
        │
        ▼
   render report  +  (if REVIEW) show the conflicting sources
```

Both functions live in `src/agentic_pipeline.py`.

> **Requires** `GROQ_API_KEY` in the environment (used for query parsing +
> indicator grouping). Same key the parser already uses.

---

## Phase 1 — get the candidates

```python
from src.agentic_pipeline import get_candidates_agentic

result = get_candidates_agentic("population of Kenya 2015-2020")
```

Returns a `CandidateList`:

```python
result.query        # "population of Kenya 2015-2020"
result.topic        # "population"        (the parsed concept)
result.geography    # "KEN"
result.time_range   # (2015, 2020)  or None
result.parse_error  # str or None  — if set, show it and stop
result.options      # list[CandidateOption]  ← render these as the picker
```

Each `CandidateOption`:

```python
option.index           # 1, 2, 3...   (use as the choice id)
option.indicator_name  # "Total Population"   ← show this to the user
option.indicator_code  # "Count_Person"       ← send this back in Phase 2
```

**Render:** show `indicator_name` for each option. Keep the `indicator_code`
to pass to Phase 2 when the user picks.

---

## Phase 2 — evaluate the user's pick

```python
from src.agentic_pipeline import evaluate_agentic

report = evaluate_agentic(
    "population of Kenya 2015-2020",
    selected_codes=["Count_Person"],          # the indicator_code(s) chosen
    labels={"Count_Person": "Total Population"},  # optional: id -> name
)
```

Returns a `MultiDatasetReport`:

```python
report.overall_status   # "VIABLE" | "NOT_VIABLE"
report.candidates       # list[CandidateResult]  ← one per evaluated dataset
report.chain            # list[ChainRecommendation]  (related queries)
report.parse_error      # str or None
```

Each `CandidateResult`:

```python
c.verdict                 # "PASS" | "REVIEW" | "REJECT"   ← the headline badge
c.operational_explanation # plain-English assessment paragraph
c.dataset_info            # see below
c.dimension_scores        # see below
```

`c.dataset_info`:

```python
.indicator_name   # "Total Population"
.indicator_code   # "Count_Person"
.geography        # "KEN"
.source_org       # "WorldDevelopmentIndicators"
.years_in_data    # (2015, 2020)
.row_count        # number of observations
.last_updated     # "2024"
.api_url          # the Commons observation endpoint
```

`c.dimension_scores` — four dimensions, each a 0..1 score:

```python
.metadata_completeness.score   # 0.0–1.0  -> show as %
.metadata_completeness.missing_fields   # ["unit", ...]
.data_quality.score
.data_quality.issues
.freshness.score
.freshness.note
.cross_source                  # may be None; if present:
.cross_source.status           # "CONFLICT" | "AGREE" | "SINGLE_SOURCE" | ...
.cross_source.spread_pct
.cross_source.source_count
.cross_source.authoritative_count
.cross_source.sources          # list of sources (see conflict view below)
```

**Verdict colours (suggested):** PASS = green, REVIEW = amber, REJECT = red.

---

## The conflict view (the REVIEW case — our differentiator)

When `c.verdict == "REVIEW"` and `c.dimension_scores.cross_source.status == "CONFLICT"`,
render the disagreeing sources so the user decides which to trust.

The sources are on the cross-source result. To get the full list with values
and provenance:

```python
from src.fetch_commons import fetch_commons_facets

sources = fetch_commons_facets(indicator_code, geography)  # e.g. "Count_Person", "KEN"
for s in sources:
    s.source_name        # "Kenya_Census"
    s.value              # 47564296.0
    s.latest_year        # 2019
    s.provenance_url     # "https://kenya.opendataforafrica.org/"
    s.measurement_method # may be None
```

**Render:** a list/table of sources, each with name, value, year, and a link to
`provenance_url`. Flag crowd-sourced ones (name contains "Wikipedia"/"Wikidata").
Make clear the tool does **not** pick — the human chooses.

---

## Fetching the raw data for charts

The Commons observation endpoint is a **POST** (not a GET URL). To get the time
series for visualisation, use the helper — it returns a ready-to-send request:

```python
from src.agentic_pipeline import commons_request

req = commons_request("Count_Person", "KEN")
# req = {
#   "method": "POST",
#   "url":    "https://.../core/api/v2/observation",
#   "body":   { "date":"", "variable":{"dcids":["Count_Person"]},
#               "entity":{"dcids":["country/KEN"]},
#               "select":["entity","variable","value","date","facet"] }
# }
```

POST `req["body"]` to `req["url"]`. The response shape:

```
response["facets"][facetId] = {importName, provenanceUrl, unit?, measurementMethod?}
response["byVariable"][var]["byEntity"]["country/KEN"]["orderedFacets"]
    = [ { "facetId": "...", "observations": [ {"date":"2019","value":...}, ... ] } ]
```

Each `orderedFacets` entry is one source; `observations` is its time series.

---

## Quickest way to see it all

Run the interactive CLI to watch the whole flow and see the exact objects:

```bash
python -X utf8 -m src.main_agentic "population of Kenya 2015-2020"
```

Pick `1` → you'll see the REVIEW verdict and the conflicting sources, which is
exactly what the UI should render.
