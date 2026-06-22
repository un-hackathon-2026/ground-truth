# ground-truth

**Agentic Trust Copilot for UN development data** — UN Open Source Week, Challenge 3 (Agentic Copilots).

Ask a development-data question in plain English. Ground Truth searches the
**UN Data Commons** for the indicators that match, lets you choose the one you
mean, then checks whether that dataset can be *trusted* — including whether
independent sources agree on the numbers — and returns a clear
**PASS / REVIEW / REJECT** verdict with the evidence chain visible.

> Most tools answer with a number. Ground Truth tells you whether to trust it —
> and when sources disagree, it shows you the conflict and lets a human decide.

---

## How it works — the agentic flow

```
question  ->  search the Commons  ->  you pick  ->  trust check  ->  verdict
 (plain       (live indicator        (human in     (4 dimensions)   PASS /
  English)     discovery)             the loop)                      REVIEW /
                                                                     REJECT
```

1. **Discovery** — a free-form question is parsed into a concept + country, and
   the Commons `search_indicators` tool finds matching indicators live. An LLM
   groups the raw results into clean, human-readable choices (no hardcoded list).
2. **You choose** — the matching indicators are shown; you pick the one you mean
   (or paste your own Commons variable id).
3. **Verification** — the chosen indicator is fetched from the Commons and scored
   on four dimensions:
   - Metadata completeness
   - Data quality
   - Freshness
   - **Cross-source agreement** — do independent sources report the same value?
4. **Verdict** — `PASS` (trustworthy), `REVIEW` (usable, but sources disagree —
   a human chooses which to trust), or `REJECT` (not fit — try an alternative).
   On REVIEW, every conflicting source is shown with its value and provenance.

---

## Two pipelines in this repo

| Path | Entry point | Data source | Use |
|------|-------------|-------------|-----|
| **Agentic (primary)** | `src/main_agentic.py` | UN Data Commons | Free-form queries, live indicator search, Commons-native |
| Two-phase (fallback) | `src/main.py` | World Bank API | Curated indicator list; original pipeline |

The agentic path is the Challenge-3 submission flow. The two-phase path is kept
as a working fallback.

---

## Run it

```bash
pip install -r requirements.txt
# put your key in .env:  GROQ_API_KEY=...
python -X utf8 -m src.main_agentic "population of Kenya 2015-2020"
```

Pick a candidate when prompted.

**Demo queries:**
- `under-5 mortality in Kenya 2018-2022` -> **PASS** (Commons supplies the unit
  field, so metadata scores 100%)
- `population of Kenya 2015-2020` -> **REVIEW** — five sources report Kenya's
  population and disagree by ~9 million; the tool surfaces all five with
  provenance and lets a human choose.

On Windows, the `-X utf8` flag keeps the report characters rendering correctly.

---

## Project structure

```
src/
  main_agentic.py     interactive CLI for the agentic Commons flow
  agentic_pipeline.py query -> Commons search -> pick -> trust eval (Commons-native)
  commons_search.py   Commons indicator search + LLM grouping (the agentic discovery)
  fetch_commons.py    Commons multi-source fetch + cross-source conflict detection
  scoring.py          metadata / quality / freshness scoring
  integrate.py        cross-source -> 4th dimension, extended verdict, chain
  verdict.py          verdict rule + narration
  schemas.py          data contracts
  # fallback pipeline:
  main.py, pipeline.py, parser.py, fetch.py
tests/
```

See `SCORING_METHODOLOGY.md` for how each dimension is scored, and
`INTEGRATION_GUIDE_AGENTIC.md` for wiring the front-end.

---

## Design notes

- **We detect and surface conflicts; we do not auto-resolve them.** A trust tool
  should not silently pick which source is "true." On a conflict, the verdict is
  REVIEW and the human chooses, with every source's value and provenance shown.
- **Scoring is deterministic and inspectable** — the LLM parses the question and
  writes the summary; it does **not** decide the trust score. Same input -> same
  score, every time.
- **Provenance travels with the data** — every value carries its source name and
  origin URL straight from the Commons.

---

## Known limitations

- "Authoritative vs. crowd-sourced" is currently a simple split (Wikipedia /
  Wikidata flagged as crowd; everything else treated as authoritative).
- The verdict reflects the real data: some indicators legitimately REJECT when
  their data is thin or stale.
- Requires `GROQ_API_KEY` for query parsing and indicator grouping.
