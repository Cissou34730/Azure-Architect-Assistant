from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path


def test_importlinter_config_declares_expected_baseline_contracts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    config = ConfigParser()
    config.read(repo_root / ".importlinter", encoding="utf-8")

    assert config["importlinter"]["root_package"] == "app"
    assert "importlinter:contract:core-layers" in config
    assert "importlinter:contract:selected-router-independence" in config
    assert "importlinter:contract:agents-platform" in config
    assert "importlinter:contract:shared-foundation" in config
    assert "importlinter:contract:feature-api-independence" in config
    assert "importlinter:contract:projects-feature-layers" in config
    assert "importlinter:contract:knowledge-feature-layers" in config
    assert "importlinter:contract:ingestion-feature-layers" in config
    assert "importlinter:contract:checklists-feature-layers" in config
    assert "importlinter:contract:agent-feature-layers" in config
    assert "importlinter:contract:settings-feature-layers" in config
    assert "importlinter:contract:projects-application-avoids-projects-api" in config
    assert "importlinter:contract:projects-application-avoids-other-feature-internals" in config
    assert "importlinter:contract:features-and-shared-avoid-legacy-ai-mcp-core" in config
    assert "importlinter:contract:retired-kb-shim" in config
    assert "importlinter:contract:retired-diagram-model-shim" in config
    assert "importlinter:contract:checklists-feature-avoids-legacy-agents-checklists" in config
    forbidden_modules = config["importlinter:contract:agents-platform"][
        "forbidden_modules"
    ]
    assert "app.features.projects.api" in forbidden_modules
    assert "app.features.knowledge.api" in forbidden_modules


def test_projects_application_does_not_import_other_feature_application_modules() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    application_root = repo_root / "backend" / "app" / "features" / "projects" / "application"

    module_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(application_root.glob("*.py"))
        if path.name != "__init__.py"
    )

    assert "app.features.diagrams.application" not in module_text
    assert "app.features.ingestion.application" not in module_text
    assert "app.features.knowledge.application" not in module_text
    assert "app.models.diagram" not in module_text
    assert "app.service_registry" not in module_text


def test_diagrams_application_does_not_import_legacy_diagram_models() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    application_root = repo_root / "backend" / "app" / "features" / "diagrams" / "application"

    module_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(application_root.glob("*.py"))
        if path.name != "__init__.py"
    )

    assert "app.models.diagram" not in module_text


def test_knowledge_feature_does_not_import_legacy_kb_package() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    knowledge_root = repo_root / "backend" / "app" / "features" / "knowledge"

    module_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(knowledge_root.rglob("*.py"))
        if path.name != "__init__.py"
    )

    assert "app.kb" not in module_text


def test_legacy_kb_shim_package_has_been_removed() -> None:
    """The app.kb compatibility shim was retired; the directory must not exist."""
    repo_root = Path(__file__).resolve().parents[3]
    kb_root = repo_root / "backend" / "app" / "kb"
    assert not kb_root.exists(), f"Legacy app.kb shim package still present at {kb_root}"


def test_legacy_diagram_model_shim_package_has_been_removed() -> None:
    """The app.models.diagram compatibility shim was retired; the directory must not exist."""
    repo_root = Path(__file__).resolve().parents[3]
    diagram_root = repo_root / "backend" / "app" / "models" / "diagram"
    assert not diagram_root.exists(), (
        f"Legacy app.models.diagram shim package still present at {diagram_root}"
    )


def test_ingestion_feature_does_not_import_legacy_ingestion_package() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    ingestion_root = repo_root / "backend" / "app" / "features" / "ingestion"

    module_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(ingestion_root.rglob("*.py"))
        if path.name != "__init__.py"
    )

    assert "app.ingestion" not in module_text


def test_feature_and_shared_packages_do_not_import_legacy_ai_mcp_or_settings_paths() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    package_roots = [
        repo_root / "backend" / "app" / "features",
        repo_root / "backend" / "app" / "shared",
    ]

    module_text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in package_roots
        for path in sorted(root.rglob("*.py"))
        if path.name != "__init__.py"
    )

    assert "app.services.ai" not in module_text
    assert "app.services.mcp" not in module_text
    assert "app.core.settings" not in module_text
    assert "app.core.db" not in module_text


def test_shared_package_does_not_import_feature_packages() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    shared_root = repo_root / "backend" / "app" / "shared"

    module_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(shared_root.rglob("*.py"))
        if path.name != "__init__.py"
    )

    assert "app.features" not in module_text


def test_checklists_feature_does_not_import_legacy_agents_checklists_package() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    checklists_root = repo_root / "backend" / "app" / "features" / "checklists"

    module_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(checklists_root.rglob("*.py"))
        if path.name != "__init__.py"
    )

    assert "app.agents_system.checklists" not in module_text


def test_agent_tool_factory_and_nodes_use_feature_owned_tool_implementations() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    candidate_tool = repo_root / "backend" / "app" / "agents_system" / "tools" / "aaa_candidate_tool.py"
    cost_node = (
        repo_root
        / "backend"
        / "app"
        / "agents_system"
        / "langgraph"
        / "nodes"
        / "cost_estimator.py"
    )

    candidate_text = candidate_tool.read_text(encoding="utf-8")
    cost_node_text = cost_node.read_text(encoding="utf-8")

    assert "app.features.agent.infrastructure.tools" in candidate_text
    assert "app.agents_system.tools.aaa_cost_tool" not in cost_node_text


def test_agents_system_aaa_tool_modules_are_compatibility_wrappers() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    tools_root = repo_root / "backend" / "app" / "agents_system" / "tools"

    for path in sorted(tools_root.glob("aaa_*.py")):
        module_text = path.read_text(encoding="utf-8")
        assert "app.features.agent.infrastructure.tools" in module_text, path.name
        assert "langchain_core.tools" not in module_text, path.name


