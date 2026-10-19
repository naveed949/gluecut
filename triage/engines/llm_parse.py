"""Freeform LLM JSON recovery — fences, embedded objects, retries live in the engine."""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_JSON_OBJECT = re.compile(r"\{[\s\S]*\}")


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
