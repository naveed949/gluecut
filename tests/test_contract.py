import pytest

from triage.contract import decide_action, validate_llm_payload


def test_decide_action_routes_when_clear():
    assert decide_action(abstain=False, needs_human=False) == "route"


def test_decide_action_reviews_on_abstain_or_human():
    assert decide_action(abstain=True, needs_human=False) == "needs_review"
    assert decide_action(abstain=False, needs_human=True) == "needs_review"


def test_validate_llm_payload_ok():
    out = validate_llm_payload(
        {"team": "billing", "priority": 2, "needs_human": False, "confidence": 0.9}
    )
    assert out["team"] == "billing"


@pytest.mark.parametrize(
    "payload",
    [
        {"team": "finance", "priority": 1, "needs_human": False, "confidence": 0.9},
        {"team": "billing", "priority": 9, "needs_human": False, "confidence": 0.9},
        {"team": "billing", "priority": 1, "needs_human": "yes", "confidence": 0.9},
        {"team": "billing", "priority": 1, "needs_human": False, "confidence": 1.5},
    ],
)
def test_validate_llm_payload_rejects(payload):
    with pytest.raises(ValueError):
        validate_llm_payload(payload)
