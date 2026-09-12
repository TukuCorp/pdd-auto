"""Tests for the reconcile comparison (PHASE-06, S-6)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

import pdd_agent.reconcile.diff as diff_module
from pdd_agent.calc.dispatch import AnnualErEntry, PddCalcResult
from pdd_agent.config_io import load_project_input
from pdd_agent.reconcile.diff import reconcile, render_markdown
from pdd_agent.reconcile.workbook import read_acm0022_workbook

from tests.test_reconcile_workbook import _make_workbook


def _fake_result(nets: list[float]) -> PddCalcResult:
    return PddCalcResult(
        methodology_id="ACM0022",
        baseline_emissions_tco2e=0.0,
        project_emissions_tco2e=0.0,
        leakage_tco2e=0.0,
        net_emission_reductions_tco2e=sum(nets) / len(nets),
        crediting_period_total_tco2e=sum(nets),
        crediting_period_years=len(nets),
        annual_schedule=[
            AnnualErEntry(
                year=i + 1, baseline_tco2e=n, project_tco2e=0.0, leakage_tco2e=0.0, net_tco2e=n
            )
            for i, n in enumerate(nets)
        ],
    )


def _inegol_pi_no_zone():
    pi = load_project_input(Path(__file__).parent.parent / "configs/demo/inegol_project_input.yaml")
    pi.location.climate_zone = None
    return pi


def _synthetic_workbook(tmp_path: Path):
    return read_acm0022_workbook(_make_workbook(tmp_path / "synth.xlsx"))


def test_reconcile_pass_totals_and_year_row(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diff_module, "compute_for", lambda pi: _fake_result([950.0, 1750.0]))
    report = reconcile(_inegol_pi_no_zone(), _synthetic_workbook(tmp_path), tolerance=0.20)
    assert report.total_registered == 2700.0
    assert report.total_engine == 2700.0
    assert report.total_rel_diff == 0.0
    assert report.verdict_pass is True
    net_year1 = next(r for r in report.rows if r.component == "net" and r.year_index == 1)
    assert net_year1.abs_diff == pytest.approx(50.0)
    assert net_year1.rel_diff == pytest.approx(50 / 900)


def test_reconcile_fail_verdict(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diff_module, "compute_for", lambda pi: _fake_result([500.0, 900.0]))
    report = reconcile(_inegol_pi_no_zone(), _synthetic_workbook(tmp_path), tolerance=0.20)
    assert report.total_rel_diff == pytest.approx((1400 - 2700) / 2700)
    assert report.verdict_pass is False


def test_zero_registered_leakage_rows_are_informational(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diff_module, "compute_for", lambda pi: _fake_result([950.0, 1750.0]))
    report = reconcile(_inegol_pi_no_zone(), _synthetic_workbook(tmp_path), tolerance=0.20)
    leakage_rows = [r for r in report.rows if r.component == "leakage"]
    assert leakage_rows, "expected leakage rows"
    for row in leakage_rows:
        assert row.rel_diff is None
        assert row.within_tolerance is True


def test_undeclared_zone_is_a_parameter_mismatch(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diff_module, "compute_for", lambda pi: _fake_result([950.0, 1750.0]))
    report = reconcile(_inegol_pi_no_zone(), _synthetic_workbook(tmp_path), tolerance=0.20)
    zone_notes = [m for m in report.parameter_mismatches if "climate zone" in m]
    assert len(zone_notes) == 1
    assert "boreal_temperate_wet" in zone_notes[0]  # engine derived value
    assert "boreal_temperate_dry" in zone_notes[0]  # workbook-inferred value


def test_render_markdown_contains_verdict_table_and_mismatches(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(diff_module, "compute_for", lambda pi: _fake_result([500.0, 900.0]))
    report = reconcile(_inegol_pi_no_zone(), _synthetic_workbook(tmp_path), tolerance=0.20)
    text = render_markdown(report)
    assert "| Year |" in text
    assert ("FAIL" in text) != report.verdict_pass
    assert ("PASS" in text) == report.verdict_pass
    for mismatch in report.parameter_mismatches:
        assert mismatch in text


def test_cli_reconcile_json_exit_3_on_fail(tmp_path: Path, monkeypatch, capsys):
    from pdd_agent.cli import main

    inegol_copy = tmp_path / "inegol.yaml"
    shutil.copy(
        Path(__file__).parent.parent / "configs/demo/inegol_project_input.yaml", inegol_copy
    )
    wb_path = _make_workbook(tmp_path / "synth.xlsx")
    monkeypatch.setattr(diff_module, "compute_for", lambda pi: _fake_result([100.0, 100.0]))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pdd-agent",
            "reconcile",
            "--input",
            str(inegol_copy),
            "--workbook",
            str(wb_path),
            "--json",
        ],
    )
    assert main() == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict_pass"] is False
    assert set(payload) >= {"project_name", "total_registered", "total_engine", "rows"}
