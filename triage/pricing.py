"""Assumed API list prices for $ estimates in bench/shadow (document, not invoice)."""

from __future__ import annotations

# gpt-4o-mini list prices as of late 2025 — update if your bill differs.
# https://openai.com/api/pricing/
GPT4O_MINI_INPUT_PER_MTOK = 0.15
GPT4O_MINI_OUTPUT_PER_MTOK = 0.60

# Local Vega: no API $ (device power ignored in this research table).
VEGA_USD_PER_DECISION = 0.0


def estimate_chat_usd(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    engine: str,
    input_per_mtok: float = GPT4O_MINI_INPUT_PER_MTOK,
    output_per_mtok: float = GPT4O_MINI_OUTPUT_PER_MTOK,
) -> float:
    if engine == "vega":
        return VEGA_USD_PER_DECISION
    return (prompt_tokens / 1_000_000.0) * input_per_mtok + (
        completion_tokens / 1_000_000.0
    ) * output_per_mtok
