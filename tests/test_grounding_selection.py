"""Tests for ranked grounding selection (Specification S-1, S-2, S-3)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.grounding import Grounding, ground_section, profile_from_project
from pdd_agent.grounding.selection import exclusion_set, score_chunk
from pdd_agent.retrieval.index import RetrievalIndex
from pdd_agent.retrieval.search import RetrievalResult

ROOT_DIR = Path(__file__).parent.parent.resolve()
SCHEMA_PATH = ROOT_DIR / "schemas" / "pdd_section_schema.yaml"

ALPHA = "A_Alpha_Project-Description.norm"
BETA = "B_Beta_Project-Description.norm"
ZULU = "Z_Zulu_Project-Description.norm"
METHOD = "M_Method.norm"


def _project_input():
    """Duck-typed project input matching the plan's grounding profile."""
    return SimpleNamespace(
        technology=SimpleNamespace(technology_type="combined_wte_ad", methodology_ids=["ACM0022"]),
        location=SimpleNamespace(country="Türkiye"),
        project=SimpleNamespace(project_id_vcs="VCS-3908"),
    )


def _write_norm_doc(path: Path, heading: str, body: str) -> None:
    path.write_text(
        json.dumps(
            {
                "headings": [{"text": heading, "level": 1}],
                "text_blocks": [{"heading": heading, "text": body}],
                "pages": [{"page": 1, "chars": len(body), "text": body}],
            }
        ),
        encoding="utf-8",
    )


def _build_fixture(tmp_path: Path):
    """Build a four-document FTS5 index plus a family config in tmp_path."""
    corpus_dir = tmp_path / "normalized"
    corpus_dir.mkdir()
    _write_norm_doc(
        corpus_dir / f"{ALPHA}.json",
        "3.4 Baseline Scenario",
        "Mass burn incineration plant in China with grate combustion and energy recovery.",
    )
    _write_norm_doc(
        corpus_dir / f"{BETA}.json",
        "3.4 Baseline Scenario",
        "Anaerobic digestion and biogas engines in Turkey under ACM0022 baseline.",
    )
    _write_norm_doc(
        corpus_dir / f"{ZULU}.json",
        "3.4 Baseline Scenario",
        "Anaerobic digestion, biomethanization, biogas and RDF in Turkey, ACM0022.",
    )
    _write_norm_doc(
        corpus_dir / f"{METHOD}.json",
        "ACM0022 Methodology Applicability",
        "Baseline emissions from solid waste disposal sites and ACM0022 "
        "applicability conditions for project activities.",
    )
    cfg = tmp_path / "families.yaml"
    cfg.write_text(
        "default_family: wte\n"
        "documents:\n"
        f"  {ALPHA}: wte\n"
        f"  {BETA}: wte\n"
        f"  {ZULU}: wte\n"
        f"  {METHOD}: wte\n"
        "registry_ids:\n"
        f'  {ZULU}: "3908"\n'
        "methodology_documents:\n"
        f"  - {METHOD}\n",
        encoding="utf-8",
    )
    idx = RetrievalIndex(db_path=tmp_path / "ground.fts.db")
    idx.build(normalized_dir=corpus_dir, schema_path=SCHEMA_PATH)
    return idx, cfg


def test_exclusion_set_matches_digits():
    assert exclusion_set("VCS-3908", {ZULU: "3908"}) == frozenset({ZULU})


def test_exclusion_set_empty_inputs():
    registry = {ZULU: "3908"}
    assert exclusion_set(None, registry) == frozenset()
    assert exclusion_set("", registry) == frozenset()


def test_ground_section_ranks_and_excludes(tmp_path):
    idx, cfg = _build_fixture(tmp_path)
    try:
        grounding = ground_section(
            "3", "3.4", "Baseline Scenario", _project_input(), k=5, index=idx, config_path=cfg
        )
    finally:
        idx.close()
    docs = [r.document_name for r in grounding.precedent]
    assert docs == [BETA, ALPHA]
    assert ZULU not in docs
    assert METHOD not in docs
    assert all(r.score > 0 for r in grounding.precedent)
    beta = grounding.precedent[0]
    assert "family:wte" in beta.matched_terms
    assert "tech:anaerobic digestion" in beta.matched_terms
    assert "country:Türkiye" in beta.matched_terms
    assert "methodology:ACM0022" in beta.matched_terms


