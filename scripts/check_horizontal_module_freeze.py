"""CLI wrapper for the Phase 0/1 horizontal module freeze check."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.architecture.horizontal_module_freeze import main

if __name__ == "__main__":
    raise SystemExit(main())
