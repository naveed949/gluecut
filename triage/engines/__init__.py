from __future__ import annotations

from triage.contract import EngineName, Ticket, TriageDecision
from triage.engines.llm_engine import LlmTriageEngine
from triage.engines.llm_schema_engine import LlmSchemaTriageEngine
from triage.engines.llm_structured_engine import LlmStructuredTriageEngine
from triage.engines.vega_engine import VegaTriageEngine


def get_engine(name: EngineName):
    if name == "vega":
        return VegaTriageEngine()
    if name == "llm":
        return LlmTriageEngine()
    if name == "llm_structured":
        return LlmStructuredTriageEngine()
    if name == "llm_schema":
        return LlmSchemaTriageEngine()
    raise ValueError(f"unknown engine: {name}")


__all__ = [
    "get_engine",
    "LlmTriageEngine",
    "LlmSchemaTriageEngine",
    "LlmStructuredTriageEngine",
    "VegaTriageEngine",
    "Ticket",
    "TriageDecision",
]
