import json

from triage.contract import Ticket
from triage.engines.llm_client import SimulatedJsonLlm
from triage.engines.llm_engine import LlmTriageEngine
from triage.engines.llm_parse import extract_json_object
from triage.engines.llm_structured_engine import LlmStructuredTriageEngine


def test_extract_json_from_fence():
    text = 'Here you go:\n```json\n{"team":"billing","priority":1,"needs_human":false,"confidence":0.8}\n```'
    assert extract_json_object(text)["team"] == "billing"


def test_extract_json_embedded():
    text = 'Sure {"team":"sales","priority":1,"needs_human":false,"confidence":0.7} thanks'
    assert extract_json_object(text)["team"] == "sales"


def test_repair_round_on_broken_marker():
    engine = LlmTriageEngine(client=SimulatedJsonLlm(), client_label="simulated")
    decision = engine.triage(
        Ticket(body="[[force_bad_json]] please refund my invoice for March.")
    )
    assert decision.orchestration["repair_rounds"] >= 1
    assert decision.orchestration["schema_failures"] >= 1
    assert decision.team == "billing"
    assert decision.action == "route"


def test_simulated_billing_path():
    engine = LlmTriageEngine(client=SimulatedJsonLlm(), client_label="simulated")
    decision = engine.triage(Ticket(body="Please refund my last invoice."))
    assert decision.team == "billing"
    assert decision.orchestration["parse_attempts"] == 1
    assert json.loads(decision.raw["replies"][0])["team"] == "billing"


def test_structured_skips_fence_repair_on_marker():
    engine = LlmStructuredTriageEngine(client=SimulatedJsonLlm(), client_label="simulated")
    decision = engine.triage(
        Ticket(body="[[force_bad_json]] please refund my invoice for March.")
    )
    assert decision.orchestration["mode"] == "json_object"
    assert decision.orchestration["repair_rounds"] == 0
    assert decision.team == "billing"
