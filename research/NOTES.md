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

| Concern | LLM engine | Vega engine |
|--------|------------|-------------|
| How meaning is obtained | Chat completion + prose | Typed `decide()` |
| Structured output | Prompt + extract + validate + repair | Native choice / score / boolean |
| Uncertainty | DIY `confidence` floor | Calibrated probs + `abstain` / `unbound` |
| Glue LOC | See `triage complexity` | See `triage complexity` |

## How to run

```bash
# Complexity (no model download required for the LOC table)
uv run python -m triage complexity

# One ticket
uv run python -m triage decide --engine vega --text "Please refund my last invoice."
uv run python -m triage decide --engine llm --text "Please refund my last invoice."

# Fixture eval
uv run python -m triage eval --engine vega
uv run python -m triage eval --engine llm
```

### LLM engine modes

- **Offline (default):** no `OPENAI_API_KEY` → `SimulatedJsonLlm` emits JSON strings so parse/repair glue still runs. Use this to inspect orchestration metrics and glue LOC — **not** for fair accuracy vs Vega.
- **Live:** set `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, `OPENAI_MODEL` (default `gpt-4o-mini`).

Fixture `broken-json-marker` (`[[force_bad_json]]`) forces a messy first LLM reply so repair rounds show up offline.

## Metrics to record

Fill after you run eval (paste JSON summaries into `METRICS.md`):

1. **Complexity:** `code_lines` for `llm_engine.py` vs `vega_engine.py` (+ shared `contract.py`)
2. **Accuracy:** team / priority / needs_human on `fixtures/tickets.jsonl`
3. **Safety:** `forced_wrong_team_rate` (wrong team while `action=route`)
4. **Escalation:** `needs_review_rate`, `abstain_rate`
5. **Glue stress (LLM only):** mean `parse_attempts`, `repair_rounds`, `schema_failures`

## Claim to defend (or falsify)

> LLM engineers still write the deterministic shell. System One removes the prompt/parse/repair/confidence scaffold that usually wraps a generative model when the job is a **typed decision**.

## Non-claims

- System One does not replace auth, cache, schema validation of *inputs*, or feature flags.
- Offline simulated LLM accuracy is not evidence against (or for) frontier models.
- Vega is not “more deterministic than if/else”; the **system** stays typed and policy-bounded.
