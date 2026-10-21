# Adopt System One (Vega) — staff-engineer one-pager

**Audience:** LLM-heavy engineers deciding whether gluecut / System One belongs in a production judgment path.
**Companion evidence:** [`report.md`](report.md), [`RUBRIC.md`](RUBRIC.md), `triage shadow`, `triage bench`.

---

## Adopt *if*

1. **The job is a typed decision** — fixed enums/scores/booleans your code branches on (route, reason code, allow/deny), not open-ended generation.
2. **You are paying glue tax** — prompt → parse → schema repair → confidence hacks dominate the module, and JSON mode only partially helped.
3. **Wrong auto-actions are costly** — you need an explicit abstain / `needs_review` path, not a silent wrong enum.
4. **Privacy / local inference matters** — judgment over PII-ish text that should not leave the box (or you want a cheap local gate before an API LLM).
5. **You will own the rubric** — criteria live as data you can diff; you accept frozen labels and disagreement sheets as engineering artifacts.
6. **Shadow metrics look acceptable** — on *your* held-out set, forced-wrong and abstain rates beat (or match with lower $) your current LLM classifier at target latency.

## Do *not* adopt if

1. **You need free-form text** — summaries, emails, code, tool plans. System One is not a chat model.
2. **The API already gives clean enums** — map `failure_code` in a `match`; do not add a model.
3. **You require frontier accuracy on soft labels today** — on gluecut’s triage held-out set, a live LLM often wins priority / needs_human; Vega’s win is glue + local typed decide, not universal SOTA.
4. **You cannot run or host the weights** — cold start / torch / device constraints dominate and you have no ONNX/MLX/server plan.
5. **You refuse evaluation discipline** — no frozen rubric, no held-out set, no shadow/$ table → you will cargo-cult a demo.
6. **AuthZ, cache, and schema validation are what hurt** — System One does not replace those; keep them deterministic.

## Practical insertion pattern

```text
validate input → (optional) System One decide() → deterministic policy on typed answers
                                      ↘ abstain / needs_review → human or expensive LLM
```

Use **shadow mode** (`triage shadow`) before cutover: same fixtures through Vega + your strong LLM baseline; compare forced-wrong, abstain, latency, and estimated $.

## Decision cheat-sheet

| Situation | Prefer |
|-----------|--------|
| Structured vendor codes already present | Plain code |
| Messy prose → internal enum, high volume, local OK | System One |
| Messy prose → enum, need best soft-label accuracy, API OK | Strong structured LLM (+ schema lib) |
| Uncertain / high blast radius | Either, but **must** abstain or review — never silent route |

---

*This page is intentional opinion for gluecut research. Update when held-out metrics or domains change; bump the freeze note in `RUBRIC.md` if labels move.*
