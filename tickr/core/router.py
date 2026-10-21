"""
Command router for Tickr.
"""

from typing import TYPE_CHECKING

from rich.console import Console

from tickr.core.parser import (
    COMPARE,
    DES,
    EQUITY,
    EXIT,
    EXPORT,
    FA,
    GP,
    HELP,
    HP,
    MACRO,
    NI,
    RATE,
    RV,
    SCREEN,
    SOURCE,
    TA,
    VERDICT,
    WATCH,
    UNKNOWN,
)

from tickr.render.theme import RICH_THEME


console = Console(theme=RICH_THEME)


if TYPE_CHECKING:
    from tickr.core.session import Session
    from tickr.providers.base import DataProvider
    from tickr.ai.client import GroqClient


class Router:
    """Routes parsed Tickr commands to the appropriate page."""

    def __init__(
        self,
        session: "Session",
        provider: "DataProvider",
        ai: "GroqClient",
    ):
        self.session = session
        self.provider = provider

        self.ai = ai

    def dispatch(self, parsed) -> bool:
        """Dispatch a parsed command.

        Returns False when the REPL should exit.
        """

        command = parsed.command
        s = self.session

        if command == EXIT:
            return False

        if command == HELP:
            from tickr.pages.help import render_help

            render_help()
            return True

        if command == EQUITY:
            from tickr.pages.equity import render_equity

            render_equity(
                s,
                parsed,
                self.provider,
                self.ai,
            )
            return True

        if command == DES:
            from tickr.pages.des import render_des

            self._require_security()
            render_des(
                s,
                self.provider,
            )
            return True

        if command == FA:
            from tickr.pages.fa import render_fa

            self._require_security()
            render_fa(
                s,
                parsed,
                self.provider,
                self.ai,
            )
            return True

        if command == GP:
            from tickr.pages.gp import render_gp

            self._require_security()
            render_gp(
                s,
                parsed,
                self.provider,
            )
            return True

        if command == HP:
            from tickr.pages.hp import render_hp

            self._require_security()
            render_hp(
                s,
                parsed,
                self.provider,
            )
            return True

        if command == VERDICT:
            from tickr.pages.verdict import render_verdict

            self._require_security()
            render_verdict(
                s,
                self.provider,
                self.ai,
            )
            return True

        if command == RATE:
            from tickr.pages.rate import render_rate

            self._require_security()
            render_rate(
                s,
                self.provider,
                self.ai,
            )
            return True

        if command in {
            TA,
            RV,
            NI,
            MACRO,
            COMPARE,
            SCREEN,
            WATCH,
            EXPORT,
        }:
            console.print(
                f"[warning]'{command}' is planned for a future Tickr release.[/warning]"
            )
            return True

        if command == SOURCE:
            if not parsed.args:
                console.print(
                    "[error]Usage: SOURCE <provider>[/error]"
                )
                return True

            self.session.provider_override = parsed.args[0]

            console.print(
                f"[success]Data source set to "
                f"{self.session.provider_override}[/success]"
            )
            return True

        if command == UNKNOWN:
            console.print(
                "[error]Unknown command. Type HELP for available commands.[/error]"
            )
            return True

        console.print(
            "[error]Unable to route command.[/error]"
        )

        return True

    def _require_security(self) -> None:
        """Ensure a security is selected before running a page."""

        if not self.session.ticker:
            raise ValueError(
                "No security selected. "
                "Use EQUITY <TICKER> first."
            )