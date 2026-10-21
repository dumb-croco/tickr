"""
Session state for the Tickr terminal.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


EXCHANGE_SUFFIX = {
    "NS": ".NS",
    "BO": ".BO",
    "LN": ".L",
    "PA": ".PA",
    "DE": ".DE",
    "AS": ".AS",
    "MI": ".MI",
    "HK": ".HK",
    "TK": ".T",
    "AU": ".AX",
    "SG": ".SI",
    "KS": ".KS",
    "US": "",
    "CN": ".TO",
    "IN": None,
}

COUNTRY_DEFAULT_SUFFIX = {
    "IN": ".NS",
    "US": "",
    "GB": ".L",
    "AU": ".AX",
    "HK": ".HK",
    "JP": ".T",
}


@dataclass
class Session:
    """Holds the current Tickr session state."""

    ticker: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    yf_symbol: Optional[str] = None
    company_name: Optional[str] = None

    timeframe: str = "1Y"

    provider_override: Optional[str] = None
    watchlist: list[str] = field(default_factory=list)

    last_page: Optional[str] = None
    last_data: Any = None

    # Generic AI verdict cache.
    ai_verdict_cache: Optional[dict] = None

    def set_security(
        self,
        ticker: str,
        exchange: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        """Set the active security."""

        self.ticker = ticker.upper().strip()
        self.exchange = exchange.upper().strip() if exchange else None
        self.country = country.upper().strip() if country else None

        self.yf_symbol = self._resolve_symbol()

        self.company_name = None
        self.ai_verdict_cache = None

    def _resolve_symbol(self) -> str:
        """Resolve the user-provided ticker into a Yahoo Finance symbol."""

        if not self.ticker:
            raise ValueError("Ticker is required.")

        # Explicit exchange takes priority.
        if self.exchange:
            suffix = EXCHANGE_SUFFIX.get(self.exchange)

            if suffix is None:
                return self.ticker

            return f"{self.ticker}{suffix}"

        # Country-based resolution.
        if self.country:
            suffix = COUNTRY_DEFAULT_SUFFIX.get(self.country)

            if suffix is not None:
                return f"{self.ticker}{suffix}"

        # Default to US-style ticker.
        return self.ticker

    def set_timeframe(self, timeframe: str) -> None:
        """Set the active chart/data timeframe."""

        timeframe = timeframe.upper().strip()

        valid_timeframes = {
            "1D",
            "5D",
            "1M",
            "3M",
            "6M",
            "1Y",
            "2Y",
            "5Y",
        }

        if timeframe not in valid_timeframes:
            raise ValueError(
                f"Invalid timeframe '{timeframe}'. "
                f"Valid values: {', '.join(sorted(valid_timeframes))}"
            )

        self.timeframe = timeframe

    def __str__(self) -> str:
        """Human-readable session description."""

        symbol = self.yf_symbol or self.ticker or "No security"

        company = (
            f" · {self.company_name}"
            if self.company_name
            else ""
        )

        return (
            f"{symbol}{company} "
            f"· {self.timeframe}"
        )