"""Tests for P10: Diagram quality improvements.

Covers:
- diagram_explanation and how_to_read fields in diagram tool input
- Static semantic validation checks (non-LLM, non-blocking)
"""

from __future__ import annotations

import pytest

from app.features.agent.infrastructure.tools.aaa_diagram_tool import (
    AAACreateDiagramSetInput,
)
from app.features.diagrams.application.semantic_validator import (
    validate_diagram_semantics,
)


# ---------------------------------------------------------------------------
# AAACreateDiagramSetInput field tests
# ---------------------------------------------------------------------------


class TestDiagramToolExplanationFields:
    def test_accepts_diagram_explanation_field(self):
        """diagram_explanation should be accepted and stored."""
        data = {
            "inputDescription": "An e-commerce platform with Azure services",
            "diagramExplanation": "This shows the top-level context of the system.",
        }
        model = AAACreateDiagramSetInput.model_validate(data)
        assert model.diagram_explanation == "This shows the top-level context of the system."

    def test_accepts_how_to_read_field(self):
        """how_to_read should be accepted and stored."""
        data = {
            "inputDescription": "An e-commerce platform with Azure services",
            "howToRead": "Boxes are systems; arrows show data flow.",
        }
        model = AAACreateDiagramSetInput.model_validate(data)
        assert model.how_to_read == "Boxes are systems; arrows show data flow."

    def test_explanation_fields_optional(self):
        """Both explanation fields should default to None."""
        data = {"inputDescription": "An e-commerce platform with Azure services"}
        model = AAACreateDiagramSetInput.model_validate(data)
        assert model.diagram_explanation is None
        assert model.how_to_read is None

    def test_both_explanation_fields_together(self):
        """Both fields can be provided simultaneously."""
        data = {
            "inputDescription": "An e-commerce platform with Azure services",
            "diagramExplanation": "Top-level context view.",
            "howToRead": "Rectangles are systems, lines are integrations.",
        }
        model = AAACreateDiagramSetInput.model_validate(data)
        assert model.diagram_explanation == "Top-level context view."
        assert model.how_to_read == "Rectangles are systems, lines are integrations."


# ---------------------------------------------------------------------------
# Static semantic validation tests
# ---------------------------------------------------------------------------


WELL_FORMED_C4_CONTEXT = """\
C4Context
title E-Commerce Platform Context

Person(customer, "Customer", "A paying customer")
System(web_app, "Web App", "Handles orders")
System_Ext(payment, "Payment Gateway", "Processes payments")

Rel(customer, web_app, "Uses", "HTTPS")
Rel(web_app, payment, "Calls", "REST")
"""

WELL_FORMED_MERMAID = """\
flowchart LR
    User -->|"HTTP request"| WebApp
    WebApp -->|"SQL query"| DB[(Azure SQL)]
    WebApp -->|"Stores files"| Blob[Azure Blob Storage]
"""


class TestStaticSemanticValidation:
    def test_clean_diagram_has_no_warnings(self):
        """A well-formed diagram should return no warnings."""
        warnings = validate_diagram_semantics(WELL_FORMED_C4_CONTEXT, "c4_context")
        assert warnings == [], f"Unexpected warnings: {warnings}"

    def test_clean_mermaid_has_no_warnings(self):
        """A well-formed Mermaid diagram should return no warnings."""
        warnings = validate_diagram_semantics(WELL_FORMED_MERMAID, "mermaid_functional")
        assert warnings == [], f"Unexpected warnings: {warnings}"

    def test_detects_missing_actor_in_context_diagram(self):
        """A C4 context diagram with no Person node should warn about missing actor."""
        no_actor = """\
C4Context
title System without users

System(api, "Backend API", "Processes data")
System_Ext(db, "External DB", "Stores data")
Rel(api, db, "Reads", "SQL")
"""
        warnings = validate_diagram_semantics(no_actor, "c4_context")
        assert any("actor" in w.lower() or "person" in w.lower() for w in warnings), (
            f"Expected missing-actor warning, got: {warnings}"
        )

    def test_detects_unlabeled_flows_in_mermaid(self):
        """Mermaid arrows without labels should trigger a warning."""
        unlabeled = """\
flowchart LR
    User --> WebApp
    WebApp --> DB[(Azure SQL)]
"""
        warnings = validate_diagram_semantics(unlabeled, "mermaid_functional")
        assert any("label" in w.lower() or "flow" in w.lower() for w in warnings), (
            f"Expected unlabeled-flow warning, got: {warnings}"
        )

    def test_detects_placeholder_text(self):
        """Diagrams containing TODO/PLACEHOLDER should warn."""
        with_placeholder = """\
C4Context
title TODO: fill in later

Person(user, "PLACEHOLDER USER", "TBD")
System(sys, "EXAMPLE system", "does stuff")
Rel(user, sys, "TODO", "HTTP")
"""
        warnings = validate_diagram_semantics(with_placeholder, "c4_context")
        assert any("placeholder" in w.lower() or "todo" in w.lower() or "example" in w.lower() for w in warnings), (
            f"Expected placeholder warning, got: {warnings}"
        )

    def test_detects_unclear_abbreviations(self):
        """Services named with bare abbreviations (DB, SVC, API) should warn."""
        abbreviation_only = """\
flowchart LR
    User -->|"sends"| API
    API -->|"stores"| DB
    API -->|"calls"| SVC
"""
        warnings = validate_diagram_semantics(abbreviation_only, "mermaid_functional")
        assert any("abbreviat" in w.lower() or "name" in w.lower() for w in warnings), (
            f"Expected naming warning, got: {warnings}"
        )

    def test_detects_missing_external_dep_in_container_diagram(self):
        """Container diagram without an external system should warn."""
        no_external = """\
C4Container
title Internal containers only

Person(user, "User", "End user")
Container(api, "API", "Python", "Handles requests")
ContainerDb(db, "Database", "PostgreSQL", "Stores data")
Rel(user, api, "Uses", "HTTPS")
Rel(api, db, "Reads/Writes", "SQL")
"""
        warnings = validate_diagram_semantics(no_external, "c4_container")
        assert any("external" in w.lower() for w in warnings), (
            f"Expected missing-external-dependency warning, got: {warnings}"
        )

    def test_returns_list_of_strings(self):
        """validate_diagram_semantics should always return a list[str]."""
        result = validate_diagram_semantics("graph LR\n  A --> B", "mermaid_functional")
        assert isinstance(result, list)
        assert all(isinstance(w, str) for w in result)

    def test_empty_diagram_returns_warnings(self):
        """An empty diagram string should trigger at least one warning."""
        warnings = validate_diagram_semantics("", "c4_context")
        assert len(warnings) > 0
