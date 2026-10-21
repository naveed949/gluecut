# gluecut

Cut LLM prompt/parse/repair glue. Keep a deterministic shell. Use System One (Vega) for typed triage decisions.

Compare **LLM freeform glue**, **LLM JSON-mode**, and **Vega** on the same support-ticket triage job.

Audience: engineers already using LLMs for classification — see [`research/NOTES.md`](research/NOTES.md).

## Setup

```bash
uv sync
```

First Vega run downloads weights (`vegaml.load()`).

## Commands

```bash
# LOC + fair breakdown (excludes HTTP client from semantic delta)
uv run python -m triage complexity

# One ticket
uv run python -m triage decide --engine vega --text "Please refund my last invoice."
uv run python -m triage decide --engine llm --text "Please refund my last invoice."
uv run python -m triage decide --engine llm_structured --text "Please refund my last invoice."

# Labeled fixtures (glue probe excluded from accuracy denominators)
uv run python -m triage eval --engine vega
uv run python -m triage eval --engine llm --verbose
uv run python -m triage eval --engine llm_structured

# One-shot shareable report → research/report.md (+ report.html)
uv run python -m triage compare
```

Optional live LLM (otherwise offline JSON simulator):

```bash
export OPENAI_API_KEY=...
# optional: OPENAI_BASE_URL OPENAI_MODEL
uv run python -m triage compare
```

Share [`research/report.md`](research/report.md) (or open `research/report.html`).

## Layout

| Path | Role |
|------|------|
| `triage/contract.py` | Shared schema + deterministic `route` / `needs_review` policy |
| `triage/engines/vega_engine.py` | System One `decide()` |
| `triage/engines/llm_engine.py` | Freeform: extract JSON → validate → repair |
| `triage/engines/llm_structured_engine.py` | JSON mode: `json.loads` + validate (less glue) |
| `triage/engines/llm_client.py` | HTTP / offline transport (excluded from fair semantic delta) |
| `triage/engines/llm_parse.py` | Fence / embedded-JSON recovery |
| `fixtures/tickets.jsonl` | Labeled cases (+ notes) |
| `research/` | Notes, metrics, **report.md / report.html** |
| `vega.py` | Minimal vegaml smoke script |

## Tests

```bash
uv run pytest
```