def test_ground_section_records_excluded(tmp_path):
    idx, cfg = _build_fixture(tmp_path)
    try:
        grounding = ground_section(
            "3", "3.4", "Baseline Scenario", _project_input(), k=5, index=idx, config_path=cfg
        )
    finally:
        idx.close()
    assert grounding.excluded_documents == [ZULU]


def test_ground_section_caller_override_disables_exclusion(tmp_path):
    idx, cfg = _build_fixture(tmp_path)
    try:
        grounding = ground_section(
            "3",
            "3.4",
            "Baseline Scenario",
            _project_input(),
            k=5,
            index=idx,
            config_path=cfg,
            exclude_documents=(),
        )
    finally:
        idx.close()
    docs = [r.document_name for r in grounding.precedent]
    assert docs[0] == ZULU
    assert BETA in docs


def test_ground_section_normative_channel(tmp_path):
    idx, cfg = _build_fixture(tmp_path)
    try:
        grounding = ground_section(
            "3", "3.4", "Baseline Scenario", _project_input(), k=5, index=idx, config_path=cfg
        )
    finally:
        idx.close()
    assert len(grounding.normative) == 1
    hit = grounding.normative[0]
    assert hit.document_name == METHOD
    assert hit.channel == "normative"
    assert hit.to_dict()["provenance"].startswith(f"[METHODOLOGY: {METHOD}")


def test_score_chunk_damaged_text_penalty(tmp_path):
    profile = profile_from_project(_project_input())
    families = {ALPHA: "wte"}
    score, labels = score_chunk("text with �" * 50, ALPHA, profile, families, False, 0.0)
    assert "damaged-text" in labels
    assert score == 3.0 - 2.0


def test_ground_section_is_deterministic(tmp_path):
    idx, cfg = _build_fixture(tmp_path)
    try:
        first = ground_section(
            "3", "3.4", "Baseline Scenario", _project_input(), k=5, index=idx, config_path=cfg
        )
        second = ground_section(
            "3", "3.4", "Baseline Scenario", _project_input(), k=5, index=idx, config_path=cfg
        )
    finally:
        idx.close()

    def _key(grounding: Grounding):
        return [(r.document_name, r.score, tuple(r.matched_terms)) for r in grounding.precedent]

    assert _key(first) == _key(second)


def test_ground_section_unbuilt_index_returns_empty(tmp_path):
    idx = RetrievalIndex(db_path=tmp_path / "none.db")
    try:
        assert ground_section("3", "3.4", "Baseline Scenario", _project_input(), index=idx) == (
            Grounding([], [], [], False)
        )
    finally:
        idx.close()


def test_prompt_header_uses_subsection_label():
    orch = SectionOrchestrator()
    prompt = orch._build_prompt("4", "4.1", [])
    assert "(4.1)" in prompt
    assert "4.4.1" not in prompt


def test_prompt_normative_block_before_precedent():
    orch = SectionOrchestrator()
    precedent = RetrievalResult(
        section_id="4",
        sub_section_id="4.1",
        document_name=BETA,
        canonical_heading="Baseline Scenario",
        text="Precedent text.",
        content_class="",
        review_sensitivity="",
        score=7.25,
        matched_terms=["family:wte"],
    )
    normative = RetrievalResult(
        section_id="",
        sub_section_id="",
        document_name=METHOD,
        canonical_heading="Applicability",
        text="Methodology text.",
        content_class="",
        review_sensitivity="",
        score=0.9,
        matched_terms=["methodology:ACM0022"],
        channel="normative",
    )
    prompt = orch._build_prompt("4", "4.1", [precedent], None, normative=[normative])
    assert prompt.index("## Methodology Requirements (normative)") < prompt.index(
        "## Precedent Evidence (ranked by project similarity)"
    )