def test_feature_directories_match_the_curated_backend_and_frontend_sets() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    backend_features_root = repo_root / "backend" / "app" / "features"
    frontend_features_root = repo_root / "frontend" / "src" / "features"

    backend_feature_dirs = {
        path.name
        for path in backend_features_root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }
    frontend_feature_dirs = {
        path.name
        for path in frontend_features_root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }

    assert backend_feature_dirs == {
        "agent",
        "checklists",
        "diagrams",
        "ingestion",
        "knowledge",
        "projects",
        "settings",
    }
    assert frontend_feature_dirs == {
        "agent",
        "diagrams",
        "ingestion",
        "knowledge",
        "projects",
        "settings",
    }


def test_canonical_runtime_modules_do_not_import_legacy_core_package() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    module_paths = [
        repo_root / "backend" / "app" / "main.py",
        repo_root / "backend" / "app" / "shared" / "config" / "app_settings.py",
        repo_root
        / "backend"
        / "app"
        / "features"
        / "settings"
        / "application"
        / "settings_service.py",
    ]

    module_text = "\n".join(
        path.read_text(encoding="utf-8") for path in module_paths
    )

    assert "app.core." not in module_text


def test_main_and_feature_routers_do_not_depend_on_legacy_router_package() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    module_paths = [
        repo_root / "backend" / "app" / "main.py",
        repo_root
        / "backend"
        / "app"
        / "features"
        / "checklists"
        / "api"
        / "checklist_router.py",
        repo_root
        / "backend"
        / "app"
        / "features"
        / "knowledge"
        / "api"
        / "management_router.py",
        repo_root
        / "backend"
        / "app"
        / "features"
        / "projects"
        / "api"
        / "document_router.py",
        repo_root
        / "backend"
        / "app"
        / "features"
        / "projects"
        / "api"
        / "project_router.py",
        repo_root
        / "backend"
        / "app"
        / "features"
        / "projects"
        / "api"
        / "state_router.py",
    ]

    module_text = "\n".join(
        path.read_text(encoding="utf-8") for path in module_paths
    )

    assert "app.routers" not in module_text


def test_projects_and_diagrams_services_do_not_import_projectstate_model_directly() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    module_paths = [
        repo_root / "backend" / "app" / "features" / "projects" / "application" / "chat_service.py",
        repo_root / "backend" / "app" / "features" / "projects" / "application" / "document_service.py",
        repo_root / "backend" / "app" / "features" / "projects" / "application" / "project_service.py",
        repo_root / "backend" / "app" / "features" / "projects" / "application" / "state_edit_service.py",
        repo_root / "backend" / "app" / "features" / "diagrams" / "application" / "project_diagram_helpers.py",
    ]

    module_text = "\n".join(path.read_text(encoding="utf-8") for path in module_paths)

    assert "from app.models import ProjectState" not in module_text
    assert "from app.models.project import ProjectState" not in module_text


def test_workspace_contract_does_not_expose_raw_project_state_payload() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    contract_path = (
        repo_root / "backend" / "app" / "features" / "projects" / "contracts" / "workspace.py"
    )

    contract_text = contract_path.read_text(encoding="utf-8")

    assert "project_state:" not in contract_text
    assert 'alias="projectState"' not in contract_text


def test_runtime_modules_do_not_import_legacy_ingestion_package() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    module_paths = [
        repo_root / "backend" / "app" / "shared" / "db" / "session_helpers.py",
        repo_root / "backend" / "app" / "dependencies.py",
        repo_root / "backend" / "app" / "main.py",
        repo_root / "backend" / "app" / "lifecycle.py",
    ]

    module_text = "\n".join(path.read_text(encoding="utf-8") for path in module_paths)

    assert "app.ingestion" not in module_text


def test_runtime_modules_do_not_import_service_registry_directly() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    module_paths = [
        repo_root / "backend" / "app" / "agents_system" / "agents" / "rag_agent.py",
        repo_root / "backend" / "app" / "features" / "projects" / "api" / "_deps.py",
    ]

    module_text = "\n".join(path.read_text(encoding="utf-8") for path in module_paths)

    assert "app.service_registry" not in module_text


def test_lane_ownership_lists_only_feature_canonical_ingestion_root() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    lane_doc = repo_root / "docs" / "architecture" / "LANE_OWNERSHIP.md"

    lane_text = lane_doc.read_text(encoding="utf-8")

    assert "backend/app/features/ingestion/" in lane_text
    assert "backend/app/ingestion/" not in lane_text


def test_projects_api_deps_delegates_workspace_composer_wiring() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    deps_path = repo_root / "backend" / "app" / "features" / "projects" / "api" / "_deps.py"
    workspace_deps_path = (
        repo_root
        / "backend"
        / "app"
        / "features"
        / "projects"
        / "api"
        / "workspace_dependencies.py"
    )

    deps_text = deps_path.read_text(encoding="utf-8")
    workspace_deps_text = workspace_deps_path.read_text(encoding="utf-8")

    assert "class _ChecklistWorkspaceAdapter" not in deps_text
    assert "class _KnowledgeWorkspaceAdapter" not in deps_text
    assert "class _ArchitectureInputsWorkspaceAdapter" not in deps_text
    assert "class _ChecklistWorkspaceAdapter" in workspace_deps_text
    assert "class _KnowledgeWorkspaceAdapter" in workspace_deps_text
    assert "class _ArchitectureInputsWorkspaceAdapter" in workspace_deps_text

