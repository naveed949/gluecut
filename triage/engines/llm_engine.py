"""Freeform LLM path: prompt → prose → extract JSON → validate → repair → decide."""

from __future__ import annotations

import json
import time
from typing import Any

from triage.contract import (
    LLM_REPAIR_PROMPT,
    LLM_SYSTEM_PROMPT,
    Ticket,
    TriageDecision,
    decide_action,
    validate_llm_payload,
)
from triage.engines.llm_client import ChatClient, build_client
from triage.engines.llm_parse import extract_json_object

MAX_REPAIR_ROUNDS = 2
CONFIDENCE_FLOOR = 0.55


class LlmTriageEngine:
    name = "llm"

    def __init__(self, client: ChatClient | None = None, client_label: str | None = None):
        if client is None:
            client, client_label = build_client()
        self.client = client
        self.client_label = client_label or "custom"

    def triage(self, ticket: Ticket) -> TriageDecision:
        t0 = time.time()
        user_payload = (
            f"Subject: {ticket.subject or '(none)'}\n"
            f"Message:\n{ticket.body}"
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ]
        prompt_chars = sum(len(m["content"]) for m in messages)
        parse_attempts = 0
        repair_rounds = 0
        schema_failures = 0
        last_error: str | None = None
        validated: dict[str, Any] | None = None
        raw_replies: list[str] = []

        for round_i in range(MAX_REPAIR_ROUNDS + 1):
            reply = self.client.complete(messages, json_object=False)
            raw_replies.append(reply)
            parse_attempts += 1
            try:
                parsed = extract_json_object(reply)
                validated = validate_llm_payload(parsed)
                break
            except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
                last_error = str(exc)
                schema_failures += 1
                if round_i >= MAX_REPAIR_ROUNDS:
                    break
                repair_rounds += 1
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": LLM_REPAIR_PROMPT})

        latency_ms = round(1000 * (time.time() - t0), 1)
        orch = {
            "prompt_chars": prompt_chars,
            "parse_attempts": parse_attempts,
            "repair_rounds": repair_rounds,
            "schema_failures": schema_failures,
            "latency_ms": latency_ms,
            "client": self.client_label,
            "max_repair_rounds": MAX_REPAIR_ROUNDS,
            "confidence_floor": CONFIDENCE_FLOOR,
            "last_error": last_error,
            "mode": "freeform",
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
                raw={"replies": raw_replies, "error": last_error},
            )

        conf = validated["confidence"]
        abstain = conf < CONFIDENCE_FLOOR
        needs_human = validated["needs_human"] or abstain

        return TriageDecision(
            team=None if abstain else validated["team"],
            priority=None if abstain else validated["priority"],
            needs_human=needs_human,
            abstain=abstain,
            action=decide_action(abstain=abstain, needs_human=needs_human),
            engine=self.name,
            confidence=conf,
            probs={"confidence": conf},
            orchestration=orch,
            raw={"replies": raw_replies, "validated": validated},
        )
