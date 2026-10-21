# gluecut

Cut LLM prompt/parse/repair glue. Keep a deterministic shell. Use System One (Vega) for typed decisions.

Domains: **support triage** + **payment failure → reason code**.

Pitch docs for staff engineers: [`research/ADOPT.md`](research/ADOPT.md) · frozen labels: [`research/RUBRIC.md`](research/RUBRIC.md).

## Setup

```bash
uv sync --group dev
uv sync --group dev --extra vega   # local Vega weights
```

## Commands

```bash
# Fair LOC breakdown
uv run python -m triage complexity

# Strong baseline = Pydantic + OpenAI json_schema (not fence-parse)
uv run python -m triage decide --engine llm_schema --text "Please refund my last invoice."
uv run python -m triage decide --engine vega --text "Please refund my last invoice."

# Held-out eval (≥100 triage cases)
uv run python -m triage eval --engine llm_schema
uv run python -m triage eval --engine vega

# Shadow mode → research/disagreements.md (+ forced-wrong, abstain, $)
uv run python -m triage shadow --engines vega llm_schema

# Cost/latency at fixed QPS → research/bench.md
uv run python -m triage bench --engines vega llm_schema --qps 1 --limit 30

# Second domain
uv run python -m triage payments-eval --engine llm_schema
uv run python -m triage payments-eval --engine vega

# Shareable compare report
uv run python -m triage compare --engines vega llm_schema
```

Set `OPENAI_API_KEY` for live LLM columns (otherwise simulated).

## Layout

| Path | Role |
|------|------|
| `research/ADOPT.md` | Adopt if / don’t adopt if |
| `research/RUBRIC.md` | Frozen labeling rubric v1 |
| `research/disagreements.md` | Shadow disagreement sheet (generated) |
| `research/bench.md` | Cost/latency table (generated) |
| `fixtures/triage/held_out.jsonl` | ≥100 scored triage cases |
| `fixtures/payments/held_out.jsonl` | Payment failure cases |
| `triage/engines/llm_schema_engine.py` | Strong LLM baseline |
| `triage/payments.py` | Second domain |

## Tests

```bash
uv run pytest
```
