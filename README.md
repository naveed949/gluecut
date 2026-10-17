# gluecut

Cut LLM prompt/parse/repair glue. Keep a deterministic shell. Use System One (Vega) for typed triage decisions.

Compare **LLM prompt/parse/repair glue** with **Vega (System One) typed decisions** on the same support-ticket triage job.

Audience: engineers already using LLMs for classification — see [`research/NOTES.md`](research/NOTES.md).

## Setup

```bash
uv sync
```

First Vega run downloads weights (`vegaml.load()`).

## Commands

```bash
# How much glue code each engine carries
uv run python -m triage complexity

# One ticket
uv run python -m triage decide --engine vega --text "Please refund my last invoice."
uv run python -m triage decide --engine llm --text "Please refund my last invoice."

# Labeled fixtures
uv run python -m triage eval --engine vega
uv run python -m triage eval --engine llm --verbose
```

Optional live LLM (otherwise offline JSON simulator):

```bash
export OPENAI_API_KEY=...
# optional: OPENAI_BASE_URL OPENAI_MODEL
uv run python -m triage eval --engine llm
```

## Layout

| Path | Role |
|------|------|
| `triage/contract.py` | Shared schema + deterministic `route` / `needs_review` policy |
| `triage/engines/vega_engine.py` | System One `decide()` |
| `triage/engines/llm_engine.py` | Prompt → extract JSON → validate → repair |
| `fixtures/tickets.jsonl` | Labeled cases |
| `research/` | Notes + metrics log |
| `vega.py` | Minimal vegaml smoke script |

## Tests

```bash
uv run pytest
```
