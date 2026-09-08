"""Build the walkthrough evidence bundle from PHASE-01/02 raw captures.

Reads every file under ``reports/walkthrough/raw/`` plus the two Inegol run
JSONs under ``data/runs/``, calls the live retrieval / prompt / export-gate /
calc-dispatch APIs, and writes exactly one file:
``reports/walkthrough/inegol-evidence.json`` (schema_version "1.0").

Tolerates absent optional raw files by recording ``null`` plus a
``missing_inputs`` list rather than raising. Returns exit code 1 only when a
mandatory input (calc JSON or either run JSON) is missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import structlog
import yaml

logger = structlog.get_logger()

SCHEMA_VERSION = "1.0"
FOCUS_SUBSECTIONS = ["4.1", "3.5", "1.13", "1.1"]
EXPECTED_RAW_FILES = [
    "environment.txt",
    "index-report.json",
    "calc-inegol.json",
    "calc-inegol.txt",
    "draft-noop.json",
    "draft-demo.json",
    "review-noop.txt",
    "review-demo.txt",
    "export-noop-unforced.txt",
    "export-noop-forced.txt",
    "export-demo.txt",
    "packages.json",
    "tinh-3908-hashes.json",
    "tinh-tools.txt",
    "tinh-run.json",
    "tinh-outputs.json",
    "tinh-run-manifest.json",
    "tinh-process-excerpt.md",
    "tinh-execution-status.json",
]
MANDATORY_RAW_FILES = ["calc-inegol.json"]


def _natural_key(sub_section_id: str) -> tuple[int, ...]:
    parts = []
    for piece in str(sub_section_id).split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            return (10**9,)
    return tuple(parts)


def _strip_log_lines(text: str) -> str:
    """Return the JSON payload buried in structlog-decorated stdout."""
    candidates = []
    if text.find("{") >= 0 and text.rfind("}") > text.find("{"):
        candidates.append(text[text.find("{") : text.rfind("}") + 1])
    if text.find("[") >= 0 and text.rfind("]") > text.find("["):
        candidates.append(text[text.find("[") : text.rfind("]") + 1])
    for candidate in candidates:
        try:
            json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return candidate
    return text


def load_raw(raw_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """Parse raw captures keyed by filename stem; list expected-but-absent files."""
    parsed: dict[str, Any] = {}
    missing: list[str] = []
    for name in EXPECTED_RAW_FILES:
        path = raw_dir / name
        stem = Path(name).stem
        key = stem if stem not in parsed else f"{stem}_{Path(name).suffix.lstrip('.')}"
        if not path.exists():
            missing.append(name)
            parsed[key] = None
            continue
        text = path.read_text(encoding="utf-8")
        if name.endswith(".json"):
            try:
                parsed[key] = json.loads(text)
            except json.JSONDecodeError:
                try:
                    parsed[key] = json.loads(_strip_log_lines(text))
                except json.JSONDecodeError:
                    missing.append(name)
                    parsed[key] = None
        else:
            parsed[key] = text
    return parsed, missing


def _review_states_lookup(review_state: dict[str, Any] | None) -> dict[str, Any]:
    states: dict[str, Any] = {}
    if review_state:
        sections = review_state.get("sections", {})
        if isinstance(sections, dict):
            for key, entry in sections.items():
                if isinstance(entry, dict) and "sub_section_id" in entry:
                    states[entry["sub_section_id"]] = entry.get("state")
                elif isinstance(key, str) and "/" in key:
                    sub = key.split("/", 1)[1]
                    states[sub] = entry.get("state") if isinstance(entry, dict) else entry
    return states


def summarize_sections(
    run: dict[str, Any], review_state: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """One summary record per drafted subsection, naturally sorted by id."""
    states = _review_states_lookup(review_state)
    records = []
    for section in run.get("sections", []):
        sub_id = section.get("sub_section_id", "")
        text = section.get("text", "") or ""
        provenance = section.get("provenance", []) or []
        issues = section.get("issues", []) or []
        records.append(
            {
                "sub_section_id": sub_id,
                "heading": section.get("heading", ""),
                "confidence": section.get("confidence"),
                "char_count": len(text),
                "issue_count": len(issues),
                "provenance_count": len(provenance),
                "review_state": states.get(sub_id),
                "has_structured_content": section.get("structured_content") is not None,
            }
        )
    records.sort(key=lambda r: _natural_key(r["sub_section_id"]))
    return records


def focus_sections(
    run: dict[str, Any], sub_section_ids: list[str], max_chars: int = 4000
) -> dict[str, dict[str, Any]]:
    """Truncated text plus full issue/provenance arrays for focus subsections."""
    wanted = set(sub_section_ids)
    result: dict[str, dict[str, Any]] = {}
    for section in run.get("sections", []):
        sub_id = section.get("sub_section_id", "")
        if sub_id not in wanted:
            continue
        text = section.get("text", "") or ""
        result[sub_id] = {
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
            "char_count": len(text),
            "confidence": section.get("confidence"),
            "issues": section.get("issues", []) or [],
            "provenance": section.get("provenance", []) or [],
            "fact_provenance": section.get("fact_provenance", []) or [],
            "synthetic_uses": section.get("synthetic_uses", []) or [],
        }
    return result


def capture_retrieval(sub_section_ids: list[str], family_slug: str = "wte") -> dict[str, Any]:
    """Per-subsection retrieval hits; empty list plus reason when no index."""
    from pdd_agent.retrieval.search import get_examples_for_section

    out: dict[str, Any] = {"family_slug": family_slug, "sections": {}}
    for sub_id in sub_section_ids:
        section_id = sub_id.split(".")[0]
        try:
            hits = get_examples_for_section(
                section_id, sub_section_id=sub_id, document_family=family_slug
            )
        except Exception as exc:
            out["sections"][sub_id] = {"hits": [], "reason": f"{type(exc).__name__}: {exc}"}
            continue
        if not hits:
            out["sections"][sub_id] = {
                "hits": [],
                "reason": "index unavailable or no examples for subsection",
            }
            continue
        out["sections"][sub_id] = {
            "hits": [
                {
                    "document_name": hit.document_name,
                    "canonical_heading": hit.canonical_heading,
                    "score": hit.score,
                    "matched_terms": hit.matched_terms,
                    "from_fallback_family": hit.from_fallback_family,
                    "excerpt": hit.text[:400],
                }
                for hit in hits
            ],
            "reason": None,
        }
    return out


def capture_prompt(project_input_path: Path, sub_section_id: str = "4.1") -> dict[str, Any]:
    """Assembled noop prompt for one subsection, with per-block char counts."""
    from pdd_agent.agent.section_orchestrator import SectionOrchestrator
    from pdd_agent.calc.dispatch import compute_for
    from pdd_agent.llm.provider import NoopProvider
    from pdd_agent.retrieval.search import get_examples_for_section
    from schemas.project_input import ProjectInput

    with open(project_input_path, encoding="utf-8") as f:
        project_input = ProjectInput.model_validate(yaml.safe_load(f))
    section_id = sub_section_id.split(".")[0]
    orchestrator = SectionOrchestrator(
        provider=NoopProvider(), project_input=project_input, run_id="walkthrough-prompt-probe"
    )
    try:
        live_calc = compute_for(project_input)
        if live_calc is None:
            raise ValueError("compute_for returned None")
        orchestrator.set_calc_result(live_calc)
        calc_attached = True
    except Exception as exc:
        logger.warning("walkthrough_prompt_calc_skipped", error=str(exc))
        calc_attached = False
    try:
        examples = get_examples_for_section(section_id, sub_section_id=sub_section_id)
    except Exception:
        examples = []
    try:
        prompt = orchestrator._build_prompt(section_id, sub_section_id, examples, project_input)
        capture_mode = "assembled_text"
    except Exception as exc:
        logger.warning("walkthrough_prompt_fallback", error=str(exc))
        return {
            "sub_section_id": sub_section_id,
            "capture_mode": "component_inventory",
            "reason": f"{type(exc).__name__}: {exc}",
            "char_count": 0,
            "components": [],
            "text": None,
        }
    components: list[dict[str, Any]] = []
    chunks = prompt.split("\n## ")
    if chunks:
        components.append({"block": "preamble", "chars": len(chunks[0])})
        for chunk in chunks[1:]:
            heading = chunk.split("\n", 1)[0].strip()
            components.append({"block": heading, "chars": len(chunk)})
    if len(prompt) > 20000:
        text: str | None = prompt[:8000] + "\n[... elided ...]\n" + prompt[-8000:]
        elided = True
    else:
        text = prompt
        elided = False
    return {
        "sub_section_id": sub_section_id,
        "capture_mode": capture_mode,
        "calc_attached": calc_attached,
        "example_count": len(examples),
        "char_count": len(prompt),
        "elided": elided,
        "components": components,
        "text": text,
    }


def capture_export_gate(
    run: dict[str, Any], project_input_path: Path, calc: dict[str, Any] | None
) -> dict[str, Any]:
    """Hard blocks, required-input/advisory counts, unforced-export verdict."""
    from pdd_agent.calc.dispatch import PddCalcResult
    from pdd_agent.export.docx_export import check_export_gate
    from schemas.project_input import ProjectInput

    with open(project_input_path, encoding="utf-8") as f:
        project_input = ProjectInput.model_validate(yaml.safe_load(f))
    calc_result = PddCalcResult.from_dict(calc) if calc else None
    gate = check_export_gate(run, project_input=project_input, calc_result=calc_result)
    return {
        "blocked": gate.blocked,
        "hard_blocks": gate.hard_blocks,
        "required_inputs_count": len(gate.required_inputs),
        "advisory_count": len(gate.advisories),
        "advisories": gate.advisories[:20],
        "would_export_unforced": not gate.blocked,
    }


def capture_breadth() -> list[dict[str, Any]]:
    """One record per non-ACM0022 engine: gating field plus support presence."""
    from pdd_agent.calc.dispatch import ENGINE_BY_METHODOLOGY

    specs = {
        "VM0051": (
            "pdd_agent.calc.rice_vm0051",
            "technology.rice_cultivation",
            "rules/verra/rice_vm0051_rules.yaml",
            "rice",
        ),
        "VM0044": (
            "pdd_agent.calc.biochar_vm0044",
            "technology.biochar_production",
            "rules/verra/biochar_vm0044_rules.yaml",
            "biochar",
        ),
        "AMS-II.G": (
            "pdd_agent.calc.cookstove_amsiig",
            "technology.cookstove_fleet",
            "rules/verra/cookstove_amsiig_rules.yaml",
            "cookstove",
        ),
    }
    corpus_dir = REPO_ROOT / "data" / "corpus" / "normalized"
    oracle_text = ""
    oracle_path = REPO_ROOT / "tests" / "test_registered_pdd_oracle.py"
    if oracle_path.exists():
        oracle_text = oracle_path.read_text(encoding="utf-8").lower()
    records = []
    for methodology_id in ["VM0051", "VM0044", "AMS-II.G"]:
        module_path, gating_field, rules_rel, family_hint = specs[methodology_id]
        assert ENGINE_BY_METHODOLOGY.get(methodology_id) is not None
        corpus_hit = False
        if corpus_dir.exists():
            for child in corpus_dir.iterdir():
                name = child.name.lower()
                if family_hint in name or methodology_id.lower().replace(".", "") in name:
                    corpus_hit = True
                    break
        records.append(
            {
                "methodology_id": methodology_id,
                "engine_module": module_path,
                "gating_field": gating_field,
                "has_corpus_document": corpus_hit,
                "has_registered_oracle": methodology_id.lower() in oracle_text,
                "review_rules_path": rules_rel,
                "has_review_rules": (REPO_ROOT / rules_rel).exists(),
            }
        )
    return records


def build_reality_checks(index_report: dict[str, Any] | None) -> list[dict[str, str]]:
    """Fixed honest-state statements the page must show on every step."""
    headline = (
        index_report.get("headline_rows", index_report.get("total_rows")) if index_report else None
    )
    reachable = index_report.get("reachable_rows") if index_report else None
    if headline is not None and reachable is not None:
        retrieval_truth = (
            f"Index holds {headline} headline rows but only {reachable} are reachable "
            "through retrieval; the ACM0022 methodology document itself "
            "(EB111_repan07_ACM0022_v03.0) is in missing_documents, so "
            "methodology rules never arrive via retrieval."
        )
    else:
        retrieval_truth = (
            "No index report was captured, so every corpus-backed claim on the "
            "page is unevidenced; treat retrieval as unavailable."
        )
    missing = index_report.get("missing_documents", []) if index_report else []
    missing_truth = (
        f"Missing from the index: {', '.join(missing)}. "
        "Sections citing them fall back to other families or to nothing."
        if missing
        else "Missing-document list unavailable; assume methodology retrieval is incomplete."
    )
    return [
        {
            "id": "no-model-run",
            "claim": "The repository lane shows what the pipeline writes.",
            "truth": (
                "No model-backed drafting run has ever completed in this repository "
                "beyond a single-section smoke test. The noop lane shows placeholders; "
                "the demo lane shows hand-written synthetic prose, not model output."
            ),
            "severity": "material",
        },
        {
            "id": "retrieval-reachability",
            "claim": "Corpus retrieval grounds every section in registered PDDs.",
            "truth": retrieval_truth,
            "severity": "material"
            if reachable is not None and headline != reachable
            else "caution",
        },
        {
            "id": "methodology-not-retrievable",
            "claim": "The methodology document is available to the drafter.",
            "truth": missing_truth,
            "severity": "caution",
        },
        {
            "id": "structured-table-coverage",
            "claim": "Verra tables render for every section that needs one.",
            "truth": (
                "All 11 structured-table renderers are registered in "
                "docx_export._TABLE_RENDERERS, but only 3 of the 36 Inegol sections "
                "(proponent, applicability, ghg_boundary) carry structured_content, "
                "so risk_assessment, sustainable_development and data_gaps tables "
                "are registered yet unexercised by this project."
            ),
            "severity": "info",
        },
        {
            "id": "oracle-xfail",
            "claim": "The calculator is fully cross-validated.",
            "truth": (
                "Two tests in tests/test_registered_pdd_oracle.py remain xfail; "
                "cross-validation against the five reconciled registered projects "
                "(VCS 4818 x2, 5040, 4940, 4921) is recommended follow-up, not done here."
            ),
            "severity": "caution",
        },
        {
            "id": "climate-zone-derived",
            "claim": "Every calc parameter was supplied by the project input.",
            "truth": (
                "calc_climate_zone_resolved: zone=boreal_temperate_wet derived=True — "
                "no location.climate_zone was supplied, so the methane decay-rate "
                "column driving the baseline was inferred from latitude. Open human decision."
            ),
            "severity": "material",
        },
        {
            "id": "tinh-authoring-not-executed",
            "claim": "Both lanes were executed end to end on this machine.",
            "truth": (
                "Only the portable workspace's mechanical packaging was executed "
                "(560-page merged PDF in 224s). The Codex authoring stage "
                "(36-slot prose, citations, attestations) was documented_only, read "
                "from PDD_CREATION_PROCESS.md, never run."
            ),
            "severity": "material",
        },
        {
            "id": "no-assumption-register",
            "claim": "Assumption gating was exercised by this project.",
            "truth": (
                "Inegol has no configs/demo/inegol_project_input.assumptions.yaml, so the "
                "ASSUMPTION-BLOCK/WARN review path is present in "
                "rules/verra/wte_review_rules.yaml but not exercised. Five subsections "
                "(3.4, 3.5, 1.13, 4.1, 4.4) can never auto-approve under WTE rules."
            ),
            "severity": "info",
        },
    ]


def _parse_environment(text: str | None) -> dict[str, Any]:
    env: dict[str, Any] = {"python": None, "platform": None, "pytest_tail": None, "commit": None}
    if not text:
        return env
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "=== python ===" and i + 2 < len(lines):
            env["python"] = lines[i + 1].strip()
            env["platform"] = lines[i + 2].strip()
        if line.strip() == "=== pytest tail ===":
            env["pytest_tail"] = lines[-2].strip() if len(lines) >= 2 else None
        if line.strip() == "=== sha ===" and i + 1 < len(lines):
            env["commit"] = lines[i + 1].strip()
    if env["pytest_tail"] is None and lines:
        for line in reversed(lines):
            if "passed" in line:
                env["pytest_tail"] = line.strip()
                break
    return env


def build_bundle(raw_dir: Path, project_input_path: Path) -> dict[str, Any]:
    """Assemble the complete evidence bundle ready to serialize."""
    from schemas.project_input import ProjectInput

    raw, missing = load_raw(raw_dir)
    with open(project_input_path, encoding="utf-8") as f:
        project_input = ProjectInput.model_validate(yaml.safe_load(f))

    runs: dict[str, dict[str, Any]] = {}
    review_states: dict[str, dict[str, Any] | None] = {}
    for run_id in ["walkthrough-inegol-noop", "walkthrough-inegol-demo"]:
        run_path = REPO_ROOT / "data" / "runs" / f"{run_id}.json"
        runs[run_id] = json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else {}
        if not runs[run_id]:
            missing.append(f"data/runs/{run_id}.json")
        state_path = REPO_ROOT / "data" / "runs" / f"review-state-{run_id}.json"
        review_states[run_id] = (
            json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else None
        )
        if review_states[run_id] is None:
            missing.append(f"data/runs/review-state-{run_id}.json")

    calc = raw.get("calc-inegol")
    noop_run, demo_run = runs["walkthrough-inegol-noop"], runs["walkthrough-inegol-demo"]

    def lane(run: dict[str, Any], provider: str, draft_capture: Any) -> dict[str, Any]:
        timing = draft_capture.get("seconds") if isinstance(draft_capture, dict) else None
        return {
            "provider": provider,
            "timing_seconds": timing,
            "draft_returncode": draft_capture.get("returncode")
            if isinstance(draft_capture, dict)
            else None,
            "sections": summarize_sections(run, None),
            "focus": {},
        }

    drafting = {
        "noop": lane(noop_run, "noop", raw.get("draft-noop")),
        "demo": lane(demo_run, "demo", raw.get("draft-demo")),
    }
    drafting["noop"]["sections"] = summarize_sections(
        noop_run, review_states["walkthrough-inegol-noop"]
    )
    drafting["demo"]["sections"] = summarize_sections(
        demo_run, review_states["walkthrough-inegol-demo"]
    )
    drafting["noop"]["focus"] = focus_sections(noop_run, FOCUS_SUBSECTIONS)
    drafting["demo"]["focus"] = focus_sections(demo_run, FOCUS_SUBSECTIONS)

    def review_summary(run_id: str, txt: str | None) -> dict[str, Any]:
        state = review_states[run_id]
        counts: dict[str, int] = {}
        if state and isinstance(state.get("sections"), dict):
            for entry in state["sections"].values():
                st = entry.get("state", "unknown") if isinstance(entry, dict) else str(entry)
                counts[st] = counts.get(st, 0) + 1
        tail = txt[-1500:] if isinstance(txt, str) else None
        return {
            "state_counts": counts,
            "all_approved": state.get("all_approved") if state else None,
            "stdout_tail": tail,
        }

    packages: dict[str, Any] = {}
    pkg = raw.get("packages") or {}
    for lane_name in ["review", "demo"]:
        rel = pkg.get(lane_name)
        manifest_exists = False
        if rel:
            manifest_exists = (REPO_ROOT / rel / "manifest.json").exists()
        packages[lane_name] = {"path": rel, "manifest_exists": manifest_exists}

    tinh_outputs = raw.get("tinh-outputs") or []
    if isinstance(tinh_outputs, list):
        tinh_outputs = [e for e in tinh_outputs if "lo_profile" not in str(e.get("path", ""))]
    tinh_run = raw.get("tinh-run") or {}
    tinh_manifest = raw.get("tinh-run-manifest") or {}
    tinh_status = raw.get("tinh-execution-status") or {}
    tinh_tools_raw = raw.get("tinh-tools") or ""
    tools: dict[str, str] = {}
    if isinstance(tinh_tools_raw, str):
        for line in tinh_tools_raw.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                tools[key.strip()] = value.strip()
    stages = [
        {
            "name": "00_INPUT manifest",
            "status": "executed",
            "notes": "14 files hashed; see inputs hash table.",
        },
        {
            "name": "mechanical packaging",
            "status": "executed",
            "notes": (
                f"returncode={tinh_run.get('returncode')} "
                f"seconds={tinh_run.get('seconds')}; 139 source pages, 3 workbook PDFs, "
                "560-page merged PDF."
            ),
        },
        {
            "name": "codex authoring (36-slot prose, citations, attestations)",
            "status": "documented_only",
            "notes": tinh_status.get("note", "from PDD_CREATION_PROCESS.md excerpt"),
        },
        {
            "name": "calculation transfer",
            "status": "documented_only",
            "notes": "Workspace attests no new calculation; values transferred with cell lineage.",
        },
    ]

    index_report = raw.get("index-report")
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": {
            "project_name": project_input.project.project_name,
            "vcs_id": project_input.project.project_id_vcs,
            "methodology_ids": list(project_input.technology.methodology_ids),
            "family_slug": "wte",
            "installed_capacity_mw": project_input.technology.installed_capacity_mw,
            "country": project_input.location.country if project_input.location else None,
            "city": project_input.location.city if project_input.location else None,
            "has_evidence_registry": project_input.evidence_registry is not None,
            "has_assumptions_file": False,
        },
        "environment": _parse_environment(raw.get("environment")),
        "repo_lane": {
            "corpus_index": index_report,
            "intake": {
                "input_file": str(project_input_path),
                "project_name": project_input.project.project_name,
                "methodology_ids": list(project_input.technology.methodology_ids),
            },
            "screening": {
                "methodology_id": "ACM0022",
                "engine": "acm0022",
                "family_slug": "wte",
            },
            "calc": calc,
            "retrieval": capture_retrieval(FOCUS_SUBSECTIONS),
            "prompt": capture_prompt(project_input_path),
            "drafting": drafting,
            "judge": {
                "judge_ran": False,
                "reason": "Both lanes ran with --no-judge / no --judge flag; "
                "no LLM judge was executed.",
            },
            "review": {
                "noop": review_summary("walkthrough-inegol-noop", raw.get("review-noop")),
                "demo": review_summary("walkthrough-inegol-demo", raw.get("review-demo")),
            },
            "export_gate": {
                "noop": capture_export_gate(noop_run, project_input_path, calc),
                "demo": capture_export_gate(demo_run, project_input_path, calc),
            },
            "package": packages,
        },
        "tinh_lane": {
            "evidence_grade": "measured",
            "evidence_grade_note": (
                "Mechanical packaging measured on this machine; authoring stage documented_only."
            ),
            "stages": stages,
            "inputs": raw.get("tinh-3908-hashes"),
            "outputs": tinh_outputs,
            "timing_seconds": tinh_run.get("seconds"),
            "tools": tools,
            "process_excerpt": raw.get("tinh-process-excerpt"),
            "known_defects": [
                tinh_status.get("note", ""),
                str(tinh_manifest.get("version_note", "")),
            ],
        },
        "reality_checks": build_reality_checks(index_report),
        "breadth": capture_breadth(),
        "missing_inputs": sorted(set(missing)),
    }
    return bundle


def main() -> int:
    """Write the bundle; return 1 when a mandatory raw input is missing."""
    parser = argparse.ArgumentParser(description="Build the walkthrough evidence bundle")
    parser.add_argument("--raw-dir", default="reports/walkthrough/raw")
    parser.add_argument("--input", default="configs/demo/inegol_project_input.yaml")
    parser.add_argument("--output", default="reports/walkthrough/inegol-evidence.json")
    args = parser.parse_args()

    raw_dir = REPO_ROOT / args.raw_dir
    bundle = build_bundle(raw_dir, REPO_ROOT / args.input)
    for mandatory in MANDATORY_RAW_FILES:
        if (raw_dir / mandatory).exists() is False:
            logger.error("walkthrough_evidence_missing_mandatory", file=mandatory)
            return 1
    if not bundle["repo_lane"]["drafting"]["noop"]["sections"]:
        logger.error("walkthrough_evidence_missing_run", run_id="walkthrough-inegol-noop")
        return 1
    if not bundle["repo_lane"]["drafting"]["demo"]["sections"]:
        logger.error("walkthrough_evidence_missing_run", run_id="walkthrough-inegol-demo")
        return 1
    out = REPO_ROOT / args.output
    payload = json.dumps(bundle, ensure_ascii=False, indent=2)
    out.write_text(payload, encoding="utf-8")
    logger.info("walkthrough_bundle_written", path=str(out), bytes=len(payload.encode("utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
