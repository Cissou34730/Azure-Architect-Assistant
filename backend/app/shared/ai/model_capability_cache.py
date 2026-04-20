"""Per-model cache of unsupported API parameters.

The OpenAI family of APIs does **not** publish per-model parameter constraints.
Instead, rejected parameters are discovered at runtime: models return a
``BadRequestError`` whose structured ``param`` / ``code`` fields identify the
offending parameter.  This module captures those learnings in a process-scoped
cache so that:

* the first call to a new model may retry once (learning event),
* all subsequent calls proactively omit the known-unsupported parameters.

Cache key is ``(provider, model_id)`` because the same model name served by
different providers may have different parameter support.

Thread-safety: writes acquire a lock and produce **immutable** ``frozenset``
snapshots; reads never lock.
"""

from __future__ import annotations

import logging
import re
from threading import Lock

logger = logging.getLogger(__name__)

# Last-resort regex for environments where structured error fields are absent.
# Matches patterns like  'temperature' does not support …
_UNSUPPORTED_PARAM_RE = re.compile(
    r"'([a-z_]+)'[^']*(?:does not support|is not supported|unsupported)",
    re.IGNORECASE,
)


class ModelCapabilityCache:
    """Process-scoped, thread-safe cache of parameters that models reject."""

    _instance: ModelCapabilityCache | None = None
    _lock = Lock()

    def __init__(self) -> None:
        # (provider, model_id) → frozenset of unsupported param names
        self._unsupported: dict[tuple[str, str], frozenset[str]] = {}

    # ── singleton ─────────────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> ModelCapabilityCache:
        """Return the global singleton, creating it on first access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton — useful for tests."""
        with cls._lock:
            cls._instance = None

    # ── queries ───────────────────────────────────────────────────────────

    def is_supported(self, provider: str, model: str, param: str) -> bool:
        """Return ``True`` unless *param* was previously marked unsupported."""
        return param not in self._unsupported.get((provider, model), frozenset())

    def get_unsupported(self, provider: str, model: str) -> frozenset[str]:
        """Return the (possibly empty) set of unsupported param names."""
        return self._unsupported.get((provider, model), frozenset())

    # ── mutations ─────────────────────────────────────────────────────────

    def mark_unsupported(self, provider: str, model: str, param: str) -> None:
        """Record that *(provider, model)* rejects *param*."""
        key = (provider, model)
        with self._lock:
            existing = self._unsupported.get(key, frozenset())
            self._unsupported[key] = existing | {param}
        logger.info(
            "ModelCapabilityCache: %s/%s rejects parameter '%s'",
            provider,
            model,
            param,
        )

    # ── error parsing ─────────────────────────────────────────────────────

    @staticmethod
    def extract_rejected_param(error: Exception) -> str | None:
        """Extract the rejected parameter name from an API error.

        Prefers the structured ``param`` / ``code`` attributes provided by the
        OpenAI Python SDK, falling back to a regex over the error message.
        """
        # 1. Structured fields (openai.BadRequestError)
        param = getattr(error, "param", None)
        code = getattr(error, "code", None)
        if isinstance(param, str) and code == "unsupported_value":
            return param

        # 2. Body dict (belt-and-suspenders)
        body = getattr(error, "body", None)
        if isinstance(body, dict):
            inner = body.get("error", {})
            if isinstance(inner, dict):
                p = inner.get("param")
                c = inner.get("code")
                if isinstance(p, str) and c == "unsupported_value":
                    return p

        # 3. Regex fallback
        match = _UNSUPPORTED_PARAM_RE.search(str(error))
        return match.group(1) if match else None
