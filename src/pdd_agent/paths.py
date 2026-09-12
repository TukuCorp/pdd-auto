"""Central resolver for the default run-store directory."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Return the checkout root."""
    return Path(__file__).resolve().parents[2]


def default_runs_dir() -> Path:
    """Return the default directory for run JSON persistence.

    ``$PDD_RUNS_DIR`` when set and non-empty, else ``repo_root() / "data" / "runs"``.
    Evaluated on every call so tests can redirect it via the environment.
    """
    override = os.environ.get("PDD_RUNS_DIR")
    if override:
        return Path(override)
    return repo_root() / "data" / "runs"
