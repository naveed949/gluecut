from __future__ import annotations

from triage.contract import EngineName, Ticket, TriageDecision
from triage.engines.llm_engine import LlmTriageEngine
from triage.engines.vega_engine import VegaTriageEngine


def get_engine(name: EngineName):
    if name == "vega":
        return VegaTriageEngine()
    if name == "llm":
        return LlmTriageEngine()
    raise ValueError(f"unknown engine: {name}")


__all__ = ["get_engine", "LlmTriageEngine", "VegaTriageEngine", "Ticket", "TriageDecision"]
