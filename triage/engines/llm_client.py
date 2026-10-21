"""HTTP / offline chat clients shared by LLM engines.

Counted as transport — not semantic triage logic — in complexity breakdowns.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from triage.contract import TEAMS

DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class CompletionResult:
    text: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] | None = None


class ChatClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> str: ...

    def complete_detailed(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> CompletionResult: ...


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
        response_format: dict[str, Any] | None = None,
    ) -> str:
        return self.complete_detailed(
            messages, json_object=json_object, response_format=response_format
        ).text

    def complete_detailed(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> CompletionResult:
        url = f"{self.base_url}/chat/completions"
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if response_format is not None:
            body["response_format"] = response_format
        elif json_object:
            body["response_format"] = {"type": "json_object"}
        t0 = time.perf_counter()
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
        usage = data.get("usage") or {}
        return CompletionResult(
            text=data["choices"][0]["message"]["content"],
            latency_ms=round(1000 * (time.perf_counter() - t0), 1),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            raw=data,
        )


class SimulatedJsonLlm:
    """Keyword stand-in that returns JSON text (sometimes invalid) for offline runs."""

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        return self.complete_detailed(
            messages, json_object=json_object, response_format=response_format
        ).text

    def complete_detailed(
        self,
        messages: list[dict[str, str]],
        *,
        json_object: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> CompletionResult:
        t0 = time.perf_counter()
        original = self._original_ticket(messages)
        schema_name = ""
        if response_format and response_format.get("type") == "json_schema":
            schema_name = (response_format.get("json_schema") or {}).get("name") or ""

        if any(m["role"] == "assistant" for m in messages):
            text = self._classify(original, schema_name=schema_name)
        elif (
            not json_object
            and not response_format
            and "[[force_bad_json]]" in original.lower()
        ):
            text = 'Sure! team=billing priority=high {"needs_human": false'
        else:
            text = self._classify(original, schema_name=schema_name)

        # Rough token stand-in for $ estimates offline
        prompt_tokens = max(1, sum(len(m["content"]) for m in messages) // 4)
        completion_tokens = max(1, len(text) // 4)
        return CompletionResult(
            text=text,
            latency_ms=round(1000 * (time.perf_counter() - t0), 1),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    @staticmethod
    def _original_ticket(messages: list[dict[str, str]]) -> str:
        for m in messages:
            if m["role"] == "user" and (
                "Message:" in m["content"] or "failure_message" in m["content"]
            ):
                return m["content"]
        for m in reversed(messages):
            if m["role"] == "user":
                return m["content"]
        return ""

    def _classify(self, user: str, *, schema_name: str) -> str:
        if schema_name == "payment_judgment" or "failure_message" in user:
            return self._classify_payment(user)
        return self._classify_triage(user)

    def _classify_triage(self, user: str) -> str:
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

    def _classify_payment(self, user: str) -> str:
        t = user.lower()
        if any(w in t for w in ("insufficient", "nsf", "not enough balance")):
            reason, retry, hint = "insufficient_funds", False, "try_another_card"
        elif any(w in t for w in ("fraud", "unusual activity")):
            reason, retry, hint = "fraud_suspected", False, "contact_bank"
        elif "expir" in t:
            reason, retry, hint = "expired_card", False, "try_another_card"
        elif any(w in t for w in ("try again", "timeout", "transient", "unavailable", "glitch")):
            reason, retry, hint = "temporary", True, "try_later"
        else:
            reason, retry, hint = "other", False, "support"
        return json.dumps(
            {
                "reason": reason,
                "auto_retry": retry,
                "user_hint": hint,
                "confidence": 0.8,
            }
        )


def build_client() -> tuple[ChatClient, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return SimulatedJsonLlm(), "simulated"
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    return OpenAICompatClient(api_key=api_key, base_url=base, model=model), model
