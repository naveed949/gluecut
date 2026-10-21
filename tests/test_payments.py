from triage.engines.llm_client import SimulatedJsonLlm
from triage.payments import LlmSchemaPaymentEngine, PaymentEvent, load_payment_fixtures


def test_payment_fixtures_nonempty():
    rows = load_payment_fixtures()
    assert len(rows) >= 40


def test_payment_schema_engine_nsf():
    eng = LlmSchemaPaymentEngine(client=SimulatedJsonLlm(), client_label="simulated")
    d = eng.decide(
        PaymentEvent(failure_message="Declined: insufficient funds on the card.")
    )
    assert d.reason == "insufficient_funds"
    assert d.auto_retry is False
    assert d.user_hint == "try_another_card"
