"""Unit tests for the walkthrough evidence-bundle pure helpers.

Covers only pure functions: no pipeline execution, no network access, and no
dependence on ``data/runs/`` content.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_walkthrough_evidence import (  # noqa: E402
    build_reality_checks,
    capture_breadth,
    focus_sections,
    load_raw,
    summarize_sections,
)


def _section(sub_id: str, **overrides: object) -> dict:
    base = {
        "section_id": sub_id.split(".")[0],
        "sub_section_id": sub_id,
        "text": "abc",
        "confidence": "UNSUPPORTED",
        "issues": ["x"],
        "provenance": [],
        "structured_content": None,
    }
    base.update(overrides)
    return base


def test_summarize_sections_single_record() -> None:
    run = {"sections": [_section("4.1")]}
    (record,) = summarize_sections(run, None)
    assert record["char_count"] == 3
    assert record["issue_count"] == 1
    assert record["provenance_count"] == 0
    assert record["has_structured_content"] is False
    assert record["review_state"] is None


def test_summarize_sections_natural_sort() -> None:
    run = {"sections": [_section("4.10"), _section("4.2"), _section("1.1")]}
    records = summarize_sections(run, None)
    assert [r["sub_section_id"] for r in records] == ["1.1", "4.2", "4.10"]


def test_focus_sections_truncates_long_text() -> None:
    run = {
        "sections": [
            _section(
                "4.1",
                text="x" * 5000,
                issues=[],
                provenance=[],
                fact_provenance=[],
                synthetic_uses=[],
            )
        ]
    }
    result = focus_sections(run, ["4.1"], max_chars=4000)
    assert len(result["4.1"]["text"]) == 4000
    assert result["4.1"]["truncated"] is True


def test_focus_sections_missing_subsection() -> None:
    run = {"sections": [_section("4.1")]}
    assert focus_sections(run, ["9.9"]) == {}


def test_build_reality_checks_empty_index() -> None:
    checks = build_reality_checks(None)
    assert len(checks) >= 6
    for check in checks:
        assert check["id"] and check["claim"] and check["truth"]
        assert check["severity"] in {"info", "caution", "material"}
    assert any(check["severity"] == "material" for check in checks)


def test_build_reality_checks_reports_counts() -> None:
    checks = build_reality_checks(
        {
            "headline_rows": 3026,
            "reachable_rows": 889,
            "documents": 17,
            "reachable_documents": 13,
        }
    )
    assert any("889" in check["truth"] and "3026" in check["truth"] for check in checks)


def test_load_raw_empty_dir(tmp_path: Path) -> None:
    parsed, missing = load_raw(tmp_path)
    assert parsed == {} or all(value is None for value in parsed.values())
    assert missing


def test_capture_breadth_three_engines() -> None:
    records = capture_breadth()
    assert len(records) == 3
    assert {r["methodology_id"] for r in records} == {"VM0051", "VM0044", "AMS-II.G"}
    for record in records:
        assert record["gating_field"].startswith("technology.")
