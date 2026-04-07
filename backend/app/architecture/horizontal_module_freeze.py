"""Warning-oriented checks for frozen horizontal module directories."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FreezeRule:
    """Path policy for one frozen directory root."""

    root: str
    allowed_prefixes: tuple[str, ...]
    guidance: str


@dataclass(frozen=True)
class FreezeViolation:
    """A newly added file that violates the freeze policy."""

    path: str
    guidance: str


@dataclass(frozen=True)
class FreezeCheckReport:
    """Collected violations for a single diff or file list."""

    checked_paths: tuple[str, ...]
    violations: tuple[FreezeViolation, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the report."""
        return asdict(self)


FREEZE_RULES: tuple[FreezeRule, ...] = (
    FreezeRule(
        root="backend/app/services",
        allowed_prefixes=(
            "backend/app/services/project/",
            "backend/app/services/ai/",
            "backend/app/services/kb/",
            "backend/app/services/diagram/",
            "backend/app/services/ingestion/",
            "backend/app/services/mcp/",
            "backend/app/services/pricing/",
        ),
        guidance="Keep new backend service files inside approved feature subpackages.",
    ),
    FreezeRule(
        root="backend/app/routers",
        allowed_prefixes=(
            "backend/app/routers/agents/",
            "backend/app/routers/checklists/",
            "backend/app/routers/diagram_generation/",
            "backend/app/routers/ingestion/",
            "backend/app/routers/kb_management/",
            "backend/app/routers/kb_query/",
            "backend/app/routers/settings/",
        ),
        guidance="Add router files inside an existing router subpackage rather than at the top level.",
    ),
    FreezeRule(
        root="frontend/src/hooks",
        allowed_prefixes=(),
        guidance="Top-level frontend hooks are frozen; prefer feature-local hooks.",
    ),
    FreezeRule(
        root="frontend/src/services",
        allowed_prefixes=(),
        guidance="Top-level frontend services are frozen; prefer feature-local API modules.",
    ),
    FreezeRule(
        root="frontend/src/types",
        allowed_prefixes=(),
        guidance="Top-level frontend types are frozen; prefer feature-local type modules.",
    ),
    FreezeRule(
        root="frontend/src/components",
        allowed_prefixes=("frontend/src/components/common/",),
        guidance="Top-level frontend components are frozen outside components/common.",
    ),
)
_SAFE_GIT_REF_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")


def default_repo_root() -> Path:
    """Return the repository root from the backend helper location."""
    return Path(__file__).resolve().parents[3]


def default_base_ref() -> str:
    """Choose a sensible default base ref for local and CI runs."""
    github_base_ref = os.environ.get("GITHUB_BASE_REF")
    if github_base_ref:
        return github_base_ref if github_base_ref.startswith("origin/") else f"origin/{github_base_ref}"
    return "origin/main"


def evaluate_added_paths(added_paths: Iterable[str]) -> FreezeCheckReport:
    """Evaluate added repo-relative paths against the freeze rules."""
    normalized_paths = tuple(sorted({_normalize_path(path) for path in added_paths if path.strip()}))
    violations: list[FreezeViolation] = []

    for path in normalized_paths:
        for rule in FREEZE_RULES:
            if not path.startswith(f"{rule.root}/"):
                continue
            if any(path.startswith(prefix) for prefix in rule.allowed_prefixes):
                break
            violations.append(FreezeViolation(path=path, guidance=rule.guidance))
            break

    return FreezeCheckReport(checked_paths=normalized_paths, violations=tuple(violations))


def collect_added_paths(repo_root: Path, base_ref: str, head_ref: str) -> list[str]:
    """Return newly added files between two refs using git diff."""
    resolved_repo_root = repo_root.resolve()
    if not resolved_repo_root.exists():
        raise ValueError(f"Repository root does not exist: {resolved_repo_root}")

    validated_base_ref = _validate_git_ref(base_ref, label="base_ref")
    validated_head_ref = _validate_git_ref(head_ref, label="head_ref")
    comparison = f"{validated_base_ref}...{validated_head_ref}"
    completed = subprocess.run(  # noqa: S603 - refs are validated and git path is resolved.
        [
            _resolve_git_executable(),
            "-C",
            str(resolved_repo_root),
            "diff",
            "--name-only",
            "--diff-filter=A",
            comparison,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git diff failed for {comparison}")
    return [line for line in completed.stdout.splitlines() if line.strip()]


def render_warning_report(report: FreezeCheckReport) -> str:
    """Render the freeze check as warning-oriented CI output."""
    if not report.violations:
        return "Horizontal module freeze warnings\nNo violations detected."

    lines = [
        "Horizontal module freeze warnings",
        "This check is warning-oriented during Phase 0/1 and can become blocking later.",
        "",
    ]
    lines.extend(
        f"- {violation.path}: {violation.guidance}" for violation in report.violations
    )
    return "\n".join(lines)


def build_cli_parser() -> argparse.ArgumentParser:
    """Create the CLI parser used by scripts/check_horizontal_module_freeze.py."""
    parser = argparse.ArgumentParser(
        description="Warn about newly added files in frozen horizontal module directories."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="Repository root used when collecting git diff paths.",
    )
    parser.add_argument(
        "--base-ref",
        default=default_base_ref(),
        help="Base ref used for git diff collection. Defaults to GITHUB_BASE_REF or origin/main.",
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head ref used for git diff collection.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for stdout.",
    )
    parser.add_argument(
        "--fail-on-violation",
        action="store_true",
        help="Exit with code 1 when violations are found.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by scripts/check_horizontal_module_freeze.py."""
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    report = evaluate_added_paths(
        collect_added_paths(
            repo_root=args.repo_root.resolve(),
            base_ref=args.base_ref,
            head_ref=args.head_ref,
        )
    )

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_warning_report(report))

    return 1 if args.fail_on_violation and report.violations else 0


def _resolve_git_executable() -> str:
    git_path = shutil.which("git")
    if git_path is None:
        raise RuntimeError("git executable not found on PATH")
    return str(Path(git_path).resolve())


def _validate_git_ref(ref: str, *, label: str) -> str:
    normalized_ref = ref.strip()
    if normalized_ref != ref or not normalized_ref:
        raise ValueError(f"{label} must be a non-empty git ref without surrounding whitespace")
    if not _SAFE_GIT_REF_PATTERN.fullmatch(normalized_ref):
        raise ValueError(f"{label} contains unsafe git ref characters: {ref!r}")
    return normalized_ref


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


__all__ = [
    "FREEZE_RULES",
    "FreezeCheckReport",
    "FreezeViolation",
    "build_cli_parser",
    "collect_added_paths",
    "default_base_ref",
    "default_repo_root",
    "evaluate_added_paths",
    "main",
    "render_warning_report",
]
