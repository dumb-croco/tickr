# Tickr

> An equity research console (like a Bloomberg terminal) — free, open-source, and AI-powered.

![Tickr Demo](assets/demo.gif)

```text
████████╗██╗ ██████╗██╗  ██╗██████╗
╚══██╔══╝██║██╔════╝██║ ██╔╝██╔══██╗
   ██║   ██║██║     █████╔╝ ██████╔╝
   ██║   ██║██║     ██╔═██╗ ██╔══██╗
   ██║   ██║╚██████╗██║  ██╗██║  ██║
   ╚═╝   ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝

       AI-POWERED EQUITY RESEARCH TERMINAL
```

Tickr is free and gives you the muscle-memory command grammar of a real terminal, dense richly-formatted output, and AI-powered analysis through Groq embedded in supported screens — delivering the one non-obvious insight that raw numbers alone can't.

---

## Install

```bash
pip install tickr
```

Then launch the REPL:

```bash
tickr
```

---

## Quickstart

```text
Tickr > AAPL EQUITY          # resolve Apple, set session
Tickr > DES                  # company description
Tickr > FA                   # full fundamentals
Tickr > FA Q                 # quarterly fundamentals
Tickr > GP                   # 1Y price chart
Tickr > GP 6M                # 6-month chart
Tickr > HP                   # historical OHLCV
Tickr > VERDICT              # AI buy/sell/hold distribution
Tickr > RATE                 # AI multi-axis fundamental rating
Tickr > HELP                 # full command reference
Tickr > EXIT                 # quit
```

**Indian markets:**

```text
Tickr > RELIANCE IN NS EQUITY    # Reliance Industries on NSE
Tickr > INFY BO EQUITY            # Infosys on BSE
```

---

## Command Reference

| Command | Description |
|---|---|
| `<TICKER> [EXCHANGE] EQUITY` | Resolve security, set session, show snapshot |
| `DES` | Company description, sector, key people |
| `FA` / `FA Q` | Full fundamentals (annual / quarterly) |
| `GP [timeframe]` | In-terminal price chart (`1D 5D 1M 3M 6M 1Y 2Y 5Y`) |
| `HP` | Historical OHLCV table |
| `VERDICT` | AI buy/sell/hold probability distribution |
| `RATE` | AI multi-axis rating (valuation/growth/quality/momentum) |
| `HELP` / `?` | Command reference |
| `EXIT` / `QUIT` | Exit the REPL |

*Phase 2: TA, NI, COMPARE, SOURCE — Phase 3: SCREEN, MACRO, WATCH, EXPORT*

---

## Configuration

On first run, Tickr creates:

```text
~/.tickr/config.yaml
```

```yaml
provider_priority:
  - yfinance

groq_api_key: ""

default_timeframe: 1Y
theme: default
```

Set your Groq API key to enable AI analysis:

```bash
export GROQ_API_KEY="your-api-key"
```

AI analysis powers:

- `VERDICT` — AI buy/hold/sell probability distribution
- `RATE` — AI multi-axis fundamental rating
- Narrative analysis
- AI-powered insights in supported screens

The terminal is fully functional without a Groq API key. AI sections show a graceful "unavailable" notice when AI access is not configured.

---

## Provider Plugins

The `providers/base.py` `DataProvider` interface is public. To add a new source:

1. Subclass `DataProvider`
2. Implement `get_info()`, `get_price_history()`, `get_financials()`, `get_news()`, `get_peers()`
3. Register the provider in:

```text
~/.tickr/config.yaml
```

under `provider_priority`.

---

## Requirements

- Python 3.10+
- A modern terminal:
  - **iTerm2** (macOS)
  - **Windows Terminal** (Windows)
  - **GNOME Terminal** / **Kitty** (Linux)
- yfinance
- Rich
- Prompt Toolkit
- Plotext
- Groq

An API key for Groq is required only for AI-powered features.

---

## Roadmap

- **v0.1 (MVP):** EQUITY, DES, FA, GP, HP, VERDICT, RATE
- **v0.2:** TA (technical panel), NI (news + sentiment), COMPARE, multi-provider
- **v0.3:** SCREEN (NL filtering), MACRO, WATCH, EXPORT
- **v0.4:** Full Textual TUI, tabbed panels, community plugins

---

## License

MIT — use freely, contribute openly.
```
