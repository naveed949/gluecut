"""HTTP / offline chat clients shared by LLM engines.

Counted as transport — not semantic triage logic — in complexity breakdowns.
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

import requests

from triage.contract import TEAMS

DEFAULT_MODEL = "gpt-4o-mini"


class ChatClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
    ) -> str: ...


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

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if json_object:
            body["response_format"] = {"type": "json_object"}
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class SimulatedJsonLlm:
    """Keyword stand-in that returns JSON text (sometimes invalid) for offline runs."""

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
    ) -> str:
        original = self._original_ticket(messages)
        if any(m["role"] == "assistant" for m in messages):
            return self._classify_json(original)

        # Freeform path only: messy first reply so extract/repair glue is exercised.
        if not json_object and "[[force_bad_json]]" in original.lower():
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
            priority = (
                3
                if legal
                else 2
                if any(w in t for w in ("urgent", "asap", "immediately"))
                else 1
            )

        return json.dumps(
            {
                "team": team,
                "priority": priority,
                "needs_human": needs_human,
                "confidence": confidence,
            }
        )


def build_client() -> tuple[ChatClient, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return SimulatedJsonLlm(), "simulated"
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    return OpenAICompatClient(api_key=api_key, base_url=base, model=model), model
