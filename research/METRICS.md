# Metrics log

Captured on 2026-10-19.

## Complexity (fair breakdown)

`uv run python -m triage complexity`:

| Bucket | LOC | Counts as… |
|--------|-----|------------|
| `http_client` | 53 | Transport (exclude from semantic claim) |
| `offline_simulator` | 64 | Test double (exclude) |
| `parse_repair` | 13 | Freeform fence/JSON recovery |
| `core_triage` (vega) | 47 | System One mapping |
| `core_triage` (llm freeform) | 80 | Prompt loop + validate + repair + policy |
| `core_triage` (llm_structured) | 85 | JSON-mode loop + validate + policy |

| Fair semantic delta vs Vega | LOC |
|-----------------------------|-----|
| Freeform (`core` + `parse_repair`) | **+46** |
| Structured (`core` only) | **+38** |

| Prompt chars | |
|--------------|--:|
| LLM system prompt | 657 |
| LLM repair prompt | 118 |
| Vega instructions + criteria | 560 |

## Eval — three engines (post fixture pass)

`n=18`, **n_scored=17** (glue probe excluded), live LLM API for `llm` / `llm_structured`.

| Metric | Vega | LLM freeform | LLM structured |
|--------|------|--------------|----------------|
| team_accuracy | **0.765** | **0.765** | **0.765** |
| priority_accuracy | 0.294 | **0.647** | **0.647** |
| needs_human_accuracy | 0.471 | **0.941** | **0.941** |
| forced_wrong_team_rate | 0.059 | **0.0** | **0.0** |
| needs_review_rate | 0.444 | 0.444 | 0.444 |
| abstain_rate | 0.167 | 0.167 | 0.167 |
| mean_parse_attempts | **0** | 1.0 | 1.0 |
| mean_repair_rounds | **0** | 0.0 | 0.0 |
| Fair semantic LOC vs Vega | 0 | +46 | +38 |

### Raw JSON

**vega**
```json
{
  "engine": "vega",
  "n": 18,
  "n_scored": 17,
  "n_glue_only": 1,
  "team_accuracy": 0.765,
  "priority_accuracy": 0.294,
  "needs_human_accuracy": 0.471,
  "forced_wrong_team_rate": 0.059,
  "needs_review_rate": 0.444,
  "abstain_rate": 0.167,
  "mean_parse_attempts": 0.0,
  "mean_repair_rounds": 0.0,
  "mean_schema_failures": 0.0
}
```

**llm**
```json
{
  "engine": "llm",
  "n": 18,
  "n_scored": 17,
  "n_glue_only": 1,
  "team_accuracy": 0.765,
  "priority_accuracy": 0.647,
  "needs_human_accuracy": 0.941,
  "forced_wrong_team_rate": 0.0,
  "needs_review_rate": 0.444,
  "abstain_rate": 0.167,
  "mean_parse_attempts": 1.0,
  "mean_repair_rounds": 0.0,
  "mean_schema_failures": 0.0
}
```

**llm_structured**
```json
{
  "engine": "llm_structured",
  "n": 18,
  "n_scored": 17,
  "n_glue_only": 1,
  "team_accuracy": 0.765,
  "priority_accuracy": 0.647,
  "needs_human_accuracy": 0.941,
  "forced_wrong_team_rate": 0.0,
  "needs_review_rate": 0.444,
  "abstain_rate": 0.167,
  "mean_parse_attempts": 1.0,
  "mean_repair_rounds": 0.0,
  "mean_schema_failures": 0.0
}
```

## Fixture label pass

| Change | Why |
|--------|-----|
| `tech-crash` priority 2 → 1 | Single-user settings crash |
| `broken-json-marker` `eval.accuracy=false` | Glue probe only |
| Notes on soft labels | GDPR / pricing / ambiguous documented |

## Interpretation

1. **Team routing tied** at 76.5% across all three — judgment quality on team is not the differentiator here.
2. **Live LLM wins** priority + needs_human and has **0** forced-wrong; Vega still has ~1/17 forced-wrong.
3. **`llm` ≈ `llm_structured` on accuracy** this run (clean JSON both ways); structured’s win is **code shape** (+38 vs +46 semantic LOC), not fixture score.
4. **Glue claim holds:** same team accuracy without parse/repair machinery on Vega; structured shrinks freeform glue but does not match Vega’s zero parse layer.
5. **n=17 scored** is a sandbox — directional, not a benchmark paper.
