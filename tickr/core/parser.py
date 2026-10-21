"""
Command parser for the Tickr terminal.

Tickr uses a Bloomberg-inspired command grammar while keeping
the interface lightweight and terminal-native.
"""

import shlex
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Command constants
# ---------------------------------------------------------------------------

EQUITY = "EQUITY"
DES = "DES"
FA = "FA"
GP = "GP"
TA = "TA"
RV = "RV"
HP = "HP"
NI = "NI"
MACRO = "MACRO"
VERDICT = "VERDICT"
RATE = "RATE"
COMPARE = "COMPARE"
SCREEN = "SCREEN"
WATCH = "WATCH"
EXPORT = "EXPORT"
SOURCE = "SOURCE"
HELP = "HELP"
EXIT = "EXIT"
UNKNOWN = "UNKNOWN"


# Backwards-compatible command names expected by the test suite.
CMD_EQUITY = EQUITY
CMD_DES = DES
CMD_FA = FA
CMD_GP = GP
CMD_TA = TA
CMD_RV = RV
CMD_HP = HP
CMD_NI = NI
CMD_MACRO = MACRO
CMD_VERDICT = VERDICT
CMD_RATE = RATE
CMD_COMPARE = COMPARE
CMD_SCREEN = SCREEN
CMD_WATCH = WATCH
CMD_EXPORT = EXPORT
CMD_SOURCE = SOURCE
CMD_HELP = HELP
CMD_EXIT = EXIT
CMD_UNKNOWN = UNKNOWN


class ParseError(ValueError):
    """Raised when a syntactically invalid Tickr command is encountered."""


TIMEFRAMES = {
    "1D",
    "5D",
    "1M",
    "3M",
    "6M",
    "1Y",
    "2Y",
    "5Y",
}


EXCHANGES = {
    "NS",
    "BO",
    "LN",
    "PA",
    "DE",
    "AS",
    "MI",
    "HK",
    "TK",
    "AU",
    "SG",
    "KS",
    "US",
    "CN",
    "IN",
}


COUNTRIES = {
    "IN",
    "US",
    "GB",
    "AU",
    "HK",
    "JP",
}


ALIASES = {
    "?": HELP,
    "QUIT": EXIT,
    "Q": EXIT,
}


@dataclass
class ParsedCommand:
    """Represents a parsed Tickr command."""

    command: str

    ticker: str | None = None
    exchange: str | None = None
    country: str | None = None
    timeframe: str | None = None

    qualifier: str | None = None
    subcommand: str | None = None

    args: list[str] = field(default_factory=list)

    raw: str = ""


def parse(raw: str) -> ParsedCommand:
    """Parse a raw Tickr command string."""

    raw = raw.strip()

    if not raw:
        return ParsedCommand(
            command=UNKNOWN,
            raw=raw,
        )

    try:
        tokens = shlex.split(raw)
    except ValueError as exc:
        raise ParseError(f"Invalid command syntax: {exc}") from exc

    if not tokens:
        return ParsedCommand(
            command=UNKNOWN,
            raw=raw,
        )

    # Normalize tokens.
    tokens = [token.strip() for token in tokens]
    upper_tokens = [token.upper() for token in tokens]

    first = upper_tokens[0]

    # -----------------------------------------------------------------------
    # Aliases
    # -----------------------------------------------------------------------

    if first in ALIASES:
        return ParsedCommand(
            command=ALIASES[first],
            raw=raw,
            args=tokens[1:],
        )

    # -----------------------------------------------------------------------
    # HELP / EXIT
    # -----------------------------------------------------------------------

    if first in {HELP, EXIT}:
        return ParsedCommand(
            command=first,
            raw=raw,
            args=tokens[1:],
        )

    # -----------------------------------------------------------------------
    # EQUITY
    #
    # Examples:
    #   EQUITY AAPL
    #   EQUITY AAPL US
    #   EQUITY RELIANCE NS IN
    #   AAPL EQUITY
    #   AAPL US EQUITY
    #   RELIANCE IN NS EQUITY
    # -----------------------------------------------------------------------

    if first == EQUITY:
        args = tokens[1:]
        upper_args = upper_tokens[1:]

        if not args:
            raise ParseError("EQUITY requires a ticker")

        return _parse_equity(
            raw=raw,
            args=args,
            upper_args=upper_args,
        )

    # Bloomberg-style EQUITY command.

    if EQUITY in upper_tokens[1:]:
        equity_index = upper_tokens.index(EQUITY)

        return _parse_equity(
            raw=raw,
            args=tokens[:equity_index],
            upper_args=upper_tokens[:equity_index],
        )

    # -----------------------------------------------------------------------
    # Direct commands
    # -----------------------------------------------------------------------

    direct_commands = {
        DES,
        FA,
        GP,
        TA,
        RV,
        HP,
        NI,
        MACRO,
        VERDICT,
        RATE,
        COMPARE,
        SCREEN,
        WATCH,
        EXPORT,
        SOURCE,
    }

    if first in direct_commands:
        args = tokens[1:]

        # FA Q → quarterly fundamentals.
        if first == FA:
            qualifier = None

            if args:
                qualifier = args[0].upper()

            return ParsedCommand(
                command=first,
                raw=raw,
                args=args,
                qualifier=qualifier,
            )

        # GP 1D → price chart with timeframe.
        if first == GP:
            timeframe = None

            if args:
                candidate = args[0].upper()
                if candidate in TIMEFRAMES:
                    timeframe = candidate

            return ParsedCommand(
                command=first,
                raw=raw,
                args=args,
                timeframe=timeframe,
            )

        # WATCH ADD AAPL
        if first == WATCH:
            subcommand = None
            watch_args = args

            if args:
                subcommand = args[0].upper()
                watch_args = args[1:]

            ticker = watch_args[0].upper() if watch_args else None

            return ParsedCommand(
                command=first,
                raw=raw,
                args=args,
                ticker=ticker,
                subcommand=subcommand,
            )

        # Commands that require a ticker/argument.
        if first == COMPARE and not args:
            raise ParseError("COMPARE requires a ticker")

        parsed = ParsedCommand(
            command=first,
            raw=raw,
            args=args,
        )

        if args:
            parsed.ticker = args[0].upper()

        return parsed

    return ParsedCommand(
        command=UNKNOWN,
        raw=raw,
        args=tokens,
    )


def _parse_equity(
    raw: str,
    args: list[str],
    upper_args: list[str],
) -> ParsedCommand:
    """Parse EQUITY security syntax."""

    if not args:
        raise ParseError("EQUITY requires a ticker")

    ticker = upper_args[0]

    if not ticker:
        raise ParseError("EQUITY requires a ticker")

    exchange = None
    country = None
    timeframe = None
    remaining = []

    for original, upper in zip(args[1:], upper_args[1:]):
        if upper in TIMEFRAMES:
            timeframe = upper
        elif upper == "IN":
            country = upper
        elif upper == "US":
            exchange = upper
        elif upper in COUNTRIES:
            country = upper
        elif upper in EXCHANGES:
            exchange = upper
        else:
            remaining.append(original)

    return ParsedCommand(
        command=EQUITY,
        ticker=ticker,
        exchange=exchange,
        country=country,
        timeframe=timeframe,
        args=remaining,
        raw=raw,
    )