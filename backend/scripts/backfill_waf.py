"""Compatibility wrapper for backfill CLI.

Use the canonical script at ``scripts/backfill_waf.py`` from the repository root.
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "backfill_waf.py"
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
