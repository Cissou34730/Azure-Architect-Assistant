"""Unit tests for the scope-detection guardrail in agent.py.

Validates that _is_probably_in_scope, _is_scope_refusal, _is_out_of_scope_request,
and the word-boundary matching correctly distinguish legitimate project requests
from genuinely off-topic messages — without false positives or negatives.
"""

import pytest

from app.agents_system.langgraph.nodes.agent import (
    _is_out_of_scope_request,
    _is_probably_in_scope,
    _is_scope_refusal,
)

# ── In-scope: domain keywords ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "message",
    [
        "update the reliability checklist status for the project",
        "What Azure services should I use for this workload?",
        "Generate a Terraform module for the storage account",
        "Review the architecture diagram",
        "Add a new ADR for the database migration decision",
        "How much will this cost on Azure?",
        "Evaluate the WAF security pillar compliance",
        "Define non-functional requirements for latency",
        "Deploy the app service with CI/CD pipeline",
        "Propose a candidate architecture with AKS and Cosmos DB",
        "Create a mermaid diagram of the data flow",
        "Explain the disaster recovery strategy",
        "What SLA can we guarantee with geo-redundant storage?",
        "Set up VNet peering between the subnets",
        "Analyze authentication flow using Entra ID",
        "Compare PaaS vs IaaS for this workload",
        "Summarize the traceability links",
        "Assess HIPAA compliance requirements",
        "Show me the mind map",
        "List all open questions",
        "Validate the Bicep template",
        "Configure API Management policies",
        "Plan the migration from monolith to microservices",
        "Audit the RBAC role assignments",
        "Optimize the caching layer with Redis",
    ],
    ids=lambda m: m[:50],
)
def test_legitimate_requests_are_in_scope(message: str) -> None:
    assert _is_probably_in_scope(message) is True, f"Should be in-scope: {message}"


# ── In-scope: action verbs without off-topic ──────────────────────────────────


@pytest.mark.parametrize(
    "message",
    [
        "Create a new item for the checklist",
        "Remove this entry and update the list",
        "Generate a summary of what we discussed",
        "Compare the two options and recommend one",
        "Evaluate the current proposal against our constraints",
    ],
    ids=lambda m: m[:50],
)
def test_action_verbs_without_off_topic_are_in_scope(message: str) -> None:
    assert _is_probably_in_scope(message) is True


# ── In-scope: tricky messages that must NOT be blocked ────────────────────────
# These contain words that previously triggered false negatives.


@pytest.mark.parametrize(
    "message",
    [
        # "relationship" between services is legitimate architecture talk
        "Show the relationship between the API gateway and backend services",
        # "travel" as part of "traversal" or data movement
        "How does the request travel from the front door to the backend?",
        # "weather" as a domain name (edge case but should hit action verb)
        "Create an architecture for a weather monitoring IoT platform",
        # "movie" as part of a project domain
        "Design the database schema for our movie streaming project on Azure",
        # Short but contains domain keyword
        "Scale the API",
    ],
    ids=lambda m: m[:50],
)
def test_previously_blocked_legitimate_requests_now_pass(message: str) -> None:
    assert _is_probably_in_scope(message) is True


# ── Off-topic: genuinely irrelevant messages ──────────────────────────────────


@pytest.mark.parametrize(
    "message",
    [
        "tell me a joke about cats",
        "what's the weather today in Paris?",
        "give me a recipe for chocolate cake",
        "what's my horoscope for today?",
        "write me a poem about the sunset",
        "play a game with me",
        "sing me a song",
    ],
    ids=lambda m: m[:50],
)
def test_off_topic_messages_are_not_in_scope(message: str) -> None:
    assert _is_probably_in_scope(message) is False, f"Should be off-topic: {message}"


# ── Substring false-positive protection ───────────────────────────────────────
# These messages contain substrings of keywords but should NOT match.


@pytest.mark.parametrize(
    "message",
    [
        # "cost" inside "Acosta" — no word boundary match
        "Who is Acosta?",
        # No domain keyword, no action verb
        "Hello there",
    ],
    ids=lambda m: m[:50],
)
def test_substring_false_positives_are_prevented(message: str) -> None:
    assert _is_probably_in_scope(message) is False


# ── Scope refusal detection ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("I cannot assist with this topic. My scope is restricted.", True),
        ("This is out-of-scope for my capabilities.", True),
        ("This is out of scope for the project assistant.", True),
        ("Sure, here is the architecture diagram.", False),
        ("", False),
        ("scope is restricted to Azure", True),
    ],
)
def test_scope_refusal_detection(text: str, expected: bool) -> None:
    assert _is_scope_refusal(text) is expected


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_empty_message_is_not_in_scope() -> None:
    assert _is_probably_in_scope("") is False


def test_whitespace_only_not_in_scope() -> None:
    assert _is_probably_in_scope("   ") is False


