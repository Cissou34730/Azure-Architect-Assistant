"""Briefing generator for persisted pending change sets.

P6: Generate a Final Briefing From Pending Changes.

Converts a ``PendingChangeSetContract`` into a decision-quality Architect
Briefing that is injected into the agent response when the LLM output is
only a thin persistence receipt.
"""

from __future__ import annotations

from typing import Any

from app.features.projects.contracts import ArtifactDraftType, PendingChangeSetContract


class PendingChangeBriefingService:
    """Generate a stage-aware Architect Briefing from a pending change set."""

    def generate_briefing(self, pending_change_set: PendingChangeSetContract) -> str:
        """Return a rich narrative briefing for the given change set.

        Dispatches to a stage-specific formatter.  Falls back to a generic
        summary for unknown stages or empty change sets.
        """
        stage = (pending_change_set.stage or "").lower().strip()

        drafts = pending_change_set.artifact_drafts or []

        handlers: dict[str, Any] = {
            "propose_candidate": self._briefing_propose_candidate,
            "pricing": self._briefing_pricing,
            "iac": self._briefing_iac,
            "validate": self._briefing_validate,
            "clarify": self._briefing_clarify,
        }

        handler = handlers.get(stage)
        if handler is None:
            return self._briefing_generic(pending_change_set)

        return handler(pending_change_set, drafts)

    # ------------------------------------------------------------------
    # Stage-specific formatters
    # ------------------------------------------------------------------

    def _briefing_propose_candidate(
        self,
        change_set: PendingChangeSetContract,
        drafts: list[Any],
    ) -> str:
        candidate_draft = _first_draft_by_type(drafts, ArtifactDraftType.CANDIDATE_ARCHITECTURE)
        content: dict[str, Any] = candidate_draft.content if candidate_draft else {}

        title = content.get("title") or change_set.bundle_summary or "Architecture Candidate"
        summary = content.get("summary") or ""
        components: list[Any] = content.get("components") or []
        tradeoffs: list[Any] = content.get("tradeoffs") or []
        risks: list[Any] = content.get("risks") or []
        waf_mapping: dict[str, Any] = content.get("wafMapping") or content.get("waf_mapping") or {}

        lines: list[str] = [
            f"## Architect Briefing — {title}",
            "",
        ]

        if summary:
            lines += [f"**Recommendation:** {summary}", ""]

        if components:
            lines.append("**Key Components:**")
            for comp in components[:8]:
                if isinstance(comp, dict):
                    name = comp.get("name") or comp.get("service") or str(comp)
                    role = comp.get("role") or comp.get("description") or ""
                    lines.append(f"- **{name}**" + (f": {role}" if role else ""))
                else:
                    lines.append(f"- {comp}")
            lines.append("")

        if tradeoffs:
            lines.append("**Top Trade-offs Accepted:**")
            for t in tradeoffs[:3]:
                lines.append(f"- {t}")
            lines.append("")

        if waf_mapping:
            lines.append("**WAF Pillar Highlights:**")
            for pillar, coverage in list(waf_mapping.items())[:5]:
                lines.append(f"- *{pillar}*: {coverage}")
            lines.append("")

        if risks:
            lines.append("**Top Risks & Mitigations:**")
            for risk in risks[:3]:
                if isinstance(risk, dict):
                    risk_text = risk.get("risk") or risk.get("description") or str(risk)
                    mitigation = risk.get("mitigation") or ""
                    lines.append(f"- **Risk:** {risk_text}" + (f" → {mitigation}" if mitigation else ""))
                else:
                    lines.append(f"- {risk}")
            lines.append("")

        lines += _change_set_footer(change_set)
        return "\n".join(lines)

    def _briefing_pricing(
        self,
        change_set: PendingChangeSetContract,
        drafts: list[Any],
    ) -> str:
        cost_draft = _first_draft_by_type(drafts, ArtifactDraftType.COST_ESTIMATE)
        content: dict[str, Any] = cost_draft.content if cost_draft else {}

        title = content.get("title") or "Cost Estimate"
        total = content.get("totalMonthlyCost") or content.get("totalCost") or content.get("total")
        currency = content.get("currency") or "USD"
        confidence = content.get("confidence") or content.get("confidenceLevel") or "medium"
        cost_drivers: list[Any] = content.get("costDrivers") or content.get("lineItems") or []
        assumptions: list[Any] = content.get("pricingAssumptions") or content.get("assumptions") or []
        optimizations: list[Any] = content.get("optimizationOpportunities") or content.get("optimizations") or []
        gaps: list[Any] = content.get("pricingGaps") or content.get("gaps") or []

        lines: list[str] = [
            f"## Architect Briefing — {title}",
            "",
        ]

        if total is not None:
            lines += [f"**Estimated Monthly Cost:** {total} {currency}  (Confidence: {confidence})", ""]
        else:
            lines += [f"**Confidence Level:** {confidence}", ""]

        if cost_drivers:
            lines.append("**Top Cost Drivers:**")
            for driver in cost_drivers[:5]:
                if isinstance(driver, dict):
                    name = driver.get("name") or driver.get("service") or driver.get("description") or str(driver)
                    amount = driver.get("monthlyCost") or driver.get("cost") or ""
                    lines.append(f"- {name}" + (f": {amount}" if amount else ""))
                else:
                    lines.append(f"- {driver}")
            lines.append("")

        if assumptions:
            lines.append("**Key Assumptions:**")
            for a in assumptions[:5]:
                lines.append(f"- {a}")
            lines.append("")

        if optimizations:
            lines.append("**Optimization Opportunities:**")
            for o in optimizations[:3]:
                lines.append(f"- {o}")
            lines.append("")

        if gaps:
            lines.append("**Pricing Gaps (excluded from estimate):**")
            for g in gaps[:3]:
                lines.append(f"- {g}")
            lines.append("")

        lines += _change_set_footer(change_set)
        return "\n".join(lines)

    def _briefing_iac(
        self,
        change_set: PendingChangeSetContract,
        drafts: list[Any],
    ) -> str:
        iac_draft = _first_draft_by_type(drafts, ArtifactDraftType.IAC)
        content: dict[str, Any] = iac_draft.content if iac_draft else {}

        title = content.get("title") or "Infrastructure as Code"
        modules: list[Any] = content.get("modules") or content.get("resources") or []
        outputs: list[Any] = content.get("outputs") or []
        validation_status = content.get("validationStatus") or content.get("validation_status") or "pending"

        resource_count = content.get("resourceCount") or len(modules)

        lines: list[str] = [
            f"## Architect Briefing — {title}",
            "",
            f"**Resources Defined:** {resource_count}  ·  **Validation Status:** {validation_status}",
            "",
        ]

        if modules:
            lines.append("**Module / Resource Structure:**")
            for mod in modules[:6]:
                if isinstance(mod, dict):
                    name = mod.get("name") or mod.get("type") or str(mod)
                    desc = mod.get("description") or mod.get("purpose") or ""
                    lines.append(f"- **{name}**" + (f": {desc}" if desc else ""))
                else:
                    lines.append(f"- {mod}")
            lines.append("")

        if outputs:
            lines.append("**Key Outputs:**")
            for o in outputs[:5]:
                if isinstance(o, dict):
                    name = o.get("name") or str(o)
                    desc = o.get("description") or ""
                    lines.append(f"- `{name}`" + (f": {desc}" if desc else ""))
                else:
                    lines.append(f"- `{o}`")
            lines.append("")

        lines += _change_set_footer(change_set)
        return "\n".join(lines)

    def _briefing_validate(
        self,
        change_set: PendingChangeSetContract,
        drafts: list[Any],
    ) -> str:
        finding_drafts = [
            d for d in drafts
            if d.artifact_type == ArtifactDraftType.FINDING
        ]

        title = change_set.bundle_summary or "Validation Findings"

        severity_counts: dict[str, int] = {}
        top_findings: list[dict[str, Any]] = []

        for fd in finding_drafts:
            content = fd.content if fd.content else {}
            severity = str(content.get("severity") or "medium").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            if len(top_findings) < 5:
                top_findings.append(content)

        total_findings = len(finding_drafts)

        lines: list[str] = [
            f"## Architect Briefing — {title}",
            "",
            f"**Total Findings:** {total_findings}",
        ]

        if severity_counts:
            breakdown = "  ·  ".join(
                f"{sev}: {cnt}"
                for sev, cnt in sorted(severity_counts.items(), key=lambda x: _severity_order(x[0]))
            )
            lines += [f"**Severity Breakdown:** {breakdown}", ""]

        if top_findings:
            lines.append("**Top Findings:**")
            for f in top_findings:
                title_text = f.get("title") or "Finding"
                sev = f.get("severity") or "?"
                remediation = f.get("remediation") or ""
                lines.append(f"- **[{sev.upper()}] {title_text}**" + (f" → {remediation}" if remediation else ""))
            lines.append("")

        if total_findings == 0:
            lines += ["No validation findings recorded.", ""]

        lines += _change_set_footer(change_set)
        return "\n".join(lines)

    def _briefing_clarify(
        self,
        change_set: PendingChangeSetContract,
        drafts: list[Any],
    ) -> str:
        question_drafts = [
            d for d in drafts
            if d.artifact_type == ArtifactDraftType.CLARIFICATION_QUESTION
        ]

        title = change_set.bundle_summary or "Clarification Questions"

        lines: list[str] = [
            f"## Architect Briefing — {title}",
            "",
        ]

        if question_drafts:
            lines.append(f"**{len(question_drafts)} clarification question(s) logged:**")
            for qd in question_drafts[:5]:
                content = qd.content or {}
                question_text = content.get("text") or content.get("question") or "—"
                default = content.get("defaultAssumption") or content.get("default_assumption") or ""
                impact = content.get("affectedDecision") or content.get("affected_decision") or ""
                lines.append(f"- **Q:** {question_text}")
                if impact:
                    lines.append(f"  *Decision impacted:* {impact}")
                if default:
                    lines.append(f"  *Default if unanswered:* {default}")
            lines.append("")
        else:
            patch = change_set.proposed_patch or {}
            defaults: list[Any] = (
                patch.get("_clarificationResolution", {}).get("assumptions")
                or patch.get("assumptions")
                or []
            )
            if defaults:
                lines.append("**Defaults assumed (proceed with defaults path):**")
                for d in defaults[:5]:
                    if isinstance(d, dict):
                        lines.append(f"- {d.get('text') or d}")
                    else:
                        lines.append(f"- {d}")
                lines.append("")

        lines += _change_set_footer(change_set)
        return "\n".join(lines)

    def _briefing_generic(self, change_set: PendingChangeSetContract) -> str:
        """Fallback briefing for unknown stages or empty change sets."""
        stage = change_set.stage or "unknown"
        total_drafts = len(change_set.artifact_drafts or [])

        lines: list[str] = [
            f"## Architect Briefing — {change_set.bundle_summary or 'Pending Change'}",
            "",
            f"**Stage:** {stage}  ·  **Artifacts:** {total_drafts}",
            "",
        ]
        lines += _change_set_footer(change_set)
        return "\n".join(lines)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _first_draft_by_type(drafts: list[Any], artifact_type: ArtifactDraftType) -> Any | None:
    for draft in drafts:
        if getattr(draft, "artifact_type", None) == artifact_type:
            return draft
    return None


def _change_set_footer(change_set: PendingChangeSetContract) -> list[str]:
    return [
        f"**Pending Change Set ID:** `{change_set.id}`  "
        f"(stage: `{change_set.stage}` · status: `{change_set.status.value}`)",
        "",
        "_Review and approve this change set to apply it to the project._",
    ]


def _severity_order(sev: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(sev, 4)
