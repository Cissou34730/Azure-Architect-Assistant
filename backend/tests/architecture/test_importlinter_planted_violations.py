from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


def _write_module(root: Path, relative_path: str, content: str = "") -> None:
    module_path = root / relative_path
    module_path.parent.mkdir(parents=True, exist_ok=True)

    current = root
    for part in Path(relative_path).parts[:-1]:
        current /= part
        init_path = current / "__init__.py"
        if not init_path.exists():
            init_path.write_text("", encoding="utf-8")

    module_path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def _run_import_linter(config_path: Path, python_path: Path) -> subprocess.CompletedProcess[str]:
    executable = Path(sys.executable).with_name("lint-imports.exe")
    assert executable.exists()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(python_path)

    return subprocess.run(
        [str(executable), "--config", str(config_path)],
        cwd=python_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_planted_cross_feature_internal_import_is_flagged(tmp_path: Path) -> None:
    _write_module(tmp_path, "app/features/alpha/service.py", "from app.features.beta.application import sentinel")
    _write_module(tmp_path, "app/features/beta/application.py", "sentinel = 1")

    config_path = tmp_path / ".importlinter"
    config_path.write_text(
        textwrap.dedent(
            """
            [importlinter]
            root_package = app

            [importlinter:contract:feature-internals]
            name = Features avoid other feature internals
            type = forbidden
            source_modules =
                app.features.alpha
            forbidden_modules =
                app.features.beta.application
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_import_linter(config_path, tmp_path)
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode != 0
    assert "Features avoid other feature internals" in output
    assert "app.features.beta.application" in output


def test_planted_shared_to_feature_import_is_flagged(tmp_path: Path) -> None:
    _write_module(tmp_path, "app/shared/helpers.py", "from app.features.projects.application import sentinel")
    _write_module(tmp_path, "app/features/projects/application.py", "sentinel = 1")

    config_path = tmp_path / ".importlinter"
    config_path.write_text(
        textwrap.dedent(
            """
            [importlinter]
            root_package = app

            [importlinter:contract:shared-foundation]
            name = Shared package does not depend on feature packages
            type = forbidden
            source_modules =
                app.shared
            forbidden_modules =
                app.features
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_import_linter(config_path, tmp_path)
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode != 0
    assert "Shared package does not depend on feature packages" in output
    assert "app.features.projects.application" in output


def test_planted_application_to_api_import_is_flagged(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "app/features/projects/application.py",
        "from app.features.projects.api_dtos import RequestModel",
    )
    _write_module(tmp_path, "app/features/projects/api_dtos.py", "class RequestModel: pass")

    config_path = tmp_path / ".importlinter"
    config_path.write_text(
        textwrap.dedent(
            """
            [importlinter]
            root_package = app

            [importlinter:contract:application-does-not-depend-on-api]
            name = Application layer avoids router DTOs
            type = forbidden
            source_modules =
                app.features.projects.application
            forbidden_modules =
                app.features.projects.api_dtos
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = _run_import_linter(config_path, tmp_path)
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode != 0
    assert "Application layer avoids router DTOs" in output
    assert "app.features.projects.api_dtos" in output
