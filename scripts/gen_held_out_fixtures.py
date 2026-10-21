#!/usr/bin/env python3
"""Generate held-out fixtures under research/RUBRIC.md (rubric-v1). Idempotent overwrite."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAGE_OUT = ROOT / "fixtures" / "triage" / "held_out.jsonl"
PAY_OUT = ROOT / "fixtures" / "payments" / "held_out.jsonl"


def _t(
    id: str,
    subject: str,
    body: str,
    team: str,
    priority: int,
    needs_human: bool,
    *,
    split: str = "held_out",
) -> dict:
    return {
        "id": id,
        "subject": subject,
        "body": body,
        "expected": {
            "team": team,
            "priority": priority,
            "needs_human": needs_human,
        },
        "rubric": "rubric-v1",
        "split": split,
        "domain": "triage",
    }


def triage_cases() -> list[dict]:
    cases: list[dict] = []

    billing_bodies = [
        ("Refund request", "Please refund my last invoice."),
        ("Double charge", "I was charged twice for the same subscription this month."),
        ("Receipt", "Please resend the March payment receipt to finance@acme.com."),
        ("Invoice PDF", "I need a PDF copy of invoice INV-2044 for accounting."),
        ("Cancel + refund", "Cancel my plan and refund the unused portion."),
        ("Wrong amount", "You billed me $99 but my plan is $49. Please correct."),
        ("Failed payment notice", "My card was charged but the portal still says unpaid."),
        ("Tax on invoice", "Why is there sales tax on invoice INV-889?"),
        ("Proration", "I upgraded mid-cycle — the proration on my bill looks wrong."),
        ("Wire transfer", "We paid by wire; please apply payment to account ACCT-12."),
    ]
    for i, (subj, body) in enumerate(billing_bodies):
        for variant in range(3):
            cases.append(
                _t(
                    f"bill-{i}-{variant}",
                    subj if variant == 0 else f"{subj} ({variant})",
                    body if variant == 0 else f"{body} Ticket ref {1000 + i * 3 + variant}.",
                    "billing",
                    2 if "charge" in body.lower() or "refund" in body.lower() else 1,
                    False,
                )
            )

    tech_bodies = [
        ("App crash", "The iOS app crashes when I open Settings. Stack trace attached."),
        ("API 500", "Our integration gets HTTP 500 from /v1/orders since this morning."),
        ("CSV bug", "Export to CSV drops the last column. Repro: Reports → Export."),
        ("SSO login", "SSO login redirects to a blank page for all Okta users."),
        ("Webhook missing", "Webhooks stopped firing for invoice.paid events."),
        ("Slow query", "Dashboard takes 40s to load the analytics page."),
        ("Mobile blank", "Android build 3.2 shows a blank screen after splash."),
        ("Rate limit docs", "Docs say 100 rpm but we are throttled at 20."),
        ("Timezone bug", "Scheduled reports run at UTC instead of account timezone."),
        ("Search broken", "Global search returns zero results for known document titles."),
    ]
    for i, (subj, body) in enumerate(tech_bodies):
        for variant in range(3):
            pri = 2 if any(w in body.lower() for w in ("500", "sso", "crash", "blank")) else 1
            cases.append(
                _t(
                    f"tech-{i}-{variant}",
                    subj,
                    body if variant == 0 else f"{body} Env: prod-{variant}.",
                    "technical",
                    pri,
                    False,
                )
            )

    sales_bodies = [
        ("Enterprise demo", "We want a demo of Enterprise and a pricing walkthrough."),
        ("Upgrade path", "How do we upgrade from Pro to Business and what is the price delta?"),
        ("Annual discount", "Do you offer annual billing discounts for startups?"),
        ("New logo", "Our team of 80 is evaluating vendors; please send a sales pack."),
        ("Seat expansion", "We need 25 more seats next quarter — can sales help?"),
        ("Partner pricing", "Is there partner pricing for agencies?"),
        ("POC request", "Can we run a 30-day POC with SSO enabled?"),
        ("Compare plans", "Please compare Team vs Business feature lists for our CFO."),
        ("Renewal discuss", "Our renewal is in 60 days; we want to discuss a multi-year deal."),
        ("Marketplace", "Interested in listing our integration in your marketplace."),
    ]
    for i, (subj, body) in enumerate(sales_bodies):
        for variant in range(2):
            cases.append(
                _t(
                    f"sales-{i}-{variant}",
                    subj,
                    body if variant == 0 else f"{body} Company size ~{50 + variant * 10}.",
                    "sales",
                    1,
                    False,
                )
            )

    # Hard / human-required cases
    hard = [
        _t(
            "hard-multi-1",
            "Refund + crash",
            "Please refund my last invoice. Also the app crashed after I paid.",
            "billing",
            2,
            True,
        ),
        _t(
            "hard-multi-2",
            "Pricing + bug",
            "What does Enterprise cost, and also export is broken for us.",
            "sales",
            1,
            True,
        ),
        _t(
            "hard-gdpr",
            "Data request",
            "Under GDPR I demand deletion of all my data immediately or my lawyer will follow up.",
            "technical",
            3,
            True,
        ),
        _t(
            "hard-fraud",
            "Fraud",
            "Someone used my account to make fraudulent charges. This is urgent.",
            "billing",
            3,
            True,
        ),
        _t(
            "hard-outage",
            "Down",
            "Production is down ASAP — login returns errors for all users in EU.",
            "technical",
            3,
            False,
        ),
        _t(
            "hard-ambiguous",
            "Help",
            "This is not working and I am unhappy. Fix it.",
            "technical",
            1,
            True,
        ),
        _t(
            "hard-negation",
            "Clarification",
            "I do not want a refund. I only need a copy of my invoice PDF for accounting.",
            "billing",
            1,
            False,
        ),
        _t(
            "hard-sarcasm",
            "Great product",
            "Oh great, another charge I did not authorize. Love paying for a broken feature.",
            "billing",
            2,
            True,
        ),
        _t(
            "hard-empty",
            "",
            "...",
            "technical",
            1,
            True,
        ),
        _t(
            "hard-lawyer",
            "Legal",
            "Our counsel requires a DPA amendment before we renew. Please escalate.",
            "sales",
            3,
            True,
        ),
    ]
    cases.extend(hard)

    # Pad to >= 100 with numbered clear cases if needed
    n = 0
    while len(cases) < 110:
        n += 1
        cases.append(
            _t(
                f"pad-bill-{n}",
                "Billing pad",
                f"Please apply credit note CN-{n} to my account and confirm the balance.",
                "billing",
                1,
                False,
            )
        )
        if len(cases) >= 110:
            break
        cases.append(
            _t(
                f"pad-tech-{n}",
                "Tech pad",
                f"Feature flag panel throws a 404 on project P-{n}.",
                "technical",
                1,
                False,
            )
        )

    # Mark all scored
    for c in cases:
        c["eval"] = {"accuracy": True}
    return cases


def payment_cases() -> list[dict]:
    templates = [
        (
            "nsf-1",
            "insufficient_funds",
            False,
            "try_another_card",
            "Declined: insufficient funds on the card.",
        ),
        (
            "nsf-2",
            "insufficient_funds",
            False,
            "try_another_card",
            "The bank returned NSF — not enough balance to complete payment.",
        ),
        (
            "fraud-1",
            "fraud_suspected",
            False,
            "contact_bank",
            "Issuing bank declined due to suspected unusual activity.",
        ),
        (
            "fraud-2",
            "fraud_suspected",
            False,
            "contact_bank",
            "Transaction blocked by fraud filter. Customer should contact their bank.",
        ),
        (
            "exp-1",
            "expired_card",
            False,
            "try_another_card",
            "Card expired — expiration date is in the past.",
        ),
        (
            "exp-2",
            "expired_card",
            False,
            "try_another_card",
            "Payment method rejected: card expiration invalid.",
        ),
        (
            "tmp-1",
            "temporary",
            True,
            "try_later",
            "Issuer unavailable. Please try again in a few minutes.",
        ),
        (
            "tmp-2",
            "temporary",
            True,
            "try_later",
            "Network timeout talking to the processor — transient error.",
        ),
        (
            "tmp-3",
            "temporary",
            True,
            "try_later",
            "Temporary glitch at the gateway. Retry recommended.",
        ),
        (
            "oth-1",
            "other",
            False,
            "support",
            "Unable to process payment for an unspecified reason.",
        ),
        (
            "oth-2",
            "other",
            False,
            "support",
            "Decline code missing; message: do not honor.",
        ),
    ]
    rows: list[dict] = []
    for base_id, reason, retry, hint, msg in templates:
        for v in range(4):
            rows.append(
                {
                    "id": f"{base_id}-v{v}",
                    "provider": "acme_pay",
                    "failure_code": None if v % 2 == 0 else "generic_decline",
                    "failure_message": msg if v == 0 else f"{msg} (attempt {v})",
                    "expected": {
                        "reason": reason,
                        "auto_retry": retry,
                        "user_hint": hint,
                    },
                    "rubric": "rubric-v1",
                    "split": "held_out",
                    "domain": "payments",
                    "eval": {"accuracy": True},
                }
            )
    return rows


def main() -> None:
    TRIAGE_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAY_OUT.parent.mkdir(parents=True, exist_ok=True)
    triage = triage_cases()
    pay = payment_cases()
    assert len(triage) >= 100, len(triage)
    with TRIAGE_OUT.open("w") as f:
        for row in triage:
            f.write(json.dumps(row) + "\n")
    with PAY_OUT.open("w") as f:
        for row in pay:
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(triage)} → {TRIAGE_OUT}")
    print(f"wrote {len(pay)} → {PAY_OUT}")


if __name__ == "__main__":
    main()
