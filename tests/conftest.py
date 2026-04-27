"""Adds tests/ to sys.path so subdirectory tests can import shared helpers
via `from _helpers.version_check import ...` etc."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