def test_mixed_case_domain_keyword() -> None:
    assert _is_probably_in_scope("AZURE architecture REVIEW") is True


def test_action_verb_with_single_weak_off_topic_and_long_message() -> None:
    """A long message with an action verb and only 1 off-topic hint should pass."""
    msg = "Create a story about how our microservices architecture handles failover scenarios in production"
    assert _is_probably_in_scope(msg) is True


def test_pure_off_topic_even_with_action_verb() -> None:
    """A short message with action verb + off-topic should be blocked."""
    msg = "tell me a joke"
    assert _is_probably_in_scope(msg) is False


# ═══════════════════════════════════════════════════════════════════════════════
# Pre-filter: _is_out_of_scope_request — blocks before the LLM runs
# ═══════════════════════════════════════════════════════════════════════════════


# ── Should be BLOCKED (out of scope) ──────────────────────────────────────────


@pytest.mark.parametrize(
    "message",
    [
        # Generic Python scripting
        "Write me a Python script that sorts a list of numbers",
        "Create a Python program to parse CSV files",
        "Build a Python script to scrape websites",
        "Make a Python function to calculate fibonacci",
        # Generic coding in other languages
        "Write a JavaScript program to reverse a string",
        "Code a Java class that implements binary search",
        "Create a C# program to read a file",
        # Algorithm / homework
        "Implement bubble sort in Python",
        "Write a binary search algorithm",
        "Code a linked list implementation",
        "Implement dijkstra's algorithm",
        # How-to coding (no project context)
        "How do I sort a list in Python?",
        "How to parse JSON in JavaScript?",
        "How can I read a file in Java?",
        # Entertainment / personal
        "Tell me a joke about programmers",
        "What's the weather today?",
        "Write me a poem about clouds",
        "Play a game with me",
        "What's my horoscope for today?",
        "Sing me a song about coding",
        # Translation
        "Translate this paragraph to French",
        "Translate 'hello world' into Japanese",
        # Math homework
        "Solve this equation: 2x + 5 = 15",
        "Calculate the integral of x^2",
        # Generic scripts
        "Write me a script to send emails",
        "Create a bot to tweet automatically",
        "Make a calculator program in Python",
        "Build a todo app in JavaScript",
    ],
    ids=lambda m: m[:50],
)
def test_prefilter_blocks_out_of_scope_requests(message: str) -> None:
    assert _is_out_of_scope_request(message) is True, f"Should be blocked: {message}"


# ── Should NOT be blocked (in scope — has domain signal) ──────────────────────


@pytest.mark.parametrize(
    "message",
    [
        # Contains Azure/architecture keywords → always pass
        "Write a Python script to deploy to Azure",
        "Create a Terraform module for the storage account",
        "Build a Bicep template for our AKS cluster",
        "Write a script to test our Azure API endpoint",
        "Implement the deployment pipeline for our architecture",
        "Create a Python function to query Cosmos DB",
        # Architecture / project work
        "Design the microservices architecture",
        "Review the WAF security checklist",
        "Generate the mermaid diagram",
        "Update the reliability requirements",
        "Propose a candidate architecture with AKS",
        "How much will the infrastructure cost?",
        "Analyze the SLA for our multi-region setup",
        "What's the best approach for disaster recovery?",
        "Create an ADR for choosing between SQL and Cosmos",
        "Validate the Bicep template against WAF",
        # Edge: mentions a language but in project context
        "Write a Python script to validate our Bicep templates",
        "Create a PowerShell script for Azure deployment",
        "Build a CLI tool to export our architecture state",
        # Short but has domain keyword
        "Scale the API",
        "Deploy the app",
        "Check the checklist",
        "Review VNet peering",
        # Previously tricky messages
        "Show the relationship between the API gateway and backend",
        "How does the request travel from front door to backend?",
        "Create an architecture for a weather monitoring IoT platform on Azure",
    ],
    ids=lambda m: m[:50],
)
def test_prefilter_allows_in_scope_requests(message: str) -> None:
    assert _is_out_of_scope_request(message) is False, f"Should NOT be blocked: {message}"


# ── Edge cases for pre-filter ─────────────────────────────────────────────────


def test_prefilter_empty_message_not_blocked() -> None:
    """Empty message should not be blocked — let the agent handle it."""
    assert _is_out_of_scope_request("") is False


def test_prefilter_ambiguous_message_not_blocked() -> None:
    """Ambiguous message with no clear pattern should pass through to agent."""
    assert _is_out_of_scope_request("Can you help me with something?") is False


def test_prefilter_generic_greeting_not_blocked() -> None:
    """Simple greetings should pass — the agent can handle them contextually."""
    assert _is_out_of_scope_request("Hello, how are you?") is False


def test_prefilter_mixed_scope_favors_in_scope() -> None:
    """A message mentioning both a generic task and Azure should be allowed."""
    msg = "Write a python script that sorts our Azure resource list by cost"
    assert _is_out_of_scope_request(msg) is False
