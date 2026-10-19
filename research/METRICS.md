# Metrics log

Captured on 2026-10-19 unless noted.

## Complexity

`uv run python -m triage complexity`:

| Module | code_lines | functions | classes |
|--------|------------|-----------|---------|
| `vega_engine.py` | 53 | 2 | 1 |
| `llm_engine.py` | 213 | 10 | 4 |
| `contract.py` (shared) | 115 | 4 | 2 |

**Delta:** LLM engine is **+160 code lines** vs Vega for the same job (prompt, HTTP client, JSON extract, schema validate, repair loop, confidence floor).

## Eval — vega

`uv run python -m triage eval --engine vega` (local 0.8B, after field-scoped abstain policy):

```json
{
  "engine": "vega",
  "n": 18,
  "team_accuracy": 0.778,
  "priority_accuracy": 0.389,
  "needs_human_accuracy": 0.5,
  "forced_wrong_team_rate": 0.056,
  "needs_review_rate": 0.444,
  "abstain_rate": 0.167,
  "mean_parse_attempts": 0.0,
  "mean_repair_rounds": 0.0,
  "mean_schema_failures": 0.0
}
```

## Eval — llm (simulated)

Offline stand-in (`client: simulated`) — orchestration only.

```json
{
  "engine": "llm",
  "n": 18,
  "team_accuracy": 0.5,
  "priority_accuracy": 0.222,
  "needs_human_accuracy": 0.889,
  "forced_wrong_team_rate": 0.056,
  "needs_review_rate": 0.444,
  "abstain_rate": 0.444,
  "mean_parse_attempts": 1.056,
  "mean_repair_rounds": 0.056,
  "mean_schema_failures": 0.056
}
```

## Eval — llm (live)

`uv run python -m triage eval --engine llm` with API key set (2026-10-19):

```json
{
  "engine": "llm",
  "n": 18,
  "team_accuracy": 0.722,
  "priority_accuracy": 0.667,
  "needs_human_accuracy": 0.889,
  "forced_wrong_team_rate": 0.0,
  "needs_review_rate": 0.444,
  "abstain_rate": 0.222,
  "mean_parse_attempts": 1.0,
  "mean_repair_rounds": 0.0,
  "mean_schema_failures": 0.0
}
```

Clean JSON on every case (1 parse attempt, no repairs) — glue still present in code, just idle this run.

## Side-by-side (n=18)

| Metric | Vega | LLM (live) | LLM (simulated) |
|--------|------|------------|-----------------|
| Engine code_lines | **53** | 213 | 213 |
| team_accuracy | **0.778** | 0.722 | 0.500 |
| priority_accuracy | 0.389 | **0.667** | 0.222 |
| needs_human_accuracy | 0.500 | **0.889** | 0.889 |
| forced_wrong_team_rate | 0.056 | **0.0** | 0.056 |
| needs_review_rate | 0.444 | 0.444 | 0.444 |
| abstain_rate | 0.167 | 0.222 | 0.444 |
| mean_parse_attempts | **0** | 1.0 | 1.06 |
| mean_repair_rounds | **0** | 0.0 | 0.06 |
| mean_schema_failures | **0** | 0.0 | 0.06 |

## Interpretation notes

1. **Complexity claim holds:** live LLM still carries **+160 LOC** of glue even when repair never fires.
2. **Accuracy (n=18):** Vega slightly ahead on **team** (0.778 vs 0.722); live LLM stronger on **priority** and **needs_human**; live LLM had **0** forced-wrong teams.
3. **Glue stress:** with a well-behaved model, parse/repair metrics go quiet — the cost is **code you must maintain**, not runtime retries.
4. **Safety:** same `needs_review` rate (~44%); abstain/confidence policy still matters more than raw top-1.
5. **Sandbox caveat:** n=18 is small; treat as directional, not a published benchmark.
