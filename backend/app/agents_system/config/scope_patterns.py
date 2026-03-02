"""Scope-detection pattern constants for the agent scope guard.

Extracted from scope_guard.py to keep patterns configurable and auditable.
"""

import re

MIN_WORDS_FOR_AMBIGUOUS_SCOPE = 8

# ---------------------------------------------------------------------------
# Pillar / refusal aliases
# ---------------------------------------------------------------------------

PILLAR_ALIASES: dict[str, tuple[str, ...]] = {
    "Reliability": ("reliability", "reliabilty", "reliablity", "resilience", "resiliency"),
    "Security": ("security",),
    "Cost Optimization": ("cost optimization", "cost", "finops"),
    "Operational Excellence": ("operational excellence", "operations"),
    "Performance Efficiency": ("performance efficiency", "performance"),
}

SCOPE_REFUSAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"i cannot assist with this topic", re.IGNORECASE),
    re.compile(r"scope is restricted", re.IGNORECASE),
    re.compile(r"out[-\s]?of[-\s]?scope", re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Scope-detection vocabulary
# ---------------------------------------------------------------------------
# All patterns use word-boundary matching (\b) compiled once at import time
# to avoid substring false-positives (e.g. "cost" inside "Acosta").
# ---------------------------------------------------------------------------

# Domain keywords — a hit on any of these is a strong in-scope signal.
IN_SCOPE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
    for kw in (
        # Core domain
        "azure",
        "architecture",
        "architect",
        "project",
        "checklist",
        "waf",
        "well-architected",
        "well architected",
        # WAF pillars
        "reliability",
        "security",
        "cost optimization",
        "cost",
        "operational excellence",
        "performance efficiency",
        # Artifacts / concepts
        "adr",
        "decision record",
        "diagram",
        "mermaid",
        "c4 model",
        "iac",
        "terraform",
        "bicep",
        "arm template",
        "nfr",
        "non-functional",
        "validation",
        "finding",
        "traceability",
        "candidate architecture",
        "mind map",
        "requirements",
        "requirement",
        "assumptions",
        "assumption",
        "open questions",
        "clarification",
        "mcp",
        # Azure services & infra concepts
        "vm",
        "virtual machine",
        "container",
        "kubernetes",
        "aks",
        "app service",
        "function app",
        "storage account",
        "cosmos",
        "sql database",
        "sql server",
        "blob",
        "redis",
        "service bus",
        "event hub",
        "event grid",
        "api management",
        "apim",
        "front door",
        "application gateway",
        "load balancer",
        "vpn",
        "vnet",
        "subnet",
        "nsg",
        "firewall",
        "bastion",
        "key vault",
        "managed identity",
        "rbac",
        "entra",
        "active directory",
        "monitor",
        "log analytics",
        "app insights",
        "application insights",
        # Architecture / engineering terms
        "microservice",
        "monolith",
        "saas",
        "paas",
        "iaas",
        "serverless",
        "multi-tenant",
        "single-tenant",
        "deployment",
        "deploy",
        "ci/cd",
        "pipeline",
        "migration",
        "migrate",
        "scalability",
        "scale",
        "scaling",
        "latency",
        "throughput",
        "availability",
        "disaster recovery",
        "failover",
        "backup",
        "sla",
        "rto",
        "rpo",
        "region",
        "zone",
        "geo-redundant",
        "compliance",
        "hipaa",
        "gdpr",
        "soc 2",
        "pci dss",
        "iso 27001",
        "encryption",
        "tls",
        "ssl",
        "oauth",
        "authentication",
        "authorization",
        "endpoint",
        "api",
        "rest",
        "graphql",
        "grpc",
        "web app",
        "database",
        "caching",
        "cdn",
        "dns",
        "domain",
        "certificate",
        "tco",
        "budget",
        "pricing",
        "estimate",
        "infrastructure",
        "devops",
        "observability",
        "monitoring",
        "alerting",
        "logging",
        "telemetry",
        "data flow",
        "workflow",
        "integration",
        "queue",
        "pub/sub",
        "networking",
        "topology",
        "tier",
    )
)

# Action verbs — imply the user wants to *do* something to the project.
ACTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(verb)}\b", re.IGNORECASE)
    for verb in (
        "create",
        "update",
        "delete",
        "remove",
        "add",
        "set",
        "mark",
        "uncheck",
        "check",
        "generate",
        "analyze",
        "analyse",
        "validate",
        "review",
        "propose",
        "suggest",
        "compare",
        "evaluate",
        "assess",
        "refactor",
        "redesign",
        "implement",
        "plan",
        "define",
        "document",
        "export",
        "summarize",
        "list",
        "show",
        "explain",
        "describe",
        "recommend",
        "improve",
        "optimize",
        "configure",
        "provision",
        "audit",
    )
)

