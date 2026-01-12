---
name: uv-package-manager
description: Efficient Python package and environment management using uv. Use this skill to manage dependencies, sync environments, and run Python scripts using the uv tool.
---

# UV Package Manager Skill

## Overview

`uv` is an extremely fast Python package installer and resolver, written in Rust. It's designed as a drop-in replacement for common `pip`, `pip-tools`, and `virtualenv` workflows. This skill helps you manage the project's Python environment efficiently.

## Quick Start

- **Sync Environment**: `uv sync` (Installs all dependencies from `pyproject.toml` and updates `uv.lock`)
- **Add Dependency**: `uv add <package_name>`
- **Add Dev Dependency**: `uv add --dev <package_name>`
- **Remove Dependency**: `uv remove <package_name>`
- **Run Script**: `uv run <script.py>` or `uv run <command>`
- **Lock Dependencies**: `uv lock` (Updates `uv.lock` without installing)

## Virtual Environment Management

`uv` manages virtual environments automatically in a `.venv` directory at the project root.

- **Create Venv**: `uv venv`
- **Activation (Windows PowerShell)**: `.venv\Scripts\Activate.ps1`
- **Activation (Windows Command Prompt)**: `.venv\Scripts\activate.bat`

## Best Practices

- **Reproducible Builds**: Always commit `uv.lock` and `pyproject.toml` to version control.
- **Environment Isolation**: Prefer `uv run` for executing commands within the project context, as it ensures the correct environment is used without manual activation.
- **Fast Installation**: Use `uv sync` after pulling changes to ensure your local `.venv` matches the lockfile.
- **Python Versioning**: Use `uv python pin <version>` to specify a Python version for the project (stored in `.python-version`).
- **Global Tools**: Use `uv tool install <package>` for tools you want available globally (e.g., `ruff`, `mypy`).

## Troubleshooting

- **Inconsistent Environment**: If the `.venv` seems corrupted, delete it and run `uv sync`.
- **Dependency Conflicts**: `uv` provides detailed error messages when resolution fails. Check `pyproject.toml` for incompatible version ranges.
- **Network Issues**: `uv` uses a cache. If you suspect cache issues, use `--no-cache` or `uv cache clean`.

## Resources

- [Official UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub Repository](https://github.com/astral-sh/uv)
