"""Cost / latency table at a target QPS (sequential pacing)."""

from __future__ import annotations

import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from triage.contract import EngineName, Ticket
from triage.engines import get_engine
from triage.eval import load_fixtures
from triage.pricing import (
    GPT4O_MINI_INPUT_PER_MTOK,
    GPT4O_MINI_OUTPUT_PER_MTOK,
    estimate_chat_usd,
)

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BENCH_MD = REPO / "research" / "bench.md"
DEFAULT_FIXTURES = REPO / "fixtures" / "triage" / "held_out.jsonl"


@dataclass
class BenchRow:
    engine: str
    n: int
    target_qps: float
    achieved_qps: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    estimated_usd_total: float
    estimated_usd_per_decision: float
    prompt_tokens: int
    completion_tokens: int
    notes: str


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def run_bench(
    *,
    engines: Sequence[EngineName],
    fixtures_path: Path = DEFAULT_FIXTURES,
    limit: int = 30,
    target_qps: float = 1.0,
) -> list[BenchRow]:
    rows_fix = load_fixtures(fixtures_path)[:limit]
    interval = 1.0 / target_qps if target_qps > 0 else 0.0
    out: list[BenchRow] = []

    for name in engines:
        engine = get_engine(name)
        latencies: list[float] = []
        prompt_tokens = completion_tokens = 0
        usd = 0.0
        t_wall0 = time.perf_counter()
        for i, row in enumerate(rows_fix):
            slot = t_wall0 + i * interval
            now = time.perf_counter()
            if slot > now:
                time.sleep(slot - now)
            ticket = Ticket(body=row["body"], subject=row.get("subject", ""))
            t0 = time.perf_counter()
            decision = engine.triage(ticket)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            orch = decision.orchestration or {}
            # Prefer provider timer when present
            latencies.append(float(orch.get("latency_ms") or elapsed_ms))
            pt = int(orch.get("prompt_tokens") or 0)
            ct = int(orch.get("completion_tokens") or 0)
            prompt_tokens += pt
            completion_tokens += ct
            usd += estimate_chat_usd(
                prompt_tokens=pt, completion_tokens=ct, engine=name
            )
        wall = time.perf_counter() - t_wall0
        n = len(rows_fix) or 1
        sorted_l = sorted(latencies)
        note = (
            f"Paced at target_qps={target_qps}. "
            f"LLM $ assumes ${GPT4O_MINI_INPUT_PER_MTOK}/M input + "
            f"${GPT4O_MINI_OUTPUT_PER_MTOK}/M output (gpt-4o-mini list). "
            "Vega API $ = 0 (local)."
        )
        if name != "vega" and prompt_tokens == 0:
            note += " Token counters empty — $ may be 0 if client did not report usage."
        out.append(
            BenchRow(
                engine=name,
                n=n,
                target_qps=target_qps,
                achieved_qps=round(n / wall, 3) if wall else 0.0,
                mean_latency_ms=round(statistics.fmean(latencies), 1),
                p50_latency_ms=round(_percentile(sorted_l, 0.50), 1),
                p95_latency_ms=round(_percentile(sorted_l, 0.95), 1),
                estimated_usd_total=round(usd, 6),
                estimated_usd_per_decision=round(usd / n, 6),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                notes=note,
            )
        )
    return out


def render_bench_markdown(rows: list[BenchRow]) -> str:
    lines = [
        "# Cost / latency bench",
        "",
        "Fixed-QPS paced loop over held-out triage fixtures.",
        "",
        "| Engine | n | target QPS | achieved QPS | mean ms | p50 ms | p95 ms | $/dec | $ total |",
        "|--------|---|------------|--------------|---------|--------|--------|-------|---------|",
    ]
    for r in rows:
        lines.append(
            f"| {r.engine} | {r.n} | {r.target_qps} | {r.achieved_qps} | "
            f"{r.mean_latency_ms} | {r.p50_latency_ms} | {r.p95_latency_ms} | "
            f"{r.estimated_usd_per_decision} | {r.estimated_usd_total} |"
        )
    if rows:
        lines.extend(["", f"_Notes:_ {rows[0].notes}", ""])
    return "\n".join(lines)


def write_bench(
    rows: list[BenchRow], path: Path = DEFAULT_BENCH_MD
) -> Path:
    path.write_text(render_bench_markdown(rows))
    return path


def rows_to_json(rows: list[BenchRow]) -> list[dict[str, Any]]:
    return [asdict(r) for r in rows]
