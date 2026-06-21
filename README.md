# ground-truth

**Trust & Viability Copilot for development data** — UN Open Source Week Hackathon, Challenge 3.

Given a natural-language question about development data, the system suggests
candidate datasets, lets the user pick one, then deeply evaluates that dataset's
trustworthiness across four dimensions — including whether independent sources
*agree* on the numbers — and returns a clear PASS / REVIEW / REJECT verdict.

Data is fetched live from the **World Bank API** and the **UN Data Commons**.

---

## How it works — two phases

**Phase 1 · `get_candidates(query)`** *(cheap, no fetching)*
The query is parsed (topic, country, time period) and matched to a set of
candidate indicators. These are returned for the user to choose from.

**Phase 2 · `evaluate_selection(query, selected)`** *(deep evaluation)*
Runs only on the indicator(s) the user selected:
1. **Fetch** the data (World Bank) and its cross-source values (UN Commons).
2. **Score four dimensions:**
   - Metadata completeness
   - Data quality
   - Freshness
   - **Cross-source agreement** — do independent sources report the same value?
     Authoritative sources (official statistics) are counted separately from
     crowd-sourced ones (Wikipedia/Wikidata).
3. **Verdict:** `PASS` · `REVIEW` · `REJECT`
   - `REVIEW` = the data may be fine, but authoritative sources disagree —
     route to a human to choose which to trust.
4. **Chain recommendations** — suggests the same indicator for neighbouring
   countries so the user can compare across a region.

The two functions are exposed for the front-end: call `get_candidates()` to
render the picker, then `evaluate_selection()` on the user's choice.

---

## Project structure

```
main.py                 CLI entry point (two-phase interactive picker)
src/
  parser.py             query -> topic + country + period   (uses Groq LLM)
  schemas.py            data contracts + TOPIC_GROUPS catalogue + neighbours
  fetch.py              World Bank API fetch
  fetch_commons.py      UN Data Commons fetch + cross-source conflict detection
  scoring.py            metadata / quality / freshness scoring
  integrate.py          cross-source -> 4th dimension, extended verdict, chain
  verdict.py            verdict rule + narration
  pipeline.py           orchestration: get_candidates + evaluate_selection
tests/                  offline tests
```

---

## Run it

```bash
pip install -r requirements.txt
# add your Groq key to a .env file:  GROQ_API_KEY=...
python main.py "child mortality rate in Kenya 2020-2024"
```

You'll be shown candidate datasets; type a number to pick one (or several, or
`all`, or paste your own World Bank indicator code). Add `--all` to skip the
picker and evaluate everything.

On Windows, prefix with UTF-8 so the report characters render:
`python -X utf8 main.py "..."`

---

## Status & known limitations

- **Works end-to-end on live API data.** Verified for population and under-5 /
  maternal mortality (cross-source detection confirmed live on Kenya population:
  5 sources, 15.7% spread).
- **Candidate indicators are drawn from a curated topic list** (`TOPIC_GROUPS`),
  not dynamic search. Next step: dynamic indicator discovery via the Commons
  search API so the tool can answer free-form queries.
- **Most World Bank indicators currently fail the metadata-completeness floor**
  (≈33%), so they return REJECT before other dimensions matter. Open question:
  loosen the floor, or pull richer metadata from the Commons.
- **Cross-source mappings** exist for 3 indicators; others return
  `NO_COMMONS_EQUIVALENT` honestly rather than guessing.

---

## Branches

- `main` / `initial` — base pipeline (3 dimensions, World Bank only).
- `cross-source-layer` — adds the cross-source conflict layer, 4th dimension,
  REVIEW verdict, chain recommendations, and the two-phase split.
