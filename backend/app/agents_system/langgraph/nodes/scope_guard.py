"""Scope-guard helpers for the agent execution node.

Detects out-of-scope requests and over-refusal recovery.
"""


from ...config.scope_patterns import (
    ACTION_PATTERNS,
    GENERIC_REQUEST_PATTERNS,
    IN_SCOPE_PATTERNS,
    MIN_WORDS_FOR_AMBIGUOUS_SCOPE,
    OFF_TOPIC_PATTERNS,
    OUT_OF_SCOPE_REDIRECT,
    PILLAR_ALIASES,
    SCOPE_REFUSAL_PATTERNS,
)

_MIN_WORDS_FOR_AMBIGUOUS_SCOPE = MIN_WORDS_FOR_AMBIGUOUS_SCOPE
_PILLAR_ALIASES = PILLAR_ALIASES
_SCOPE_REFUSAL_PATTERNS = SCOPE_REFUSAL_PATTERNS
_IN_SCOPE_PATTERNS = IN_SCOPE_PATTERNS
_ACTION_PATTERNS = ACTION_PATTERNS
_OFF_TOPIC_PATTERNS = OFF_TOPIC_PATTERNS
_GENERIC_REQUEST_PATTERNS = GENERIC_REQUEST_PATTERNS
_OUT_OF_SCOPE_REDIRECT = OUT_OF_SCOPE_REDIRECT


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_out_of_scope_request(user_message: str) -> bool:
    """Return True if the request is clearly unrelated to the project.

    The check is deliberately conservative (high precision): it only fires
    when a generic-request pattern matches AND no domain keyword is present.
    """
    if any(pat.search(user_message) for pat in _IN_SCOPE_PATTERNS):
        return False

    if any(pat.search(user_message) for pat in _GENERIC_REQUEST_PATTERNS):
        return True

    off_topic_hits = sum(1 for pat in _OFF_TOPIC_PATTERNS if pat.search(user_message))
    return off_topic_hits >= 1


def is_scope_refusal(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(pattern.search(lowered) for pattern in _SCOPE_REFUSAL_PATTERNS)


def is_probably_in_scope(user_message: str) -> bool:
    """Determine whether *user_message* is likely an in-scope project request."""
    if any(pat.search(user_message) for pat in _IN_SCOPE_PATTERNS):
        return True

    has_action = any(pat.search(user_message) for pat in _ACTION_PATTERNS)
    off_topic_hits = sum(1 for pat in _OFF_TOPIC_PATTERNS if pat.search(user_message))

    if has_action and off_topic_hits == 0:
        return True

    return has_action and off_topic_hits == 1 and len(user_message.split()) >= _MIN_WORDS_FOR_AMBIGUOUS_SCOPE


def extract_target_pillar(user_message: str) -> str | None:
    lowered = user_message.lower()
    for pillar, aliases in _PILLAR_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return pillar
    return None
