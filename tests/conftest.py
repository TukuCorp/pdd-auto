"""Session-wide run-store redirection for tests.

Points ``PDD_RUNS_DIR`` and ``PDD_SERVICE_RUNS_DIR`` at a temporary directory
for the whole test session so no test writes into the committed ``data/runs/``.
Tests that need to *read* committed files must pin an explicit directory or
monkeypatch ``PDD_RUNS_DIR`` inside that test only.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _redirect_runs_dir(tmp_path_factory):
    runs_dir = tmp_path_factory.mktemp("runs")
    previous_runs = os.environ.get("PDD_RUNS_DIR")
    previous_service = os.environ.get("PDD_SERVICE_RUNS_DIR")
    os.environ["PDD_RUNS_DIR"] = str(runs_dir)
    os.environ["PDD_SERVICE_RUNS_DIR"] = str(runs_dir)
    try:
        yield runs_dir
    finally:
        if previous_runs is None:
            os.environ.pop("PDD_RUNS_DIR", None)
        else:
            os.environ["PDD_RUNS_DIR"] = previous_runs
        if previous_service is None:
            os.environ.pop("PDD_SERVICE_RUNS_DIR", None)
        else:
            os.environ["PDD_SERVICE_RUNS_DIR"] = previous_service
