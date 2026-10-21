"""
Tickr CLI — terminal-native equity research REPL.
"""

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from rich.console import Console

from tickr import __version__
from tickr.ai.client import GroqClient
from tickr.cache.store import CacheStore
from tickr.config.loader import load_config
from tickr.core.parser import parse
from tickr.core.router import Router
from tickr.core.session import Session
from tickr.providers.registry import ProviderRegistry
from tickr.render.theme import RICH_THEME, t


console = Console(theme=RICH_THEME)


_BANNER = r"""
████████╗██╗ ██████╗██╗  ██╗██████╗
╚══██╔══╝██║██╔════╝██║ ██╔╝██╔══██╗
   ██║   ██║██║     █████╔╝ ██████╔╝
   ██║   ██║██║     ██╔═██╗ ██╔══██╗
   ██║   ██║╚██████╗██║  ██╗██║  ██║
   ╚═╝   ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝

        AI-POWERED EQUITY RESEARCH TERMINAL
"""


_AUTOCOMPLETE_WORDS = [
    "EQUITY",
    "DES",
    "FA",
    "GP",
    "TA",
    "RV",
    "HP",
    "NI",
    "MACRO",
    "VERDICT",
    "RATE",
    "COMPARE",
    "SCREEN",
    "WATCH",
    "EXPORT",
    "SOURCE",
    "HELP",
    "EXIT",
    "QUIT",
    "Q",
]


def _print_banner() -> None:
    """Print the Tickr startup banner."""

    console.print(
        _BANNER,
        style="accent",
    )

    console.print(
        f"[bold]TICKR v{__version__}[/bold] "
        "· AI-powered terminal equity research",
        style="accent",
    )

    console.print(
        "Type [bold]HELP[/bold] for available commands.\n"
    )


def _build_prompt_session() -> PromptSession:
    """Create the prompt-toolkit REPL session."""

    history_dir = Path.home() / ".tickr"
    history_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    history_file = history_dir / "history"

    completer = WordCompleter(
        _AUTOCOMPLETE_WORDS,
        ignore_case=True,
    )

    return PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
    )


def main() -> None:
    """Run the Tickr terminal."""

    config = load_config()

    cache = CacheStore(
        provider_ttl_minutes=config.get(
            "cache_ttl_provider_minutes",
            15,
        ),
        ai_ttl_hours=config.get(
            "cache_ttl_ai_hours",
            24,
        ),
    )

    provider = ProviderRegistry(config)

    ai = GroqClient(
        api_key=config.get(
            "groq_api_key",
            "",
        ),
        cache=cache,
    )

    session = Session(
        timeframe=config.get(
            "default_timeframe",
            "1Y",
        )
    )

    router = Router(
        session=session,
        provider=provider,
        ai=ai,
    )

    _print_banner()

    # Provider status.
    try:
        console.print(
            "[success]Data provider: active[/success]"
        )
    except Exception:
        console.print(
            "[warning]Data provider: unavailable[/warning]"
        )

    # AI status.
    if config.get("groq_api_key"):
        console.print(
            "[success]AI: active[/success]"
        )
    else:
        console.print(
            "[warning]AI: inactive — configure your Groq API key[/warning]"
        )

    console.print()

    prompt_session = _build_prompt_session()

    while True:
        try:
            raw = prompt_session.prompt(
                "Tickr > "
            )

            parsed = parse(raw)

            should_continue = router.dispatch(
                parsed
            )

            if not should_continue:
                break

        except KeyboardInterrupt:
            console.print(
                "\n[muted]Use EXIT or Ctrl-D to quit.[/muted]"
            )

        except EOFError:
            break

        except Exception as exc:
            console.print(
                f"[error]Error:[/error] {exc}"
            )


if __name__ == "__main__":
    main()