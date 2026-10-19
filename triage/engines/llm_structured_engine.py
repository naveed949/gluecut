"""Structured LLM path: JSON mode / response_format — less glue, not zero.

Still needs: prompt, API call, json.loads, schema validate, confidence floor.
No fence scraping or prose-repair loop in the happy path.
"""

from __future__ import annotations

import json
import time
from typing import Any

from triage.contract import (
    LLM_SYSTEM_PROMPT,
    Ticket,
    TriageDecision,
    decide_action,
    validate_llm_payload,
)
from triage.engines.llm_client import ChatClient, build_client

CONFIDENCE_FLOOR = 0.55
MAX_SCHEMA_RETRIES = 1


class LlmStructuredTriageEngine:
    name = "llm_structured"

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
        schema_failures = 0
        last_error: str | None = None
        validated: dict[str, Any] | None = None
        raw_replies: list[str] = []

        for attempt in range(MAX_SCHEMA_RETRIES + 1):
            reply = self.client.complete(messages, json_object=True)
            raw_replies.append(reply)
            parse_attempts += 1
            try:
                parsed = json.loads(reply)
                validated = validate_llm_payload(parsed)
                break
            except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
                last_error = str(exc)
                schema_failures += 1
                if attempt >= MAX_SCHEMA_RETRIES:
                    break
                messages.append({"role": "assistant", "content": reply})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Schema invalid. Return a JSON object with keys "
                            "team, priority, needs_human, confidence only."
                        ),
                    }
                )

        latency_ms = round(1000 * (time.time() - t0), 1)
        orch = {
            "prompt_chars": prompt_chars,
            "parse_attempts": parse_attempts,
            "repair_rounds": max(0, parse_attempts - 1),
            "schema_failures": schema_failures,
            "latency_ms": latency_ms,
            "client": self.client_label,
            "confidence_floor": CONFIDENCE_FLOOR,
            "last_error": last_error,
            "mode": "json_object",
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
