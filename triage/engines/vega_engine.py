"""System One path: typed decide() — almost no semantic glue."""

from __future__ import annotations

from typing import Any

from triage.contract import VEGA_QUESTIONS, Ticket, TriageDecision, decide_action

_model: Any = None


def _load_model():
    global _model
    if _model is None:
        import vegaml

        _model = vegaml.load()
    return _model


class VegaTriageEngine:
    name = "vega"

    def triage(self, ticket: Ticket) -> TriageDecision:
        model = _load_model()
        out = model.decide(ticket.as_state(), VEGA_QUESTIONS)
        answers = out["answers"]

        team_a = answers["team"]
        pri_a = answers["priority"]
        hum_a = answers["needs_human"]

        # Only team uncertainty blocks auto-routing the team field.
        # Priority/needs_human may abstain independently without wiping a sharp team choice.
        team_abstain = bool(team_a.get("abstain") or team_a.get("unbound"))
        priority_abstain = bool(pri_a.get("abstain") or pri_a.get("unbound"))
        human_abstain = bool(hum_a.get("abstain") or hum_a.get("unbound"))

        needs_human = bool(hum_a.get("boolean", 0.0) >= 0.5) or human_abstain
        conf = float(team_a.get("confidence") or 0.0)

        return TriageDecision(
            team=None if team_abstain else team_a.get("choice"),
            priority=int(pri_a.get("score", 1)),
            needs_human=needs_human,
            abstain=team_abstain,
            action=decide_action(abstain=team_abstain, needs_human=needs_human),
            engine=self.name,
            confidence=conf,
            probs={
                "team": team_a.get("probs"),
                "priority": pri_a.get("probs"),
                "needs_human": hum_a.get("probs"),
            },
            orchestration={
                "prompt_chars": 0,
                "parse_attempts": 0,
                "repair_rounds": 0,
                "schema_failures": 0,
                "latency_ms": out.get("latency_ms"),
                "n_tokens": out.get("n_tokens"),
                "field_abstain": {
                    "team": team_abstain,
                    "priority": priority_abstain,
                    "needs_human": human_abstain,
                },
            },
            raw=out,
        )
