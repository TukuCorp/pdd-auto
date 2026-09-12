"""PHASE-01 hygiene tests: run-store resolver, ASCII help, export exit code."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from pdd_agent.paths import default_runs_dir, repo_root


def test_default_runs_dir_uses_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("PDD_RUNS_DIR", str(tmp_path))
    assert default_runs_dir() == tmp_path


def test_default_runs_dir_falls_back_without_env(monkeypatch):
    monkeypatch.delenv("PDD_RUNS_DIR", raising=False)
    assert default_runs_dir() == repo_root() / "data" / "runs"


def test_default_runs_dir_falls_back_on_empty_env(monkeypatch):
    monkeypatch.setenv("PDD_RUNS_DIR", "")
    assert default_runs_dir() == repo_root() / "data" / "runs"


def test_draft_run_save_uses_redirected_runs_dir():
    from pdd_agent.llm.provider import DraftRun

    run = DraftRun(run_id="hygiene-1", project_name="x", provider="noop")
    path = run.save()
    assert path.parent == Path(os.environ["PDD_RUNS_DIR"])
    assert not Path("data/runs/hygiene-1.json").exists()


def test_all_help_strings_ascii():
    from pdd_agent.cli import _build_parser

    parser = _build_parser()
    subparsers_actions = parser._subparsers._group_actions  # noqa: SLF001
    choices = subparsers_actions[0].choices
    assert "inventory" in choices
    for name, sub in choices.items():
        for action in sub._actions:  # noqa: SLF001
            if action.help is not None:
                assert action.help.encode("ascii"), name


def test_help_runs_under_cp1252():
    args = [sys.executable, "-m", "pdd_agent.cli", "--help"]
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    proc = subprocess.run(args, env=env, capture_output=True, timeout=120)
    assert proc.returncode == 0
    assert b"inventory" in proc.stdout


def test_run_export_returns_2_when_blocked(monkeypatch):
    import pdd_agent.cli as cli_mod
    from pdd_agent.export.docx_export import ExportBlockedError

    def _blocked(*args, **kwargs):
        raise ExportBlockedError("blocked for test")

    monkeypatch.setattr(cli_mod, "export_run_to_docx", _blocked)

    class _Log:
        def error(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

    args = argparse.Namespace(
        review_output_dir=None, output=None, force=False, pdf=False, run_id="r1"
    )
    assert cli_mod._run_export(args, _Log()) == 2
