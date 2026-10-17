"""Shared decision contract for both engines.

Deterministic shell concerns (CLI I/O, schema, routing on typed answers)
live here. Semantic judgment is delegated to an engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

TEAMS = ("billing", "technical", "sales")
Team = Literal["billing", "technical", "sales"]
Action = Literal["route", "needs_review"]
EngineName = Literal["vega", "llm"]

PRIORITY_LEVELS = (0, 1, 2, 3)

VEGA_QUESTIONS: dict[str, dict[str, Any]] = {
    "team": {
        "type": "choice",
        "instructions": "Which team should handle this support message?",
        "criteria": {
            "billing": "payments, invoices, refunds, charges, receipts",
            "technical": "bugs, crashes, errors, product faults, outages",
            "sales": "new business, pricing, demos, upgrades, plans",
        },
    },
    "priority": {
        "type": "score",
        "instructions": "How urgent is this for the support org?",
        "criteria": {
            "0": "can wait several days; informational",
            "1": "normal queue; no active harm",
            "2": "same-day; user blocked or payment issue",
            "3": "immediate; legal, fraud, security, or widespread outage",
        },
    },
    "needs_human": {
        "type": "boolean",
        "instructions": "Should a human review before auto-routing?",
        "criteria": {
            "true": (
                "ambiguous, multi-intent, legal/fraud/GDPR, angry escalation, "
                "or otherwise unsafe to auto-route"
            ),
            "false": "clear single-team request safe to auto-route",
        },
    },
}

LLM_SYSTEM_PROMPT = """You are a support triage classifier for a SaaS product.
Return ONLY a single JSON object (no markdown, no prose) with this exact shape:
{
  "team": "billing" | "technical" | "sales",
  "priority": 0 | 1 | 2 | 3,
  "needs_human": true | false,
  "confidence": 0.0-1.0
}

Rules:
- team=billing: payments, invoices, refunds, charges
- team=technical: bugs, crashes, errors, product faults
- team=sales: new business, pricing, demos, upgrades
- priority 0=can wait days, 1=normal, 2=same day, 3=immediate (legal/fraud/outage)
- needs_human=true when ambiguous, multi-intent, legal/fraud, or low confidence
- If unsure, set needs_human=true and lower confidence
"""

LLM_REPAIR_PROMPT = (
    "Your previous reply was not valid JSON matching the schema. "
    "Reply again with ONLY the JSON object, no markdown fences."
)


@dataclass
class Ticket:
    body: str
    subject: str = ""
    source: str = "cli"

    def as_state(self) -> dict[str, str]:
        state = {"body": self.body, "source": self.source}
        if self.subject:
            state["subject"] = self.subject
        return state


@dataclass
class TriageDecision:
    team: str | None
    priority: int | None
    needs_human: bool
    abstain: bool
    action: Action
    engine: str
    confidence: float | None = None
    probs: dict[str, Any] = field(default_factory=dict)
    orchestration: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def decide_action(*, abstain: bool, needs_human: bool) -> Action:
    """Deterministic post-judgment policy — same for every engine."""
    if abstain or needs_human:
        return "needs_review"
    return "route"


def validate_llm_payload(data: Any) -> dict[str, Any]:
    """Strict schema check used by the LLM glue path."""
    if not isinstance(data, dict):
        raise ValueError("payload must be a JSON object")
    team = data.get("team")
    if team not in TEAMS:
        raise ValueError(f"team must be one of {TEAMS}, got {team!r}")
    priority = data.get("priority")
    if priority not in PRIORITY_LEVELS:
        raise ValueError(f"priority must be one of {PRIORITY_LEVELS}, got {priority!r}")
    needs_human = data.get("needs_human")
    if not isinstance(needs_human, bool):
        raise ValueError("needs_human must be a boolean")
    confidence = data.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be a number in [0, 1]")
    return {
        "team": team,
        "priority": int(priority),
        "needs_human": needs_human,
        "confidence": float(confidence),
    }
