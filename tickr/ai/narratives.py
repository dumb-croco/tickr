"""
ai/narratives.py — Anomaly flagging and plain-English narratives via Groq.

Used on the FA page to unprompted surface inconsistencies in fundamentals
(debt spike, margin compression vs peers, guidance mismatch, etc.).
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tickr.ai.client import GroqClient


def _build_anomaly_state(info: dict[str, Any]) -> dict[str, Any]:
    """Build the Groq state dict for anomaly detection."""

    def s(k: str) -> Any:
        v = info.get(k)
        return round(float(v), 4) if v is not None else None

    return {
        "company":           info.get("name", ""),
        "sector":            info.get("sector", ""),

        # Profitability trends
        "gross_margins":      s("gross_margins"),
        "operating_margins":  s("operating_margins"),
        "profit_margins":     s("profit_margins"),
        "roe":                s("roe"),

        # Growth
        "revenue_growth":     s("revenue_growth"),
        "earnings_growth":    s("earnings_growth"),

        # Leverage
        "debt_to_equity":     s("debt_to_equity"),
        "current_ratio":      s("current_ratio"),
        "free_cash_flow":     s("free_cash_flow"),

        # Valuation vs earnings trajectory
        "forward_pe":         s("forward_pe"),
        "trailing_pe":        s("trailing_pe"),
        "peg_ratio":          s("peg_ratio"),
        "trailing_eps":       s("trailing_eps"),
        "forward_eps":        s("forward_eps"),

        # Analyst signals
        "analyst_rating":      info.get("analyst_rating"),
        "target_mean_price":   s("target_mean_price"),
        "target_high_price":   s("target_high_price"),
        "target_low_price":    s("target_low_price"),
        "current_price":       s("current_price"),
        "num_analyst_opinions": info.get(
            "num_analyst_opinions"
        ),
    }


def _build_anomaly_questions() -> dict:
    """Build the Groq question dict for anomaly detection."""

    return {
        "choices": {
            "has_anomaly": {
                "choices": [
                    "yes",
                    "no",
                ],
                "instructions": (
                    "Looking at this company's fundamentals, is there any notable anomaly, "
                    "inconsistency, or red flag that a fundamental analyst should investigate? "
                    "Examples: debt-to-equity spiking while margins compress, "
                    "earnings growth decelerating while valuation re-rates higher, "
                    "analyst target dispersion is extreme, forward PE much lower than trailing PE "
                    "despite weak growth, negative free cash flow with high debt. "
                    "Only flag something if it is genuinely unusual."
                ),
            },
            "anomaly_description": {
                "choices": [
                    "Debt rising sharply while margins are compressing — leverage risk growing",
                    "Valuation re-rating higher despite decelerating earnings growth",
                    "Wide analyst target dispersion suggests high uncertainty in fair value",
                    "Negative free cash flow combined with elevated debt — watch liquidity",
                    "Forward PE significantly below trailing PE despite flat or negative EPS growth",
                    "Low analyst coverage — limited visibility into fundamentals",
                    "No anomalies detected in the current fundamental profile.",
                ],
                "instructions": (
                    "If there is an anomaly, describe it in one direct sentence (max 20 words). "
                    "If no anomaly, return 'No anomalies detected in the current fundamental profile.'"
                ),
            },
        }
    }


def get_anomaly_flag(
    ai: "GroqClient",
    info: dict[str, Any],
    ticker: str,
) -> Optional[str]:
    """
    Ask Groq to scan fundamentals for anomalies.

    Returns a one-sentence anomaly description, or None if Groq is
    unavailable or no anomaly is detected.
    """

    if not ai.available:
        return None

    state = _build_anomaly_state(info)
    questions = _build_anomaly_questions()

    response = ai.call(
        state=state,
        questions=questions,
        ticker=ticker,
        timeframe="fundamental",
        cache_tag="anomaly",
    )

    if not response:
        return None

    choices = response.get(
        "choices",
        {},
    )

    has_anomaly = choices.get(
        "has_anomaly",
        {},
    )

    if (
        isinstance(has_anomaly, dict)
        and has_anomaly.get("choice") == "yes"
    ):
        desc = choices.get(
            "anomaly_description",
            {},
        )

        if isinstance(desc, dict):
            text = desc.get(
                "choice",
                "",
            )

            if text and "No anomalies" not in text:
                return text

    return None  # no anomaly or description indeterminate