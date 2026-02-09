"""Canonical Azure Well-Architected checklist template definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class WafTemplateDefinition:
    """Static descriptor for one canonical WAF pillar checklist template."""

    slug: str
    pillar: str
    title: str
    source_url: str


WAF_PILLAR_TEMPLATES: tuple[WafTemplateDefinition, ...] = (
    WafTemplateDefinition(
        slug="azure-waf-reliability-v1",
        pillar="Reliability",
        title="Azure WAF Reliability Checklist",
        source_url="https://learn.microsoft.com/azure/well-architected/reliability/checklist",
    ),
    WafTemplateDefinition(
        slug="azure-waf-security-v1",
        pillar="Security",
        title="Azure WAF Security Checklist",
        source_url="https://learn.microsoft.com/azure/well-architected/security/checklist",
    ),
    WafTemplateDefinition(
        slug="azure-waf-cost-optimization-v1",
        pillar="Cost Optimization",
        title="Azure WAF Cost Optimization Checklist",
        source_url="https://learn.microsoft.com/azure/well-architected/cost-optimization/checklist",
    ),
    WafTemplateDefinition(
        slug="azure-waf-operational-excellence-v1",
        pillar="Operational Excellence",
        title="Azure WAF Operational Excellence Checklist",
        source_url="https://learn.microsoft.com/azure/well-architected/operational-excellence/checklist",
    ),
    WafTemplateDefinition(
        slug="azure-waf-performance-efficiency-v1",
        pillar="Performance Efficiency",
        title="Azure WAF Performance Efficiency Checklist",
        source_url="https://learn.microsoft.com/azure/well-architected/performance-efficiency/checklist",
    ),
)

LEGACY_WAF_TEMPLATE_SLUGS: tuple[str, ...] = ("azure-waf-v1", "waf-2024")


def canonical_waf_template_slugs() -> list[str]:
    """Return canonical Azure WAF template slugs in pillar order."""
    return [template.slug for template in WAF_PILLAR_TEMPLATES]


def resolve_bootstrap_template_slugs(available_slugs: Iterable[str]) -> list[str]:
    """Choose template slugs to instantiate, preferring canonical 5-pillar templates."""
    available = {slug.strip() for slug in available_slugs if slug and slug.strip()}
    canonical = [slug for slug in canonical_waf_template_slugs() if slug in available]
    if canonical:
        return canonical

    legacy = [slug for slug in LEGACY_WAF_TEMPLATE_SLUGS if slug in available]
    if legacy:
        return legacy

    return sorted(available)
