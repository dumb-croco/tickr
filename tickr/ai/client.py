"""
ai/client.py — Groq AI client wrapper.

Features:
  - Graceful degradation when the Groq SDK or API key is unavailable
  - SQLite-backed AI response caching
  - Explicit JSON output instructions
  - Robust score and choice normalization
  - Diagnostics for API and client errors
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tickr.cache.store import CacheStore

try:
    from groq import Groq

    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
    Groq = None  # type: ignore[assignment,misc]


class GroqClient:
    """Thin wrapper around Groq with caching and error handling."""

    def __init__(
        self,
        api_key: str,
        cache: "CacheStore",
    ) -> None:
        self.api_key = api_key
        self.cache = cache
        self._available = _GROQ_AVAILABLE and bool(api_key)
        self._client: Optional[Any] = None

    @property
    def available(self) -> bool:
        """Whether the SDK is installed and a non-empty API key exists."""
        return self._available

    def call(
        self,
        state: dict[str, Any],
        questions: dict[str, Any],
        ticker: str,
        timeframe: str,
        cache_tag: str,
    ) -> Optional[dict[str, Any]]:
        """Call Groq, normalize its response, and cache useful results."""

        if not self._available:
            return None

        # Include the questions and a version marker in the fingerprint.
        # This prevents older, incomplete cached responses from being reused.
        fingerprint = self._fingerprint(
            state,
            f"client-v2:{cache_tag}",
            questions,
        )

        cache_key = f"{ticker}:{cache_tag}"

        try:
            cached = self.cache.get_ai(
                cache_key,
                timeframe,
                fingerprint,
            )

            if cached is not None:
                # Do not reuse empty or malformed cached responses.
                if self._has_results(cached):
                    return cached

            result = self._do_call(state, questions)

            # Never cache an empty response. It could otherwise make a
            # temporary model-output problem persist for the cache TTL.
            if result is not None and self._has_results(result):
                self.cache.set_ai(
                    cache_key,
                    timeframe,
                    fingerprint,
                    result,
                )

            return result

        except Exception as exc:  # noqa: BLE001
            print(
                f"[Groq] Client error: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            return None

    def _do_call(
        self,
        state: dict[str, Any],
        questions: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Execute the API request and normalize the returned JSON."""

        if not _GROQ_AVAILABLE:
            return None

        try:
            if self._client is None:
                self._client = Groq(api_key=self.api_key)

            prompt = self._build_prompt(state, questions)

            response = self._client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an equity research analysis engine. "
                            "Analyze only the financial data supplied by "
                            "the user. Never invent missing financial data. "
                            "Follow the requested output schema exactly. "
                            "Return a valid JSON object, with numeric values "
                            "for every requested score. Do not omit requested "
                            "fields merely because some input data is missing."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_completion_tokens=2048,
            )

            if not response.choices:
                print("[Groq] The API returned no choices.", file=sys.stderr)
                return None

            content = response.choices[0].message.content

            if not content:
                print(
                    "[Groq] The API returned an empty message.",
                    file=sys.stderr,
                )
                return None

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                print(
                    f"[Groq] Invalid JSON response: {exc}",
                    file=sys.stderr,
                )
                print(f"[Groq] Response content: {content[:500]}", file=sys.stderr)
                return None

            if not isinstance(parsed, dict):
                print(
                    "[Groq] Expected a JSON object, received "
                    f"{type(parsed).__name__}.",
                    file=sys.stderr,
                )
                return None

            normalized = self._normalize_response(parsed, questions)

            if not self._has_results(normalized):
                print(
                    "[Groq] Response contained no usable requested scores "
                    "or choices.",
                    file=sys.stderr,
                )
                print(
                    "[Groq] Returned JSON keys: "
                    f"{list(parsed.keys())}",
                    file=sys.stderr,
                )

            return normalized

        except Exception as exc:  # noqa: BLE001
            print(
                f"[Groq] API error: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            return None

    @staticmethod
    def _build_prompt(
        state: dict[str, Any],
        questions: dict[str, Any],
    ) -> str:
        """Build an explicit prompt that specifies the expected JSON shape."""

        score_keys = list(questions.get("scores", {}).keys())
        choice_keys = list(questions.get("choices", {}).keys())

        schema: dict[str, Any] = {}

        if score_keys:
            schema["scores"] = {
                key: 0.5 for key in score_keys
            }

        if choice_keys:
            schema["choices"] = {
                key: {
                    "choice": "example choice",
                    "confidence": 0.5,
                }
                for key in choice_keys
            }

        return (
            "Analyze the supplied equity research data.\n\n"
            "RULES:\n"
            "1. Use only the supplied data. Do not invent facts.\n"
            "2. Follow the requested output keys exactly.\n"
            "3. Every requested score must be a JSON number, not an object "
            "or explanatory string.\n"
            "4. For probability scores, use values between 0 and 1.\n"
            "5. Include every requested score key.\n"
            "6. If data is incomplete, make a cautious estimate using "
            "available evidence rather than omitting required keys. "
            "Do not claim unsupported facts.\n"
            "7. Return only a valid JSON object. Do not use Markdown.\n\n"
            "EXPECTED JSON SHAPE:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "FINANCIAL STATE:\n"
            f"{json.dumps(state, indent=2, default=str)}\n\n"
            "REQUESTED OUTPUT DEFINITIONS:\n"
            f"{json.dumps(questions, indent=2, default=str)}\n\n"
            "Return the completed JSON object using the exact keys shown "
            "in EXPECTED JSON SHAPE."
        )

    @classmethod
    def _normalize_response(
        cls,
        response: dict[str, Any],
        questions: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize supported response shapes into Tickr's data format."""

        result: dict[str, Any] = {
            "scores": {},
            "choices": {},
        }

        raw_scores = response.get("scores", {})
        if not isinstance(raw_scores, dict):
            raw_scores = {}

        raw_choices = response.get("choices", {})
        if not isinstance(raw_choices, dict):
            raw_choices = {}

        requested_scores = questions.get("scores", {})
        if not isinstance(requested_scores, dict):
            requested_scores = {}

        requested_choices = questions.get("choices", {})
        if not isinstance(requested_choices, dict):
            requested_choices = {}

        # Normalize the exact requested score keys first. Search the entire
        # response to support both {"scores": {...}} and root-level scores.
        for key in requested_scores:
            found, value = cls._find_value(response, key)

            if not found:
                found, value = cls._find_value(raw_scores, key)

            if found:
                number = cls._to_float(value)
                if number is not None:
                    result["scores"][key] = number

        # Preserve additional numeric scores returned by the model.
        for key, value in raw_scores.items():
            if key in result["scores"]:
                continue

            number = cls._to_float(value)
            if number is not None:
                result["scores"][key] = number

        # Handle requested choice fields.
        for key in requested_choices:
            found, value = cls._find_value(response, key)

            if not found:
                found, value = cls._find_value(raw_choices, key)

            if found:
                choice = cls._to_choice(value)
                if choice is not None:
                    result["choices"][key] = choice

        # Preserve additional choice fields.
        for key, value in raw_choices.items():
            if key in result["choices"]:
                continue

            choice = cls._to_choice(value)
            if choice is not None:
                result["choices"][key] = choice

        return result

    @staticmethod
    def _normalize_key(value: Any) -> str:
        """Normalize a key for matching despite case and punctuation."""
        return re.sub(r"[^a-z0-9]", "", str(value).lower())

    @classmethod
    def _find_value(
        cls,
        data: Any,
        target: str,
    ) -> tuple[bool, Any]:
        """Find a requested key in nested JSON, including common aliases."""

        target_key = cls._normalize_key(target)

        aliases = {
            "buyprobability": {"buy", "buyprob", "buyscore"},
            "holdprobability": {"hold", "holdprob", "holdscore"},
            "sellprobability": {"sell", "sellprob", "sellscore"},
        }

        accepted = {target_key}
        accepted.update(aliases.get(target_key, set()))

        def search(node: Any) -> tuple[bool, Any]:
            if isinstance(node, dict):
                # Prefer an exact key match.
                for key, value in node.items():
                    if cls._normalize_key(key) in accepted:
                        return True, value

                # Then search nested objects.
                for value in node.values():
                    found, result = search(value)
                    if found:
                        return True, result

            elif isinstance(node, list):
                for value in node:
                    found, result = search(value)
                    if found:
                        return True, result

            return False, None

        return search(data)

    @classmethod
    def _to_float(cls, value: Any) -> Optional[float]:
        """Extract a numeric value from a scalar or common nested structure."""

        if isinstance(value, bool) or value is None:
            return None

        if isinstance(value, dict):
            for key in (
                "value",
                "score",
                "probability",
                "estimate",
                "result",
                "answer",
            ):
                if key in value:
                    number = cls._to_float(value[key])
                    if number is not None:
                        return number
            return None

        if isinstance(value, str):
            value = value.strip().removesuffix("%").strip()

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _to_choice(cls, value: Any) -> Optional[dict[str, Any]]:
        """Convert a choice value into Tickr's choice/confidence format."""

        if isinstance(value, dict):
            choice = value.get(
                "choice",
                value.get("value", value.get("answer", "")),
            )
            confidence = cls._to_float(
                value.get("confidence", 0.0)
            )
            return {
                "choice": str(choice),
                "confidence": confidence if confidence is not None else 0.0,
            }

        if value is None:
            return None

        return {
            "choice": str(value),
            "confidence": 1.0,
        }

    @staticmethod
    def _has_results(result: Any) -> bool:
        """Return True if a normalized response contains usable output."""

        if not isinstance(result, dict):
            return False

        scores = result.get("scores", {})
        choices = result.get("choices", {})

        return (
            isinstance(scores, dict)
            and bool(scores)
        ) or (
            isinstance(choices, dict)
            and bool(choices)
        )

    @staticmethod
    def _fingerprint(
        state: dict[str, Any],
        tag: str,
        questions: Optional[dict[str, Any]] = None,
    ) -> str:
        """Hash the state, request schema, and client version for caching."""

        payload = {
            "state": state,
            "tag": tag,
            "questions": questions or {},
        }

        raw = json.dumps(
            payload,
            sort_keys=True,
            default=str,
        )

        return hashlib.sha256(raw.encode()).hexdigest()[:12]
