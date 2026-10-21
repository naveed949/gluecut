"""Shadow mode: same tickets through multiple engines; disagreements + $."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from triage.contract import EngineName, Ticket
from triage.engines import get_engine
from triage.eval import load_fixtures
from triage.pricing import estimate_chat_usd

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SHADOW_MD = REPO / "research" / "disagreements.md"
DEFAULT_FIXTURES = REPO / "fixtures" / "triage" / "held_out.jsonl"


@dataclass
class ShadowCase:
    id: str
    expected_team: str
    predictions: dict[str, Any] = field(default_factory=dict)
    forced_wrong: dict[str, bool] = field(default_factory=dict)
    disagree_team: bool = False


@dataclass
class ShadowReport:
    engines: list[str]
    n: int
    per_engine: dict[str, dict[str, Any]]
    disagreements: list[ShadowCase]
    markdown: str


def run_shadow(
    *,
    engines: Sequence[EngineName],
    fixtures_path: Path = DEFAULT_FIXTURES,
    limit: int | None = None,
) -> ShadowReport:
    fixtures = load_fixtures(fixtures_path)
    if limit is not None:
        fixtures = fixtures[:limit]
    engines = list(engines)
    loaded = {name: get_engine(name) for name in engines}

    per_engine: dict[str, dict[str, Any]] = {
        name: {
            "forced_wrong": 0,
            "abstain": 0,
            "needs_review": 0,
            "team_correct": 0,
            "usd": 0.0,
            "latency_ms_sum": 0.0,
        }
        for name in engines
    }
    disagreements: list[ShadowCase] = []

    for row in fixtures:
        if row.get("eval", {}).get("accuracy") is False:
            continue
        ticket = Ticket(body=row["body"], subject=row.get("subject", ""))
        exp = row["expected"]["team"]
        preds: dict[str, Any] = {}
        fw: dict[str, bool] = {}
        teams_seen: set[str | None] = set()

        for name in engines:
            d = loaded[name].triage(ticket)
            orch = d.orchestration or {}
            stats = per_engine[name]
            stats["latency_ms_sum"] += float(orch.get("latency_ms") or 0)
            stats["usd"] += estimate_chat_usd(
                prompt_tokens=int(orch.get("prompt_tokens") or 0),
                completion_tokens=int(orch.get("completion_tokens") or 0),
                engine=name,
            )
            if d.abstain:
                stats["abstain"] += 1
            if d.action == "needs_review":
                stats["needs_review"] += 1
            wrong = (
                d.team is not None
                and d.action == "route"
                and d.team != exp
            )
            fw[name] = wrong
            if wrong:
                stats["forced_wrong"] += 1
            if d.team == exp:
                stats["team_correct"] += 1
            preds[name] = {
                "team": d.team,
                "action": d.action,
                "abstain": d.abstain,
                "confidence": d.confidence,
            }
            teams_seen.add(d.team)

        disagree = len({p["team"] for p in preds.values()}) > 1 or any(fw.values())
        if disagree:
            disagreements.append(
                ShadowCase(
                    id=row["id"],
                    expected_team=exp,
                    predictions=preds,
                    forced_wrong=fw,
                    disagree_team=len({p["team"] for p in preds.values()}) > 1,
                )
            )

    n = len([r for r in fixtures if r.get("eval", {}).get("accuracy") is not False]) or 1
    for name, stats in per_engine.items():
        stats["forced_wrong_rate"] = stats["forced_wrong"] / n
        stats["abstain_rate"] = stats["abstain"] / n
        stats["needs_review_rate"] = stats["needs_review"] / n
        stats["team_accuracy"] = stats["team_correct"] / n
        stats["mean_latency_ms"] = round(stats["latency_ms_sum"] / n, 1)
        stats["estimated_usd_total"] = round(stats["usd"], 6)
        stats["estimated_usd_per_decision"] = round(stats["usd"] / n, 6)

    md = render_shadow_markdown(engines, n, per_engine, disagreements)
    return ShadowReport(
        engines=list(engines),
        n=n,
        per_engine=per_engine,
        disagreements=disagreements,
        markdown=md,
    )


def render_shadow_markdown(
    engines: Sequence[str],
    n: int,
    per_engine: dict[str, dict[str, Any]],
    disagreements: list[ShadowCase],
) -> str:
    lines = [
        "# Shadow mode & disagreement sheet",
        "",
        f"n_scored={n}. Engines: {', '.join(engines)}.",
        "",
        "## Summary",
        "",
        "| Engine | team acc | forced-wrong | abstain | needs_review | mean ms | $/dec | $ total |",
        "|--------|----------|--------------|---------|--------------|---------|-------|---------|",
    ]
    for name in engines:
        s = per_engine[name]
        lines.append(
            f"| {name} | {s['team_accuracy']:.3f} | {s['forced_wrong_rate']:.3f} | "
            f"{s['abstain_rate']:.3f} | {s['needs_review_rate']:.3f} | "
            f"{s['mean_latency_ms']} | {s['estimated_usd_per_decision']} | "
            f"{s['estimated_usd_total']} |"
        )
    lines.extend(
        [
            "",
            f"## Disagreements ({len(disagreements)})",
            "",
            "Cases where engines disagree on `team` or any engine forced-wrong.",
            "",
        ]
    )
    if not disagreements:
        lines.append("_None on this run._")
    else:
        lines.append("| id | expected | " + " | ".join(engines) + " | forced-wrong |")
        lines.append("|----|----------|" + "|".join(["--------"] * len(engines)) + "|---|")
        for d in disagreements[:80]:
            preds = " | ".join(
                f"{d.predictions[e]['team']}/{d.predictions[e]['action']}" for e in engines
            )
            fw = ",".join(e for e, v in d.forced_wrong.items() if v) or "—"
            lines.append(f"| {d.id} | {d.expected_team} | {preds} | {fw} |")
        if len(disagreements) > 80:
            lines.append(f"\n_… {len(disagreements) - 80} more omitted._")
    lines.append("")
    return "\n".join(lines)


def write_shadow(report: ShadowReport, path: Path = DEFAULT_SHADOW_MD) -> Path:
    path.write_text(report.markdown)
    return path