# Off-topic phrases — must be *phrases at word boundaries* to avoid false
# positives (e.g. "travel" matching "traversal").  The guardrail only blocks
# retry when *multiple* off-topic signals are present AND zero in-scope
# signals exist.
OFF_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
    for phrase in (
        "tell me a joke",
        "joke",
        "weather forecast",
        "weather today",
        "movie recommendation",
        "movie review",
        "sports score",
        "sports news",
        "political opinion",
        "politics",
        "dating advice",
        "love life",
        "recipe",
        "cook",
        "horoscope",
        "astrology",
        "song lyrics",
        "play a game",
        "trivia",
        "riddle",
        "poem",
        "story",
        "fiction",
    )
)

# ---------------------------------------------------------------------------
# Pre-filter: detect requests that are clearly outside the assistant's role
# ---------------------------------------------------------------------------
GENERIC_REQUEST_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        # Generic coding tasks
        r"\b(?:write|create|build|make|code|implement|develop)\b.{0,30}\b(?:python|javascript|typescript|java|c\+\+|c#|ruby|go|rust|php|perl|bash|shell|powershell)\s+(?:script|program|code|function|class|app|application|bot|tool|utility|game)\b",
        r"\b(?:write|create|build|make|code|implement)\b.{0,20}\b(?:script|program|code|function|class)\b.{0,30}\b(?:that|which|to)\b.{0,40}\b(?:sort|parse|convert|calculate|count|sum|multiply|divide|reverse|filter|merge|split|extract|download|scrape|crawl|fetch|send|email|sms|tweet)\b",
        r"\b(?:write|create|build|make)\b.{0,20}\b(?:a|an|the|me a|me an)\b\s+\b(?:script|program|bot|game|calculator|converter|scraper|crawler|chatbot|todo|to-do|cli|gui|todo app|to-do app)\b",
        # Generic app/tool building with language specified
        r"\b(?:write|create|build|make|develop)\b.{0,30}\b(?:app|application|tool|utility|website|web app|desktop app|mobile app)\b.{0,20}\b(?:in|using|with)\b\s+\b(?:python|javascript|typescript|java|c\+\+|c#|ruby|go|rust|react|vue|angular|svelte|next\.?js|flask|django|express|node)\b",
        # Algorithm / data-structure homework
        r"\b(?:implement|write|code)\b.{0,20}\b(?:bubble sort|quick sort|merge sort|insertion sort|binary search|linked list|binary tree|hash table|heap|stack|queue|graph traversal|bfs|dfs|dijkstra|fibonacci|factorial|palindrome|anagram|permutation)\b",
        # Generic how-to coding questions with no project context
        r"\bhow (?:do i|to|can i)\b.{0,20}\b(?:sort a list|reverse a string|read a file|write a file|open a file|parse json|parse xml|parse csv|make a request|http request|loop through|iterate over)\b.{0,20}\bin (?:python|javascript|java|c\+\+|c#|ruby|go|rust)\b",
        # Clearly personal / entertainment
        r"\b(?:write|tell|give|sing|compose)\b.{0,15}\b(?:me|us)\b.{0,15}\b(?:a joke|a poem|a song|a story|a limerick|a haiku|a riddle)\b",
        r"\bwhat(?:'s| is)\b.{0,15}\b(?:the weather|my horoscope|the score|the news)\b",
        r"\b(?:play|let's play)\b.{0,10}\b(?:a game|trivia|guess|rock paper|tic tac)\b",
        # Translation / language tasks
        r"\btranslate\b.{0,20}\b(?:to|into|from)\b.{0,20}\b(?:french|spanish|german|italian|portuguese|chinese|japanese|korean|arabic|hindi|russian)\b",
        # Math homework
        r"\b(?:solve|calculate|compute|evaluate|simplify|factor|derive|integrate)\b.{0,20}\b(?:equation|integral|derivative|matrix|polynomial|expression|limit)\b",
    )
)

OUT_OF_SCOPE_REDIRECT = (
    "I'm the Azure Architect Assistant — I help with Azure architecture design, "
    "WAF assessments, requirements analysis, ADRs, IaC generation, and cost estimation "
    "for your project.\n\n"
    "Your request doesn't seem related to the project's architecture work. "
    "Could you rephrase it in the context of your project, or ask me something about "
    "your Azure architecture instead?"
)
