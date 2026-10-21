# Metrics log

**Canonical live suite (2026-10-22):** `gpt-4o-mini` via `llm_schema` + local Vega 0.8B.  
Artifacts: [`report.md`](report.md) · [`disagreements.md`](disagreements.md) · [`bench.md`](bench.md) · [`ADOPT.md`](ADOPT.md)

## Shadow — held-out triage (n=110)

| Engine | team acc | forced-wrong | abstain | needs_review | mean ms | $/dec | $ total (110) |
|--------|----------|--------------|---------|--------------|---------|-------|---------------|
| **vega** | 0.736 | 0.100 | 0.109 | 0.309 | **695** | **$0** | **$0** |
| **llm_schema** (`gpt-4o-mini`) | **0.955** | **0.000** | 0.027 | 0.155 | 1306 | ~$6.7e-5 | ~$0.0073 |

## Bench — target 1 QPS, limit 30

| Engine | achieved QPS | mean / p50 / p95 ms | $/dec | $ total (30) |
|--------|--------------|---------------------|-------|--------------|
| vega | **1.006** | **642 / 599 / 811** | **$0** | **$0** |
| llm_schema | 0.861 | 1162 / 1112 / 1347 | ~$6.8e-5 | ~$0.0021 |

## Compare (fair LOC + accuracy)

| Metric | vega | llm_schema |
|--------|------|------------|
| Semantic LOC (fair) | **48** | 73 |
| Fair delta vs Vega | **0** | **+25** |
| Team accuracy | 72.7% | **94.5%** |
| Priority accuracy | 51.8% | **64.5%** |
| Needs-human accuracy | 78.2% | **92.7%** |
| Forced-wrong team | 9.1% | **0.0%** |

## Interpretation for LLM engineers

1. **Accuracy / safety:** live structured LLM wins clearly on this held-out set (team ~95% vs ~74%, forced-wrong 0% vs 10%).
2. **Latency @ ~1 QPS:** Vega is **~2× faster** mean (~640 ms vs ~1160 ms) and holds target QPS; API LLM drops to ~0.86 QPS.
3. **$:** Vega **$0 API**; mini is cheap per call but non-zero and scales with volume.
4. **Glue:** schema baseline still **+25 semantic LOC** vs Vega — even the strong path isn’t free of orchestration code.
5. **Honest adopt line:** use System One when local/$0/typed decide + less glue matter *and* you can live with (or escalate) the accuracy gap; keep `llm_schema` (or similar) when forced-wrong≈0 is the SLO. Shadow both before cutover — see [`ADOPT.md`](ADOPT.md).

## Payments domain

Earlier Vega payments-eval (~55% reason, high review) still stands as “pattern works, not SOTA.” Re-run `payments-eval --engine llm_schema` with the key if you want a live second-domain pair in this log.
