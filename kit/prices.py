"""Model prices for the cost column, in US dollars per 1 million tokens (input, output).

Source: OpenRouter model pages, checked 2026-10-08
  https://openrouter.ai/typesafe/jev-1.13          (JEV output tokens are free)
  https://openrouter.ai/google/gemini-3.5-flash    (thinking tokens are billed as output)
Update these when prices change, and keep the date in the step READMEs.
"""

PRICES_CHECKED_ON = "2026-10-08"

PRICES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "jev-1.13": (0.042, 0.0),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.5-flash": (1.50, 9.00),
}


def price_for(model: str | None) -> tuple[float, float] | None:
    """Prices for a model name as the API reports it (e.g. "typesafe/jev-1.13-20260917")."""
    if not model:
        return None
    for key in sorted(PRICES_USD_PER_MTOK, key=len, reverse=True):  # longest first: "-lite" before plain
        if key in model:
            return PRICES_USD_PER_MTOK[key]
    return None


def cost_usd(model: str | None, input_tokens: int | None, output_tokens: int | None) -> float | None:
    prices = price_for(model)
    if prices is None or input_tokens is None:
        return None
    return (input_tokens * prices[0] + (output_tokens or 0) * prices[1]) / 1_000_000
