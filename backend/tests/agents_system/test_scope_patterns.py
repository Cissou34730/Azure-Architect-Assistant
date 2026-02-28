"""Tests for scope_patterns config module.

Verifies all pattern lists are non-empty, compile correctly, and match expected inputs.
"""

import re

from app.agents_system.config.scope_patterns import (
    ACTION_PATTERNS,
    GENERIC_REQUEST_PATTERNS,
    IN_SCOPE_PATTERNS,
    MIN_WORDS_FOR_AMBIGUOUS_SCOPE,
    OFF_TOPIC_PATTERNS,
    OUT_OF_SCOPE_REDIRECT,
    PILLAR_ALIASES,
    SCOPE_REFUSAL_PATTERNS,
)


class TestPatternListsNonEmpty:
    def test_pillar_aliases_non_empty(self):
        assert len(PILLAR_ALIASES) > 0

    def test_scope_refusal_patterns_non_empty(self):
        assert len(SCOPE_REFUSAL_PATTERNS) > 0

    def test_in_scope_patterns_non_empty(self):
        assert len(IN_SCOPE_PATTERNS) > 0

    def test_action_patterns_non_empty(self):
        assert len(ACTION_PATTERNS) > 0

    def test_off_topic_patterns_non_empty(self):
        assert len(OFF_TOPIC_PATTERNS) > 0

    def test_generic_request_patterns_non_empty(self):
        assert len(GENERIC_REQUEST_PATTERNS) > 0

    def test_out_of_scope_redirect_non_empty(self):
        assert len(OUT_OF_SCOPE_REDIRECT) > 0

    def test_min_words_constant(self):
        assert MIN_WORDS_FOR_AMBIGUOUS_SCOPE == 8


class TestPatternsCompile:
    def test_all_scope_refusal_patterns_are_compiled(self):
        for pat in SCOPE_REFUSAL_PATTERNS:
            assert isinstance(pat, re.Pattern)

    def test_all_in_scope_patterns_are_compiled(self):
        for pat in IN_SCOPE_PATTERNS:
            assert isinstance(pat, re.Pattern)

    def test_all_action_patterns_are_compiled(self):
        for pat in ACTION_PATTERNS:
            assert isinstance(pat, re.Pattern)

    def test_all_off_topic_patterns_are_compiled(self):
        for pat in OFF_TOPIC_PATTERNS:
            assert isinstance(pat, re.Pattern)

    def test_all_generic_request_patterns_are_compiled(self):
        for pat in GENERIC_REQUEST_PATTERNS:
            assert isinstance(pat, re.Pattern)


class TestRepresentativeMatches:
    def test_azure_matches_in_scope(self):
        assert any(pat.search("Deploy to Azure") for pat in IN_SCOPE_PATTERNS)

    def test_waf_matches_in_scope(self):
        assert any(pat.search("WAF assessment needed") for pat in IN_SCOPE_PATTERNS)

    def test_kubernetes_matches_in_scope(self):
        assert any(pat.search("Set up kubernetes cluster") for pat in IN_SCOPE_PATTERNS)

    def test_joke_matches_off_topic(self):
        assert any(pat.search("tell me a joke") for pat in OFF_TOPIC_PATTERNS)

    def test_weather_matches_off_topic(self):
        assert any(pat.search("weather forecast for today") for pat in OFF_TOPIC_PATTERNS)

    def test_create_matches_action(self):
        assert any(pat.search("create a new diagram") for pat in ACTION_PATTERNS)

    def test_refusal_detected(self):
        assert any(pat.search("I cannot assist with this topic") for pat in SCOPE_REFUSAL_PATTERNS)

    def test_out_of_scope_detected(self):
        assert any(pat.search("This is out-of-scope") for pat in SCOPE_REFUSAL_PATTERNS)

    def test_generic_python_script_matches(self):
        assert any(
            pat.search("write me a python script to sort files")
            for pat in GENERIC_REQUEST_PATTERNS
        )

    def test_pillar_reliability_aliases(self):
        aliases = PILLAR_ALIASES["Reliability"]
        assert "reliability" in aliases
        assert "resilience" in aliases

    def test_pillar_cost_optimization_aliases(self):
        aliases = PILLAR_ALIASES["Cost Optimization"]
        assert "cost" in aliases
        assert "finops" in aliases
