"""
pytest configuration for the refineries test suite.

Adds the refineries/ package root to sys.path so all modules are
importable with bare names (e.g. `import refine_uniprot`).
"""
from __future__ import annotations

import sys
from pathlib import Path

# refineries/ (parent of tests/) must be on sys.path
_REFINERIES_ROOT = Path(__file__).resolve().parents[1]
if str(_REFINERIES_ROOT) not in sys.path:
    sys.path.insert(0, str(_REFINERIES_ROOT))

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
