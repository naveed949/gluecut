"""Second domain: payment failure prose → internal reason / retry / user hint."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from triage.contract import Action, decide_action
from triage.engines.llm_client import ChatClient, build_client
from triage.engines.vega_engine import _load_model
from triage.schemas import PaymentLLMOut, openai_json_schema

DEFAULT_PAYMENT_FIXTURES = (
    Path(__file__).resolve().parent.parent / "fixtures" / "payments" / "held_out.jsonl"
)

REASONS = (
    "insufficient_funds",
    "fraud_suspected",
    "expired_card",
    "temporary",
    "other",
)
HINTS = ("try_another_card", "contact_bank", "try_later", "support")

VEGA_PAYMENT_QUESTIONS: dict[str, dict[str, Any]] = {
    "reason": {
        "type": "choice",
        "instructions": "Internal payment failure reason for our ledger.",
        "criteria": {
            "insufficient_funds": "not enough balance / NSF",
            "fraud_suspected": "bank fraud or unusual activity",
            "expired_card": "card expired",
            "temporary": "retryable network/issuer glitch",
            "other": "none of the above / unclear",
        },
    },
    "auto_retry": {
        "type": "boolean",
        "instructions": "Is an automatic retry appropriate?",
        "criteria": {
            "true": "temporary issuer/network issue",
            "false": "funds, fraud, expired, or user must change method",
        },
    },
    "user_hint": {
        "type": "choice",
        "instructions": "Which canned user message should we show?",
        "criteria": {
            "try_another_card": "use a different payment method",
            "contact_bank": "ask bank to allow the charge",
            "try_later": "retry later",
            "support": "contact support",
        },
    },
}

PAYMENT_SYSTEM_PROMPT = """You classify payment-provider failure prose into internal enums.
Follow the JSON schema exactly.
Rules:
- insufficient_funds: NSF / not enough balance
- fraud_suspected: unusual activity / fraud / security block
- expired_card: expiration
- temporary: try again / timeout / issuer unavailable / transient
- other: unclear
- auto_retry true ONLY for temporary
- user_hint: try_another_card | contact_bank | try_later | support
"""


@dataclass
class PaymentEvent:
    failure_message: str
    provider: str = "unknown"
    failure_code: str | None = None

    def as_state(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
        }


@dataclass
class PaymentDecision:
    reason: str | None
    auto_retry: bool | None
    user_hint: str | None
    abstain: bool
    action: Action
    engine: str
    confidence: float | None = None
    orchestration: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


class VegaPaymentEngine:
    name = "vega"

    def decide(self, event: PaymentEvent) -> PaymentDecision:
        model = _load_model()
        out = model.decide(event.as_state(), VEGA_PAYMENT_QUESTIONS)
        answers = out["answers"]
        reason_a = answers["reason"]
        retry_a = answers["auto_retry"]
        hint_a = answers["user_hint"]
        reason_abstain = bool(reason_a.get("abstain") or reason_a.get("unbound"))
        retry_human = bool(retry_a.get("boolean", 0.0) >= 0.5)
        # Escalate if reason uncertain OR retry judgment abstains
        needs_review = reason_abstain or bool(retry_a.get("abstain")) or bool(
            hint_a.get("abstain")
        )
        return PaymentDecision(
            reason=None if reason_abstain else reason_a.get("choice"),
            auto_retry=None if reason_abstain else retry_human,
            user_hint=None if reason_abstain else hint_a.get("choice"),
            abstain=reason_abstain,
            action=decide_action(abstain=reason_abstain, needs_human=needs_review),
            engine=self.name,
            confidence=float(reason_a.get("confidence") or 0.0),
            orchestration={
                "latency_ms": out.get("latency_ms"),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "mode": "vega",
            },
            raw=out,
        )


class LlmSchemaPaymentEngine:
    name = "llm_schema"

    def __init__(self, client: ChatClient | None = None, client_label: str | None = None):
        if client is None:
            client, client_label = build_client()
        self.client = client
        self.client_label = client_label or "custom"
        self._fmt = openai_json_schema(PaymentLLMOut, name="payment_judgment")

    def decide(self, event: PaymentEvent) -> PaymentDecision:
        t0 = time.time()
        messages = [
            {"role": "system", "content": PAYMENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(event.as_state()),
            },
        ]
        detailed = self.client.complete_detailed(messages, response_format=self._fmt)
        try:
            validated = PaymentLLMOut.model_validate_json(detailed.text)
        except (ValidationError, ValueError) as exc:
            return PaymentDecision(
                reason=None,
                auto_retry=None,
                user_hint=None,
                abstain=True,
                action="needs_review",
                engine=self.name,
                confidence=None,
                orchestration={
                    "latency_ms": round(1000 * (time.time() - t0), 1),
                    "schema_failures": 1,
                    "last_error": str(exc),
                    "prompt_tokens": detailed.prompt_tokens,
                    "completion_tokens": detailed.completion_tokens,
                    "client": self.client_label,
                    "mode": "json_schema+pydantic",
                },
                raw={"text": detailed.text},
            )
        conf = float(validated.confidence)
        abstain = conf < 0.55
        return PaymentDecision(
            reason=None if abstain else validated.reason,
            auto_retry=None if abstain else validated.auto_retry,
            user_hint=None if abstain else validated.user_hint,
            abstain=abstain,
            action=decide_action(abstain=abstain, needs_human=abstain),
            engine=self.name,
            confidence=conf,
            orchestration={
                "latency_ms": round(1000 * (time.time() - t0), 1),
                "prompt_tokens": detailed.prompt_tokens,
                "completion_tokens": detailed.completion_tokens,
                "client": self.client_label,
                "mode": "json_schema+pydantic",
            },
            raw={"validated": validated.model_dump()},
        )


def get_payment_engine(name: Literal["vega", "llm_schema"]):
    if name == "vega":
        return VegaPaymentEngine()
    if name == "llm_schema":
        return LlmSchemaPaymentEngine()
    raise ValueError(name)


def load_payment_fixtures(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or DEFAULT_PAYMENT_FIXTURES
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def eval_payments(engine_name: Literal["vega", "llm_schema"], path: Path | None = None) -> dict:
    engine = get_payment_engine(engine_name)
    fixtures = load_payment_fixtures(path)
    ok_reason = ok_retry = ok_hint = forced_wrong = review = abstain_n = 0
    latencies: list[float] = []
    cost_usd = 0.0
    from triage.pricing import estimate_chat_usd

    for row in fixtures:
        event = PaymentEvent(
            failure_message=row["failure_message"],
            provider=row.get("provider", "unknown"),
            failure_code=row.get("failure_code"),
        )
        d = engine.decide(event)
        exp = row["expected"]
        latencies.append(float((d.orchestration or {}).get("latency_ms") or 0))
        cost_usd += estimate_chat_usd(
            prompt_tokens=int((d.orchestration or {}).get("prompt_tokens") or 0),
            completion_tokens=int((d.orchestration or {}).get("completion_tokens") or 0),
            engine=engine_name,
        )
        if d.reason == exp["reason"]:
            ok_reason += 1
        if d.auto_retry == exp["auto_retry"]:
            ok_retry += 1
        if d.user_hint == exp["user_hint"]:
            ok_hint += 1
        if d.reason is not None and d.action == "route" and d.reason != exp["reason"]:
            forced_wrong += 1
        if d.action == "needs_review":
            review += 1
        if d.abstain:
            abstain_n += 1
    n = len(fixtures) or 1
    return {
        "engine": engine_name,
        "domain": "payments",
        "n": len(fixtures),
        "reason_accuracy": ok_reason / n,
        "auto_retry_accuracy": ok_retry / n,
        "user_hint_accuracy": ok_hint / n,
        "forced_wrong_reason_rate": forced_wrong / n,
        "needs_review_rate": review / n,
        "abstain_rate": abstain_n / n,
        "mean_latency_ms": sum(latencies) / n,
        "estimated_usd_total": round(cost_usd, 6),
    }
