# gluecut — System One vs LLM glue for typed decisions

## Audience

Engineers who already use LLMs for classification / routing / triage — not pre-AI keyword-rule authors.

## Question

For a fixed support-ticket triage job, how much **orchestration complexity** (prompts, JSON extraction, schema validation, repair retries, confidence hacks) does a System One model (Vega) remove compared with a typical LLM prompt-and-parse path — without turning the program into free-form generation?

## What stays deterministic (both engines)

- CLI I/O and argument parsing
- Shared output schema (`team`, `priority`, `needs_human`, `action`)
- Post-judgment policy: `abstain` or `needs_human` → `needs_review`, else `route`
- Persistence / queue side effects (out of scope here; would stay in code)

## What differs

| Concern | `llm` (freeform) | `llm_structured` | Vega |
|--------|------------------|------------------|------|
| How meaning is obtained | Chat + prose | Chat + JSON mode | Typed `decide()` |
| Structured output | Fence extract + repair | `json.loads` + schema retry | Native choice / score / boolean |
| Uncertainty | DIY confidence floor | Same | Calibrated probs + abstain |
| Glue LOC | See `fair_deltas` in `triage complexity` | Smaller semantic delta | Baseline |

Fair complexity: `http_client` and `offline_simulator` are reported separately so critics cannot call the HTTP client “triage logic.”

## How to run

```bash
# Install (CI uses sync without vegaml; local Vega needs --extra vega)
uv sync --group dev
uv sync --group dev --extra vega

# Complexity (no model download required for the LOC table)
uv run python -m triage complexity

# One ticket
uv run python -m triage decide --engine vega --text "Please refund my last invoice."
uv run python -m triage decide --engine llm --text "Please refund my last invoice."

# Fixture eval
uv run python -m triage eval --engine vega
uv run python -m triage eval --engine llm
uv run python -m triage eval --engine llm_structured

# Shareable artifact
uv run python -m triage compare --engines vega llm_schema

# Minimum-bar harness
uv run python -m triage shadow --engines vega llm_schema   # → disagreements.md
uv run python -m triage bench --engines vega llm_schema --qps 1
uv run python -m triage payments-eval --engine llm_schema
```

Staff pitch: [`ADOPT.md`](ADOPT.md) · labels: [`RUBRIC.md`](RUBRIC.md) · held-out: `fixtures/triage/held_out.jsonl` (≥100).

### LLM engine modes

- **`llm` freeform:** prose → extract/repair (classic glue).
- **`llm_structured`:** `response_format=json_object` — glue shrinks, does not vanish.
- **Offline (default):** no `OPENAI_API_KEY` → `SimulatedJsonLlm`.
- **Live:** set `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, `OPENAI_MODEL`.

Fixture `broken-json-marker` (`[[force_bad_json]]`) is a freeform glue probe with `eval.accuracy=false` (excluded from accuracy denominators).

## Metrics to record

Fill after you run eval (paste JSON summaries into `METRICS.md`):

1. **Complexity:** `code_lines` for `llm_engine.py` vs `vega_engine.py` (+ shared `contract.py`)
2. **Accuracy:** team / priority / needs_human on `fixtures/tickets.jsonl`
3. **Safety:** `forced_wrong_team_rate` (wrong team while `action=route`)
4. **Escalation:** `needs_review_rate`, `abstain_rate`
5. **Glue stress (LLM only):** mean `parse_attempts`, `repair_rounds`, `schema_failures`

## Claim to defend (or falsify)

> LLM engineers still write the deterministic shell. System One removes the prompt/parse/repair/confidence scaffold that usually wraps a generative model when the job is a **typed decision**.

## Results so far (2026-10-19)

See [`METRICS.md`](METRICS.md) for raw numbers. Short read:

| Signal | Finding |
|--------|---------|
| Fair semantic LOC | Schema baseline **+25** vs Vega |
| Held-out live (n=110) | **llm_schema 95.5%** team / **0%** forced-wrong vs Vega **73.6%** / **10%** |
| Latency @ 1 QPS | Vega **~640 ms** (holds 1.0 QPS) vs mini **~1160 ms** (~0.86 QPS) |
| $ (110 shadow) | Vega **$0** vs mini **~$0.007** |
| Glue | Still the System One win when accuracy SLO allows escalation |

**Interpretation:** live structured LLM wins accuracy/safety; Vega wins $0 + lower latency + less glue. Pitch as **tradeoff**, not replacement — [`ADOPT.md`](ADOPT.md), [`METRICS.md`](METRICS.md).

## Non-claims

- System One does not replace auth, cache, schema validation of *inputs*, or feature flags.
- Offline simulated LLM accuracy is not evidence against (or for) frontier models.
- Vega is not “more deterministic than if/else”; the **system** stays typed and policy-bounded.
- These fixture scores are not a published benchmark; n=18 is a research sandbox.
