"""Evaluate an engine against labeled fixtures."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from triage.contract import EngineName, Ticket
from triage.engines import get_engine

DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "tickets.jsonl"


@dataclass
class CaseResult:
    id: str
    scored: bool
    ok_team: bool | None
    ok_priority: bool | None
    ok_needs_human: bool | None
    forced_wrong_team: bool
    action: str
    abstain: bool
    predicted_team: str | None
    expected_team: str | None
    orchestration: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalReport:
    engine: str
    n: int
    n_scored: int
    n_glue_only: int
    team_accuracy: float
    priority_accuracy: float
    needs_human_accuracy: float
    forced_wrong_team_rate: float
    needs_review_rate: float
    abstain_rate: float
    mean_parse_attempts: float
    mean_repair_rounds: float
    mean_schema_failures: float
    cases: list[CaseResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def load_fixtures(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or DEFAULT_FIXTURES
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _scored(row: dict[str, Any]) -> bool:
    """Glue-only probes set eval.accuracy=false and are excluded from accuracy rates."""
    return row.get("eval", {}).get("accuracy", True) is not False


def run_eval(engine_name: EngineName, fixtures_path: Path | None = None) -> EvalReport:
    engine = get_engine(engine_name)
    fixtures = load_fixtures(fixtures_path)
    cases: list[CaseResult] = []

    team_ok = pri_ok = hum_ok = 0
    forced_wrong = review = abstain_n = 0
    parse_attempts = repair_rounds = schema_failures = 0
    n_scored = 0
    n_glue = 0

    for row in fixtures:
        ticket = Ticket(body=row["body"], subject=row.get("subject", ""), source="fixture")
        decision = engine.triage(ticket)
        scored = _scored(row)
        exp = row.get("expected") or {}

        if scored:
            n_scored += 1
            ok_t = decision.team == exp["team"] if decision.team is not None else False
            if decision.team is None and decision.action == "needs_review":
                ok_t = False
            ok_p = (
                decision.priority == exp["priority"] if decision.priority is not None else False
            )
            ok_h = decision.needs_human == exp["needs_human"]
            fw = (
                decision.team is not None
                and decision.action == "route"
                and decision.team != exp["team"]
            )
            if ok_t:
                team_ok += 1
            if ok_p:
                pri_ok += 1
            if ok_h:
                hum_ok += 1
            if fw:
                forced_wrong += 1
        else:
            n_glue += 1
            ok_t = ok_p = ok_h = None
            fw = False

        if decision.action == "needs_review":
            review += 1
        if decision.abstain:
            abstain_n += 1

        orch = decision.orchestration or {}
        parse_attempts += int(orch.get("parse_attempts") or 0)
        repair_rounds += int(orch.get("repair_rounds") or 0)
        schema_failures += int(orch.get("schema_failures") or 0)

        cases.append(
            CaseResult(
                id=row["id"],
                scored=scored,
                ok_team=ok_t,
                ok_priority=ok_p,
                ok_needs_human=ok_h,
                forced_wrong_team=fw,
                action=decision.action,
                abstain=decision.abstain,
                predicted_team=decision.team,
                expected_team=exp.get("team"),
                orchestration={
                    "parse_attempts": orch.get("parse_attempts"),
                    "repair_rounds": orch.get("repair_rounds"),
                    "schema_failures": orch.get("schema_failures"),
                    "client": orch.get("client"),
                    "mode": orch.get("mode"),
                },
            )
        )

    n_all = len(fixtures) or 1
    denom = n_scored or 1
    return EvalReport(
        engine=engine_name,
        n=len(fixtures),
        n_scored=n_scored,
        n_glue_only=n_glue,
        team_accuracy=team_ok / denom,
        priority_accuracy=pri_ok / denom,
        needs_human_accuracy=hum_ok / denom,
        forced_wrong_team_rate=forced_wrong / denom,
        needs_review_rate=review / n_all,
        abstain_rate=abstain_n / n_all,
        mean_parse_attempts=parse_attempts / n_all,
        mean_repair_rounds=repair_rounds / n_all,
        mean_schema_failures=schema_failures / n_all,
        cases=cases,
    )
