"""Engine-vs-registered comparison for ACM0022 projects (S-6).

Recomputes a project with the calc engine and writes a per-year,
per-component diff against its registered workbook schedule. The verdict
uses only the crediting-period totals of net emission reductions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pdd_agent.calc.dispatch import build_engine_inputs, compute_for
from pdd_agent.reconcile.workbook import (
    ECBL_GRID_EF,
    RegisteredAcm0022Workbook,
    infer_climate_zone,
)
from schemas.project_input import ProjectInput

#: Absolute composition-fraction difference above which a mismatch is reported.
COMPOSITION_MISMATCH_TOLERANCE = 0.001

#: Separated-baseline ratio above which the TDL note (ASM-009) is reported.
TDL_NOTE_THRESHOLD = 1.001


@dataclass
class YearDiff:
    """One row of the per-year table."""

    year_index: int
    year_label: str
    component: str  # baseline | project | leakage | net
    registered: float
    engine: float
    abs_diff: float
    rel_diff: float | None
    within_tolerance: bool
    lineage: str  # "<sheet>!<cell>"


@dataclass
class ReconcileReport:
    """The complete engine-vs-registered comparison."""

    project_name: str
    workbook_path: str
    tolerance: float
    rows: list[YearDiff] = field(default_factory=list)
    total_registered: float = 0.0
    total_engine: float = 0.0
    total_rel_diff: float = 0.0
    verdict_pass: bool = False
    parameter_mismatches: list[str] = field(default_factory=list)
    engine_warnings: list[str] = field(default_factory=list)


def _diff_row(
    year_index: int,
    year_label: str,
    component: str,
    registered: float,
    engine: float,
    lineage: str,
    tolerance: float,
) -> YearDiff:
    abs_diff = engine - registered
    rel_diff = abs_diff / registered if registered != 0 else None
    return YearDiff(
        year_index=year_index,
        year_label=year_label,
        component=component,
        registered=registered,
        engine=engine,
        abs_diff=abs_diff,
        rel_diff=rel_diff,
        within_tolerance=rel_diff is None or abs(rel_diff) <= tolerance,
        lineage=lineage,
    )


def _parameter_mismatches(
    project_input: ProjectInput,
    workbook: RegisteredAcm0022Workbook,
    engine_zone: str | None,
) -> list[str]:
    mismatches: list[str] = []
    inferred = infer_climate_zone({k: v.value for k, v in workbook.decay_rates.items()})
    if inferred is None:
        mismatches.append(
            "climate zone: workbook decay rates match no single IPCC zone "
            f"(engine used {engine_zone}); declare location.climate_zone from the "
            "registered workbook"
        )
    elif engine_zone != inferred:
        mismatches.append(
            f"climate zone: engine {engine_zone} differs from workbook-inferred {inferred}"
        )
    for entry in project_input.technology.waste_composition:
        registered = workbook.composition.get(entry.waste_type)
        if registered is None:
            mismatches.append(
                f"composition {entry.waste_type}: config {entry.mass_fraction:.4f} "
                "has no workbook counterpart"
            )
        elif abs(entry.mass_fraction - registered.value) > COMPOSITION_MISMATCH_TOLERANCE:
            mismatches.append(
                f"composition {entry.waste_type}: config {entry.mass_fraction:.4f} vs "
                f"workbook {registered.value:.4f} ({registered.sheet}!{registered.cell})"
            )
    config_bio = project_input.technology.biomethanization_suitable_fraction
    workbook_bio = workbook.biomethanization_fraction
    if config_bio is not None and workbook_bio is not None:
        if abs(config_bio - workbook_bio.value) > COMPOSITION_MISMATCH_TOLERANCE:
            mismatches.append(
                f"biomethanization_suitable_fraction: config {config_bio:.4f} vs "
                f"workbook {workbook_bio.value:.4f} "
                f"({workbook_bio.sheet}!{workbook_bio.cell})"
            )
    elif config_bio is None and workbook_bio is not None:
        mismatches.append(
            "biomethanization_suitable_fraction: config absent (engine assumes 0.0) vs "
            f"workbook {workbook_bio.value:.4f} "
            f"({workbook_bio.sheet}!{workbook_bio.cell})"
        )
    ratios = [
        sep.value / (mwh.value * ECBL_GRID_EF)
        for mwh, sep in zip(workbook.electricity_mwh_by_year, workbook.separated_baseline_by_year)
        if mwh.value > 0
    ]
    if ratios and max(ratios) > TDL_NOTE_THRESHOLD:
        mismatches.append(
            "transmission/distribution losses (ASM-009): the workbook's separated "
            f"baseline exceeds MWh x {ECBL_GRID_EF} by up to {max(ratios):.5f}x; the "
            "engine applies no TDL multiplier to BE_EC"
        )
    return mismatches


def reconcile(
    project_input: ProjectInput,
    workbook: RegisteredAcm0022Workbook,
    tolerance: float = 0.20,
) -> ReconcileReport:
    """Compare the engine schedule against the registered schedule (S-6)."""
    mapped = build_engine_inputs(project_input)
    if mapped is None:
        raise ValueError("reconcile needs complete ACM0022 inputs (build_engine_inputs is None)")
    _mid, engine_inputs, _warnings = mapped
    result = compute_for(project_input)
    if result is None:
        raise ValueError("reconcile needs complete ACM0022 inputs (compute_for is None)")
    if result.methodology_id != "ACM0022":
        raise ValueError(f"reconcile supports ACM0022 only, got {result.methodology_id}")
    schedule = workbook.schedule
    if len(result.annual_schedule) < len(schedule.net):
        raise ValueError(
            f"engine schedule has {len(result.annual_schedule)} years but the "
            f"workbook holds {len(schedule.net)}"
        )
    rows: list[YearDiff] = []
    for idx, (label, reg_be, reg_pe, reg_le, reg_net) in enumerate(
        zip(
            schedule.year_labels,
            schedule.baseline,
            schedule.project,
            schedule.leakage,
            schedule.net,
        )
    ):
        engine_year = result.annual_schedule[idx]
        year_index = idx + 1
        for component, registered, engine_value in (
            ("baseline", reg_be, engine_year.baseline_tco2e),
            ("project", reg_pe, engine_year.project_tco2e),
            ("leakage", reg_le, engine_year.leakage_tco2e),
            ("net", reg_net, engine_year.net_tco2e),
        ):
            rows.append(
                _diff_row(
                    year_index=year_index,
                    year_label=label,
                    component=component,
                    registered=registered.value,
                    engine=engine_value,
                    lineage=f"{registered.sheet}!{registered.cell}",
                    tolerance=tolerance,
                )
            )
    total_registered = sum(v.value for v in schedule.net)
    total_engine = sum(e.net_tco2e for e in result.annual_schedule[: len(schedule.net)])
    total_rel_diff = (total_engine - total_registered) / total_registered
    return ReconcileReport(
        project_name=project_input.project.project_name,
        workbook_path=str(workbook.path),
        tolerance=tolerance,
        rows=rows,
        total_registered=total_registered,
        total_engine=total_engine,
        total_rel_diff=total_rel_diff,
        verdict_pass=abs(total_rel_diff) <= tolerance,
        parameter_mismatches=_parameter_mismatches(
            project_input, workbook, engine_inputs.get("climate_zone")
        ),
        engine_warnings=list(result.warnings),
    )


def render_markdown(report: ReconcileReport) -> str:
    """Render the report as Markdown."""
    verdict = "PASS" if report.verdict_pass else "FAIL"
    lines = [
        f"# Reconcile: {report.project_name}",
        "",
        f"Verdict: **{verdict}** (tolerance {report.tolerance:.0%})",
        "",
        f"Totals (net): registered {report.total_registered:,.1f} tCO2e vs "
        f"engine {report.total_engine:,.1f} tCO2e "
        f"(relative difference {report.total_rel_diff:+.1%})",
        f"Workbook: `{report.workbook_path}`",
        "",
        "| Year | Component | Registered | Engine | Abs diff | Rel diff | Within tol | Lineage |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.rows:
        rel = f"{row.rel_diff:+.1%}" if row.rel_diff is not None else "n/a"
        lines.append(
            f"| {row.year_label} | {row.component} | {row.registered:,.1f} | "
            f"{row.engine:,.1f} | {row.abs_diff:+,.1f} | {rel} | "
            f"{'yes' if row.within_tolerance else 'no'} | {row.lineage} |"
        )
    lines.append("")
    lines.append("## Parameter mismatches")
    lines.append("")
    if report.parameter_mismatches:
        lines.extend(f"- {m}" for m in report.parameter_mismatches)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Engine warnings")
    lines.append("")
    if report.engine_warnings:
        lines.extend(f"- {w}" for w in report.engine_warnings)
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def report_to_dict(report: ReconcileReport) -> dict[str, Any]:
    """Return a JSON-serializable form of the report."""
    return {
        "project_name": report.project_name,
        "workbook_path": report.workbook_path,
        "tolerance": report.tolerance,
        "verdict_pass": report.verdict_pass,
        "total_registered": report.total_registered,
        "total_engine": report.total_engine,
        "total_rel_diff": report.total_rel_diff,
        "rows": [
            {
                "year_index": r.year_index,
                "year_label": r.year_label,
                "component": r.component,
                "registered": r.registered,
                "engine": r.engine,
                "abs_diff": r.abs_diff,
                "rel_diff": r.rel_diff,
                "within_tolerance": r.within_tolerance,
                "lineage": r.lineage,
            }
            for r in report.rows
        ],
        "parameter_mismatches": list(report.parameter_mismatches),
        "engine_warnings": list(report.engine_warnings),
    }
