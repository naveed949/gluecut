# gluecut compare report

Generated: `2026-10-19 07:55 UTC` (seeded from measured complexity + terminal eval runs; refresh with `triage compare`)

Fixtures: `fixtures/tickets.jsonl` (n=18, n_scored=17)

LLM client label (if present): `n/a` (set `OPENAI_API_KEY` for live models; otherwise simulated).

## Head-to-head

| Metric | vega | llm | llm_structured |
|--------|--------|--------|--------|
| Semantic LOC (fair) | 47 | 93 | 85 |
| Fair delta vs Vega | 0 | +46 | +38 |
| Team accuracy | 76.5% | 76.5% | 76.5% |
| Priority accuracy | 29.4% | 64.7% | 64.7% |
| Needs-human accuracy | 47.1% | 94.1% | 94.1% |
| Forced-wrong team | 5.9% | 0.0% | 0.0% |
| Needs-review rate | 44.4% | 44.4% | 44.4% |
| Abstain rate | 16.7% | 16.7% | 16.7% |
| Mean parse attempts | 0.00 | 1.00 | 1.00 |
| Mean repair rounds | 0.00 | 0.00 | 0.00 |

## Fair complexity notes

- Semantic LOC excludes `http_client` and `offline_simulator`.
- Freeform still pays `parse_repair` (13 LOC).
- HTTP client called out separately: 53 LOC (not in semantic delta).
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
uv run python -m triage compare --fixtures fixtures/tickets.jsonl
```
