# Cost / latency bench

Fixed-QPS paced loop over held-out triage fixtures.

> **2026-10-22 live:** `llm_schema` = `gpt-4o-mini` (mean ~1162 ms). Vega local ~642 ms @ 1 QPS.

| Engine | n | target QPS | achieved QPS | mean ms | p50 ms | p95 ms | $/dec | $ total |
|--------|---|------------|--------------|---------|--------|--------|-------|---------|
| vega | 30 | 1.0 | 1.006 | 641.5 | 598.5 | 810.7 | 0.0 | 0.0 |
| llm_schema | 30 | 1.0 | 0.861 | 1162.0 | 1111.8 | 1346.7 | 6.8e-05 | 0.002051 |

_Notes:_ Paced at target_qps=1.0. LLM $ assumes $0.15/M input + $0.6/M output (gpt-4o-mini list). Vega API $ = 0 (local).
