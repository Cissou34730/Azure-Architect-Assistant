from app.agents_system.checklists.default_templates import (
    canonical_waf_template_slugs,
    resolve_bootstrap_template_slugs,
)


def test_canonical_template_slugs_include_five_pillars() -> None:
    slugs = canonical_waf_template_slugs()
    assert len(slugs) == 5
    assert slugs == [
        "azure-waf-reliability-v1",
        "azure-waf-security-v1",
        "azure-waf-cost-optimization-v1",
        "azure-waf-operational-excellence-v1",
        "azure-waf-performance-efficiency-v1",
    ]


def test_resolve_bootstrap_prefers_canonical_pillars() -> None:
    available = set(canonical_waf_template_slugs() + ["azure-waf-v1", "waf-2024"])
    resolved = resolve_bootstrap_template_slugs(available)
    assert resolved == canonical_waf_template_slugs()


def test_resolve_bootstrap_falls_back_to_legacy() -> None:
    resolved = resolve_bootstrap_template_slugs(["waf-2024", "azure-waf-v1"])
    assert resolved == ["azure-waf-v1", "waf-2024"]
