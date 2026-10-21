# gluecut compare report

Generated: `2026-10-21 19:45 UTC`

Fixtures: `fixtures/triage/held_out.jsonl` (n=110, n_scored=110)

LLM client label (if present): `gpt-4o-mini` (set `OPENAI_API_KEY` for live models; otherwise simulated).

## Head-to-head

| Metric | vega | llm_schema |
|--------|--------|--------|
| Semantic LOC (fair) | 48 | 73 |
| Fair delta vs Vega | 0 | +25 |
| Team accuracy | 72.7% | 94.5% |
| Priority accuracy | 51.8% | 64.5% |
| Needs-human accuracy | 78.2% | 92.7% |
| Forced-wrong team | 9.1% | 0.0% |
| Needs-review rate | 30.0% | 14.5% |
| Abstain rate | 14.5% | 4.5% |
| Mean parse attempts | 0.00 | 1.00 |
| Mean repair rounds | 0.00 | 0.00 |

## Fair complexity notes

- Semantic LOC excludes `http_client` and `offline_simulator`.
- Freeform still pays `parse_repair` (13 LOC).
- HTTP client called out separately: 82 LOC (not in semantic delta).
- Prompt chars — LLM system: 657; Vega criteria: 560.

## Reading for LLM engineers

- **Team accuracy** answers “who got the label right?”
- **Forced-wrong** answers “who auto-routed a wrong team?”
- **Fair delta vs Vega** is the glue claim after removing HTTP inflation.
- JSON mode (`llm_structured`) shrinks freeform glue; it does not remove prompt + validate + confidence policy.

## Reproduce

```bash
uv run python -m triage compare
# or
uv run python -m triage compare --fixtures fixtures/triage/held_out.jsonl
```
