"""Strong LLM baseline: Pydantic model → OpenAI strict JSON Schema (no fence-parse)."""

from __future__ import annotations

import time
from typing import Any

from pydantic import ValidationError

from triage.contract import (
    LLM_SYSTEM_PROMPT,
    Ticket,
    TriageDecision,
    decide_action,
)
from triage.engines.llm_client import ChatClient, build_client
from triage.schemas import TriageLLMOut, openai_json_schema

CONFIDENCE_FLOOR = 0.55


class LlmSchemaTriageEngine:
    """Production-shaped baseline: schema library + structured outputs API."""

    name = "llm_schema"

    def __init__(self, client: ChatClient | None = None, client_label: str | None = None):
        if client is None:
            client, client_label = build_client()
        self.client = client
        self.client_label = client_label or "custom"
        self._response_format = openai_json_schema(TriageLLMOut, name="triage_judgment")

    def triage(self, ticket: Ticket) -> TriageDecision:
        t0 = time.time()
        user_payload = (
            f"Subject: {ticket.subject or '(none)'}\n"
            f"Message:\n{ticket.body}"
        )
        messages = [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ]
        prompt_chars = sum(len(m["content"]) for m in messages)
        detailed = self.client.complete_detailed(
            messages, response_format=self._response_format
        )
        schema_failures = 0
        validated: TriageLLMOut | None = None
        last_error: str | None = None
        try:
            validated = TriageLLMOut.model_validate_json(detailed.text)
        except (ValidationError, ValueError) as exc:
            schema_failures = 1
            last_error = str(exc)

        latency_ms = round(1000 * (time.time() - t0), 1)
        orch: dict[str, Any] = {
            "prompt_chars": prompt_chars,
            "parse_attempts": 1,
            "repair_rounds": 0,
            "schema_failures": schema_failures,
            "latency_ms": latency_ms,
            "client": self.client_label,
            "confidence_floor": CONFIDENCE_FLOOR,
            "last_error": last_error,
            "mode": "json_schema+pydantic",
            "prompt_tokens": detailed.prompt_tokens,
            "completion_tokens": detailed.completion_tokens,
            "provider_latency_ms": detailed.latency_ms,
        }

        if validated is None:
            return TriageDecision(
                team=None,
                priority=None,
                needs_human=True,
                abstain=True,
                action="needs_review",
                engine=self.name,
                confidence=None,
                orchestration=orch,
                raw={"text": detailed.text, "error": last_error},
            )

        conf = float(validated.confidence)
        abstain = conf < CONFIDENCE_FLOOR
        needs_human = validated.needs_human or abstain
        return TriageDecision(
            team=None if abstain else validated.team,
            priority=None if abstain else int(validated.priority),
            needs_human=needs_human,
            abstain=abstain,
            action=decide_action(abstain=abstain, needs_human=needs_human),
            engine=self.name,
            confidence=conf,
            probs={"confidence": conf},
            orchestration=orch,
            raw={"validated": validated.model_dump()},
        )
