"""Minimal vegaml smoke test. Prefer: uv run python -m triage decide --engine vega ..."""

import vegaml

v = vegaml.load()

out = v.decide(
    {"body": "Hello — please refund my last invoice."},
    {
        "team": {
            "type": "choice",
            "instructions": "Which team should handle this?",
            "criteria": {
                "billing": "payments and refunds",
                "technical": "bugs and product faults",
                "sales": "new business",
            },
        }
    },
)

ans = out["answers"]["team"]
print(ans["choice"], ans["probs"], "abstain=", ans["abstain"])
