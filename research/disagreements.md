# Shadow mode & disagreement sheet

> **2026-10-22 live:** `llm_schema` ≈1306 ms mean (API). Vega local. n=110.

n_scored=110. Engines: vega, llm_schema.

## Summary

| Engine | team acc | forced-wrong | abstain | needs_review | mean ms | $/dec | $ total |
|--------|----------|--------------|---------|--------------|---------|-------|---------|
| vega | 0.736 | 0.100 | 0.109 | 0.309 | 694.7 | 0.0 | 0.0 |
| llm_schema | 0.955 | 0.000 | 0.027 | 0.155 | 1306.0 | 6.7e-05 | 0.007319 |

## Disagreements (32)

Cases where engines disagree on `team` or any engine forced-wrong.

| id | expected | vega | llm_schema | forced-wrong |
|----|----------|--------|--------|---|
| bill-4-0 | billing | None/needs_review | billing/route | — |
| bill-4-1 | billing | None/needs_review | billing/route | — |
| bill-4-2 | billing | None/needs_review | billing/route | — |
| tech-4-0 | technical | billing/needs_review | technical/route | — |
| tech-4-1 | technical | billing/needs_review | technical/route | — |
| tech-4-2 | technical | billing/needs_review | technical/route | — |
| sales-0-0 | sales | None/needs_review | sales/route | — |
| sales-0-1 | sales | None/needs_review | sales/route | — |
| sales-1-0 | sales | None/needs_review | sales/route | — |
| sales-1-1 | sales | None/needs_review | sales/route | — |
| sales-2-0 | sales | billing/route | sales/route | vega |
| sales-2-1 | sales | billing/needs_review | sales/route | — |
| sales-3-0 | sales | technical/route | sales/route | vega |
| sales-3-1 | sales | technical/route | sales/route | vega |
| sales-4-0 | sales | None/needs_review | sales/route | — |
| sales-4-1 | sales | technical/route | sales/route | vega |
| sales-5-0 | sales | None/needs_review | sales/route | — |
| sales-5-1 | sales | None/needs_review | sales/route | — |
| sales-6-0 | sales | technical/route | sales/route | vega |
| sales-6-1 | sales | technical/route | sales/route | vega |
| sales-7-0 | sales | technical/route | sales/route | vega |
| sales-7-1 | sales | technical/route | sales/route | vega |
| sales-8-0 | sales | None/needs_review | sales/route | — |
| sales-8-1 | sales | technical/route | sales/route | vega |
| sales-9-0 | sales | technical/route | sales/route | vega |
| sales-9-1 | sales | technical/route | sales/route | vega |
| hard-multi-1 | billing | billing/route | technical/needs_review | — |
| hard-gdpr | technical | technical/route | None/needs_review | — |
| hard-ambiguous | technical | technical/needs_review | None/needs_review | — |
| hard-sarcasm | billing | technical/needs_review | billing/needs_review | — |
| hard-empty | technical | technical/route | None/needs_review | — |
| hard-lawyer | sales | None/needs_review | sales/needs_review | — |
