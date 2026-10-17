"""LLM path: the glue an LLM-using engineer typically writes.

Prompt → free text → extract JSON → validate schema → repair retry →
threshold confidence → typed decision.

Offline (no API key): a keyword stand-in emits JSON *strings* so the same
parse/repair pipeline still runs; accuracy is not comparable to a real LLM.
Set OPENAI_API_KEY (and optionally OPENAI_BASE_URL / OPENAI_MODEL) for a live model.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Protocol

import requests

from triage.contract import (
    LLM_REPAIR_PROMPT,
    LLM_SYSTEM_PROMPT,
    TEAMS,
    Ticket,
    TriageDecision,
    decide_action,
    validate_llm_payload,
)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_JSON_OBJECT = re.compile(r"\{[\s\S]*\}")

DEFAULT_MODEL = "gpt-4o-mini"
MAX_REPAIR_ROUNDS = 2
CONFIDENCE_FLOOR = 0.55


class ChatClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class OpenAICompatClient:
    """Minimal OpenAI-compatible chat completions client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.base_url}/chat/completions"
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class SimulatedJsonLlm:
    """Keyword stand-in that returns JSON text (sometimes invalid) for offline runs."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        original = self._original_ticket(messages)
        # Repair rounds: previous assistant message failed — return clean JSON.
        if any(m["role"] == "assistant" for m in messages):
            return self._classify_json(original)

        # Deliberately messy first reply on this marker so repair glue is exercised.
        if "[[force_bad_json]]" in original.lower():
            return 'Sure! team=billing priority=high {"needs_human": false'

        return self._classify_json(original)

    @staticmethod
    def _original_ticket(messages: list[dict[str, str]]) -> str:
        for m in messages:
            if m["role"] == "user" and "Message:" in m["content"]:
                return m["content"]
        for m in reversed(messages):
            if m["role"] == "user":
                return m["content"]
        return ""

    def _classify_json(self, user: str) -> str:
        body = user
        if "Message:" in user:
            body = user.split("Message:", 1)[1]
        t = body.lower().replace("[[force_bad_json]]", " ")

        scores = {team: 0 for team in TEAMS}
        for w in ("refund", "invoice", "charge", "payment", "billing", "receipt"):
            if w in t:
                scores["billing"] += 2
        for w in ("crash", "bug", "error", "broken", "stack", "outage", "500"):
            if w in t:
                scores["technical"] += 2
        for w in ("pricing", "demo", "upgrade", "plan", "sales", "enterprise"):
            if w in t:
                scores["sales"] += 2

        team = max(scores, key=scores.get)
        if max(scores.values()) == 0:
            team = "technical"
            needs_human = True
            confidence = 0.35
            priority = 1
        else:
            multi = sum(1 for v in scores.values() if v > 0) >= 2
            legal = any(w in t for w in ("lawyer", "gdpr", "fraud", "lawsuit"))
            needs_human = multi or legal or "not a refund" in t
            confidence = 0.4 if needs_human else 0.85
            priority = 3 if legal else 2 if any(w in t for w in ("urgent", "asap", "immediately")) else 1

        return json.dumps(
            {
                "team": team,
                "priority": priority,
                "needs_human": needs_human,
                "confidence": confidence,
            }
        )


def extract_json_object(text: str) -> Any:
    """Typical LLM-engineer JSON recovery: fences, then first object, then raw parse."""
    text = text.strip()
    fence = _JSON_FENCE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT.search(text)
        if not match:
            raise
        return json.loads(match.group(0))


def build_client() -> tuple[ChatClient, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return SimulatedJsonLlm(), "simulated"
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    return OpenAICompatClient(api_key=api_key, base_url=base, model=model), model


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
            reply = self.client.complete(messages)
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
