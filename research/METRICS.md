# Metrics log

Paste outputs from `triage complexity` and `triage eval` here as you run them.

## Complexity

Captured 2026-10-17 via `uv run python -m triage complexity`:

| Module | code_lines | functions | classes |
|--------|------------|-----------|---------|
| `vega_engine.py` | 51 | 2 | 1 |
| `llm_engine.py` | 213 | 10 | 4 |
| `contract.py` (shared) | 115 | 4 | 2 |

**Delta:** LLM engine is **+162 code lines** vs Vega for the same job (prompt, HTTP client, JSON extract, schema validate, repair loop, confidence floor).

## Eval — llm (simulated)

Offline stand-in (`client: simulated`) — orchestration only; **not** a fair accuracy contest vs Vega or a frontier LLM.

```json
{
  "engine": "llm",
  "n": 18,
  "team_accuracy": 0.5,
  "priority_accuracy": 0.22,
  "needs_human_accuracy": 0.89,
  "forced_wrong_team_rate": 0.056,
  "needs_review_rate": 0.44,
  "abstain_rate": 0.44,
  "mean_parse_attempts": 1.06,
  "mean_repair_rounds": 0.056,
  "mean_schema_failures": 0.056
}
```

Repair path exercised by fixture `broken-json-marker`.

## Eval — vega

```text
# uv run python -m triage eval --engine vega
(pending — downloads/loads local weights; run when ready)
```

## Eval — llm (live)

```text
# export OPENAI_API_KEY=...
# uv run python -m triage eval --engine llm
(pending)
```

## Interpretation notes

- Primary research signal for LLM engineers: **glue LOC / repair machinery**, not the simulated keyword accuracy.
- Compare Vega eval next for `forced_wrong_team_rate` and `abstain_rate` on the same fixtures.
- With a live LLM, re-check whether parse/repair rounds drop to ~0 and whether forced-wrong still appears without abstain.
