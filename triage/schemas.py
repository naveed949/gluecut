"""Pydantic schemas for the strong LLM baseline (JSON Schema structured outputs)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TriageLLMOut(BaseModel):
    """Strict triage judgment — used as OpenAI json_schema + local validation."""

    team: Literal["billing", "technical", "sales"]
    priority: Literal[0, 1, 2, 3]
    needs_human: bool
    confidence: float = Field(ge=0.0, le=1.0)


class PaymentLLMOut(BaseModel):
    reason: Literal[
        "insufficient_funds",
        "fraud_suspected",
        "expired_card",
        "temporary",
        "other",
    ]
    auto_retry: bool
    user_hint: Literal["try_another_card", "contact_bank", "try_later", "support"]
    confidence: float = Field(ge=0.0, le=1.0)


def openai_json_schema(model: type[BaseModel], *, name: str) -> dict:
    """Wrap a Pydantic model as OpenAI response_format json_schema."""
    schema = model.model_json_schema()
    # OpenAI structured outputs prefer additionalProperties false on objects.
    def _forbid_extras(node: dict) -> None:
        if node.get("type") == "object" or "properties" in node:
            node.setdefault("additionalProperties", False)
        for key in ("properties", "$defs", "definitions"):
            kids = node.get(key)
            if isinstance(kids, dict):
                for child in kids.values():
                    if isinstance(child, dict):
                        _forbid_extras(child)
        for key in ("anyOf", "oneOf", "allOf"):
            for child in node.get(key, []) or []:
                if isinstance(child, dict):
                    _forbid_extras(child)

    _forbid_extras(schema)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }
