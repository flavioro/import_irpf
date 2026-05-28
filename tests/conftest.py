"""Test configuration.

Ensures the project root is on sys.path when pytest is invoked either as
`pytest` or `python -m pytest` on Windows/Conda environments.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
