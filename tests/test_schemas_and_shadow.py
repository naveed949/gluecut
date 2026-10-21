from pathlib import Path

from triage.contract import Ticket
from triage.engines.llm_client import SimulatedJsonLlm
from triage.engines.llm_schema_engine import LlmSchemaTriageEngine
from triage.pricing import estimate_chat_usd
from triage.schemas import TriageLLMOut, openai_json_schema
from triage.shadow import render_shadow_markdown


def test_openai_json_schema_wraps_pydantic():
    fmt = openai_json_schema(TriageLLMOut, name="triage_judgment")
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "triage_judgment"
    assert "team" in fmt["json_schema"]["schema"]["properties"]


def test_llm_schema_engine_simulated():
    engine = LlmSchemaTriageEngine(client=SimulatedJsonLlm(), client_label="simulated")
    d = engine.triage(Ticket(body="Please refund my last invoice."))
    assert d.team == "billing"
    assert d.orchestration["mode"] == "json_schema+pydantic"


def test_pricing_vega_zero():
    assert estimate_chat_usd(prompt_tokens=100, completion_tokens=50, engine="vega") == 0.0
    assert estimate_chat_usd(prompt_tokens=1_000_000, completion_tokens=0, engine="llm") == 0.15


def test_held_out_fixture_count():
    path = Path("fixtures/triage/held_out.jsonl")
    n = sum(1 for _ in path.open())
    assert n >= 100


def test_shadow_markdown_renders():
    md = render_shadow_markdown(
        ["vega", "llm_schema"],
        2,
        {
            "vega": {
                "team_accuracy": 1.0,
                "forced_wrong_rate": 0.0,
                "abstain_rate": 0.0,
                "needs_review_rate": 0.0,
                "mean_latency_ms": 10,
                "estimated_usd_per_decision": 0.0,
                "estimated_usd_total": 0.0,
            },
            "llm_schema": {
                "team_accuracy": 1.0,
                "forced_wrong_rate": 0.0,
                "abstain_rate": 0.0,
                "needs_review_rate": 0.0,
                "mean_latency_ms": 20,
                "estimated_usd_per_decision": 0.001,
                "estimated_usd_total": 0.002,
            },
        },
        [],
    )
    assert "Shadow mode" in md
    assert "llm_schema" in md
