# ground-truth

Multi-agent system that generates decision-ready CSVs from official UN data,
with a validator that checks every number against the source before it's trusted.

UN Open Source Week Hackathon — Challenge 3

## Structure
- /orchestrator — Strands agents that generate the CSV (pulls from UN Data Commons API)
- /validator — checks generated numbers against source
- /docs — design notes

## Validator
Returns a verdict for each AI-claimed number:
- BACKED — matches the most recent source (with source link)
- STALE — real but outdated; a newer figure exists
- NOT_FOUND — no source match (likely fabricated)
- REDUNDANT — same value counted twice; not independent

### How the validator agent calls it
    from validator import parse_observations, validate
    sources = parse_observations(commons_response, variable, entity)
    verdict = validate(claimed_number, sources)
    # verdict.status -> BACKED / STALE / NOT_FOUND / REDUNDANT
    # verdict.matched_source.provenance_url -> source link

## Run
    python validator/validator.py
