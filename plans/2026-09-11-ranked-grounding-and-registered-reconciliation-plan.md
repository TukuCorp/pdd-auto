---
title: "Ranked Grounding and Registered Reconciliation: retrieve what is relevant, and check the arithmetic against a registered workbook"
date: "2026-09-11"
status: "draft"
request: "Implement research/2026-09-11-pdd-ranked-grounding-and-registered-reconciliation-brainstorm.md: hygiene opener (blocked-export exit code, --help UTF-8 crash, test isolation from data/runs), Track A grounding (parser TOC fix for text/plain docs, zero-row warning, ranked similarity selection, self-exclusion, normative methodology channel, prompt header numbering, grounding/ module), Track B Inegol reconciliation (climate zone no wet/dry guessing + declared dry zone, ER workbook mapper with lineage, per-year throughput, Inegol year-by-year oracle, duplicate-key YAML loader), Track C pdd-agent reconcile."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-09-11-pdd-ranked-grounding-and-registered-reconciliation-brainstorm.md"
  - "research/2026-08-27-pdd-assembly-and-defensible-numbers-brainstorm.md"
---

# Plan: Ranked Grounding and Registered Reconciliation

## Objective

Make the drafting pipeline ground every section on precedent chosen for its relevance to the
project, never on the project's own registered PDD, and, for the first time, on the ACM0022
methodology text itself. In parallel, make the ACM0022 calculation engine reproduce the
registered Inegol (VCS 3908) project year by year from parameters read out of that project's own
registered calculation workbook. Expose that comparison as a `pdd-agent reconcile` command. Both
matter now because the pipeline has made no real-model run yet (the survivability work that gates
one is done), and a real run spent on today's grounding would be ungradeable.

## Context Snapshot

- **Current state:**
  - `src/pdd_agent/retrieval/search.py::get_examples_for_section()` is the only precedent entry
    point the orchestrator uses. It is explicitly "non-ranked": it hard-codes `score=0.0` and
    `matched_terms=[]`, and the SQL in `src/pdd_agent/retrieval/index.py::get_section_examples()`
    orders by `doc_rank, document_name`. Every section is therefore grounded on the first five
    documents alphabetically. For Inegol those are `VCS_Bergama`, `VCS_DRAFT_Yanjiang`,
    `VCS_Guangzhou`, `VCS_Guanxi_Zhuang` and `VCS_Inegol`, which includes the project's own
    registered PDD.
  - The retrieval index (`data/index/corpus.fts.db`) contains 13 of 17 normalized documents. The
    four `text/plain` documents (`EB111_repan07_ACM0022_v03.0` = the ACM0022 methodology,
    `DraftProjectDescription`, `Bergama_VCS-Joint-Project-Description-Monitoring-Report-v4.2`,
    `VCS-Project-Description-HEREKO-v4.1_2022-10-24`) produce **zero** section spans in
    `src/pdd_agent/parse/section_parser.py::parse_document()`. Their normalized record holds the
    whole document as a single "page" and their headings carry no `page` key, so every heading
    defaults to page 1. Page 1 contains "CONTENTS", `_is_toc_page()` returns True, and every
    heading is skipped. The indexer drops documents with zero rows without logging anything.
  - `src/pdd_agent/agent/section_orchestrator.py` never calls `search()`, so there is no normative
    (methodology) channel. The prompt header at line ~616 formats
    `f"({section_id}.{sub_section_id})"`, but `sub_section_id` is already `"4.1"`, so the model is
    told it is writing section "4.4.1".
  - `src/pdd_agent/calc/constants.py::climate_zone_for()` can only return `tropical_wet` or
    `boreal_temperate_wet`; it never returns a dry zone. The registered Inegol ER workbook uses
    exactly the engine's `boreal_temperate_dry` decay rates (wood 0.02, paper 0.04, food 0.06,
    textiles 0.04, garden 0.05 per year). The engine derives `boreal_temperate_wet` and computes a
    7-year total of 893,441 tCO2e against the registered 730,000 (+22.4%). Declaring
    `boreal_temperate_dry` moves it to 594,306 (−18.6%), measured on 2026-09-11.
  - `src/pdd_agent/calc/cdm_tool_04.py::methane_from_swds()` assumes a **constant** annual waste
    deposit. Inegol's registered waste grows every year (299,300 t in 2021 to 547,500 t in 2026).
  - `configs/demo/inegol_project_input.yaml` defines `technology.biomethanization_suitable_fraction`
    twice (`0.35` with an assumption comment, then `0.45` with none). PyYAML silently keeps
    `0.45`, and no loader rejects duplicate keys.
  - `pdd-agent export` prints `Export blocked: …` and exits 0 when the export gate blocks.
    `pdd-agent --help` crashes with `UnicodeEncodeError` on a cp1252 console because the `ingest`
    help string contains `→`. A full test run writes about 57 new `run-*.json` files into the
    production run store `data/runs/`.
  - Suite baseline: `974 passed, 7 deselected, 2 xfailed` (the 2 xfails are
    `TestInegolOracle::test_annual_net_within_tolerance` and
    `TestInegolOracle::test_crediting_period_total_within_tolerance` in
    `tests/test_registered_pdd_oracle.py`, both `strict=True`).
- **Desired state:**
  - All 17 normalized documents contribute rows to the index. `EB111_repan07_ACM0022_v03.0`
    has more than 0 rows, and the indexer warns about any document that yields zero rows.
  - A new `src/pdd_agent/grounding/` package selects precedent by a deterministic similarity score
    (documented in `## Specification` S-1). It excludes the project's own registered PDD, retrieves
    methodology text through a separate normative channel, and records a non-zero `score` and
    human-readable `matched_terms` for every selected chunk. The orchestrator calls it once per
    section.
  - The prompt header names the correct subsection number.
  - The climate-zone resolver warns whenever it derives a zone rather than silently guessing wet
    vs dry. The engine accepts an optional per-year waste deposit schedule and an optional per-year
    electricity schedule. Project-input YAML with duplicate keys fails to load.
  - A registered-workbook reader extracts the Inegol ER workbook's parameters and year-by-year
    schedule with sheet/cell lineage. The Inegol config is re-sourced from it, and a year-by-year
    Inegol oracle test exists.
  - `pdd-agent reconcile` recomputes a project and writes a per-year, per-component diff against
    its registered workbook.
  - `pdd-agent export` exits 2 on a block. `pdd-agent --help` works on cp1252. The test suite
    writes nothing into `data/runs/`.
- **Key repo surfaces:**
  - `src/pdd_agent/cli.py` (argparse subcommands; `main()` dispatch dict at line ~459;
    `_run_export` at line ~888)
  - `src/pdd_agent/parse/section_parser.py` (`parse_document`, nested `_is_toc_page`,
    `_find_content_page`)
  - `src/pdd_agent/retrieval/index.py` (`RetrievalIndex.build`, `.search`, `.get_section_examples`,
    `load_family_map`-style loading of `configs/corpus_families.yaml` at line ~53)
  - `src/pdd_agent/retrieval/search.py` (`RetrievalResult`, `search`, `get_examples_for_section`,
    `get_section_heading_examples`)
  - `src/pdd_agent/agent/section_orchestrator.py` (`draft_section` at line ~756, `_build_prompt` at
    line ~597, `_format_retrieval_results` at line ~481, a second retrieval call near line ~1204)
  - `src/pdd_agent/calc/constants.py`, `src/pdd_agent/calc/cdm_tool_04.py`,
    `src/pdd_agent/calc/acm0022.py`, `src/pdd_agent/calc/models.py`, `src/pdd_agent/calc/dispatch.py`
  - `schemas/project_input.py` (`ProjectLocation.climate_zone`, `ProjectTechnology`)
  - Run-store defaults: `src/pdd_agent/llm/provider.py` (`DraftRun.save/load`),
    `src/pdd_agent/review/states.py` (`ReviewStateStore.save/load`),
    `src/pdd_agent/export/docx_export.py` (`_DRAFT_RUNS_DIR`), `src/pdd_agent/export/drive_upload.py`,
    `src/pdd_agent/phase05/benchmark.py` (`_DEFAULT_RUNS_DIR`), `src/pdd_agent/service/main.py`
    (`RUNS_DIR`, `_runs_dir`, `_service_runs_dir`), `src/pdd_agent/agent/section_orchestrator.py`
    (`Path("data/runs")` at lines ~1120 and ~1166)
  - `configs/corpus_families.yaml`, `configs/demo/inegol_project_input.yaml`
  - `tests/test_registered_pdd_oracle.py`, `tests/test_retrieval_search.py`,
    `tests/test_section_parser.py`, `tests/test_section_orchestrator.py`,
    `tests/test_prompt_assembly.py`
- **Out of scope:**
  - Any real-model (paid or `claude-code`) drafting run. No API spend of any kind.
  - Embedding or LLM-based reranking.
  - Fixing corpus encoding damage (U+FFFD) or the mojibake document stem `VCS_Ã_demis`.
    Retrieval only *penalizes* damaged chunks.
  - Citation resolution (`[CORPUS: …]` / `[CALC: …]` verification), the LLM coherence pass, and
    prompt caching.
  - Replacing the 29 `Path(__file__).parent.parent.parent.parent` asset lookups outside the
    run-store defaults listed above; packaging data files into the wheel.
  - `run_id` validation in the service.
  - A DOCX appendix for the reconcile report (Markdown and JSON only).
  - Regenerating committed `reports/demo-packages/` or `reports/review-packages/` artifacts.
  - Changing `TOLERANCE = 0.20` in `tests/test_registered_pdd_oracle.py`.

## Environment & Conventions

- **Stack:** Python 3.11+ (CI matrix 3.11 and 3.12; local development has used 3.13). Pydantic v2,
  structlog, PyYAML, openpyxl (a core dependency), python-docx, FastAPI, SQLite FTS5. A committed
  `uv.lock` is checked in CI. Build backend: hatchling.
- **Setup:**
  ```bash
  pip install -e ".[dev,service,export,llm,ingest]"
  ```
  or, with uv:
  ```bash
  uv sync --locked --all-extras
  ```
- **Build / Run:** no build step. The CLI entry point is `pdd-agent` (`src/pdd_agent/cli.py::main`).
  ```bash
  pdd-agent doctor
  pdd-agent build-index
  pdd-agent index-report --json
  pdd-agent calc --input configs/demo/inegol_project_input.yaml
  ```
- **Test:** full suite:
  ```bash
  python -m pytest -m "not corpus" -q
  ```
  single file:
  ```bash
  python -m pytest tests/test_registered_pdd_oracle.py -v
  ```
  single test:
  ```bash
  python -m pytest "tests/test_registered_pdd_oracle.py::TestInegolOracle::test_crediting_period_total_within_tolerance" -v
  ```
  Tests marked `corpus` need local-only data (`data/corpus/normalized/` or git-ignored
  workbooks) and are excluded by `-m "not corpus"`. Tests must never require API keys, network
  access, or a running Ollama instance; mock all HTTP.
- **Lint / format gates** (CI runs all three; all must pass):
  ```bash
  ruff check .
  ruff format --check .
  uv lock --check
  ```
- **Conventions & traps:**
  - Ruff, line length 100. structlog event-style logging: `logger.warning("event_name", key=value)`.
  - Pydantic v2 for `ProjectInput` (`schemas/project_input.py`, a top-level package **outside**
    `src/`, imported as `from schemas.project_input import ProjectInput`) and for calc-engine
    inputs (`src/pdd_agent/calc/models.py`). Use dataclasses everywhere else.
  - Units: waste masses in **tonnes per year (wet basis)**; emissions in **tCO2e per year**;
    electricity in **MWh per year**; grid emission factor in **tCO2/MWh**; FOD decay rate `k` in
    **1/year**; DOC as a **fraction 0–1** (the registered workbook writes DOC as a percentage,
    e.g. `43` = 0.43). Mass fractions are dimensionless 0–1, never percentages.
  - Backward compatibility: every existing `configs/**/*.yaml` project config must keep validating.
    Every new `ProjectInput` field is optional, with a default (`None`) that preserves today's
    behaviour.
  - On Windows, set `PYTHONIOENCODING=utf-8` before piping CLI output. If the shell has a
    machine-level `PYTHONPATH` pointing into a different virtualenv, clear it for commands in this
    repo (for example `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q`).
  - `data/corpus/`, `data/index/` and `data/runs/` are git-ignored. Never commit their contents.
  - The two Inegol oracle xfails are `strict=True`: if a change makes them pass, pytest reports
    `XPASS(strict)` as a **failure**, which is the signal to remove the decorator.
  - Exit-code convention for this plan: `0` success, `1` unexpected error (already produced by
    `main()`'s exception handler), `2` refused by a gate (budget, export block), `3` reconcile
    finished but a crediting-period total is outside tolerance.
- **Repo map:**
  ```
  src/pdd_agent/cli.py         argparse CLI; main() maps subcommand -> _run_* handler, returns int
  src/pdd_agent/parse/         section_parser.py: .norm.json -> section_spans / sections_mapped
  src/pdd_agent/retrieval/     index.py (FTS5 build/search), search.py (RetrievalResult, entry points)
  src/pdd_agent/grounding/     NEW: precedent + normative selection for one section
  src/pdd_agent/agent/         section_orchestrator.py: retrieval, prompt assembly, drafting loop
  src/pdd_agent/calc/          ACM0022 engine, CDM tools, constants, dispatch from ProjectInput
  src/pdd_agent/reconcile/     NEW: registered-workbook reader + engine-vs-registered diff
  schemas/project_input.py     ProjectInput (Pydantic)
  configs/corpus_families.yaml corpus document stem -> methodology family (+ new keys, PHASE-03)
  configs/demo/inegol_project_input.yaml   the Inegol (VCS 3908) project input
  tests/                       pytest suite (no conftest.py exists yet; PHASE-01 creates one)
  ```

## Research Inputs

- From `research/2026-09-11-pdd-ranked-grounding-and-registered-reconciliation-brainstorm.md`:
  - Retrieval is an alphabetical sort. In the captured Inegol evidence bundle, both the retrieval
    hits and the drafted `[CORPUS: …]` citations come uniformly from exactly the first five
    documents alphabetically (4 hits and 12 citations each), including `VCS_Inegol`. Damaged text
    is over-selected because `VCS_DRAFT_Yanjiang` (1,629 U+FFFD characters) sorts early.
  - The four text/plain documents parse to 0 `section_spans` with 71–106 mapped headings, all with
    empty `text_preview`. The root cause is the TOC-page test on a single-page record whose headings
    lack a `page` key. The existing fallback branch for these documents never runs because blocks
    and headings now align.
  - The registered Inegol ER workbook's *Waste Parameters* sheet matches the engine's
    `boreal_temperate_dry` k column exactly. Measured on Inegol: derived wet → +22.4%;
    declared dry → −18.6%; dry plus 59,455.872 MWh/yr → −13.6%. The remaining residual is
    structural: growing waste deposits, back-loaded baseline, growing project emissions.
  - Registered Inegol schedule (*SUMMARY (ER)*), years 2021–2027: BE
    `[10167, 43251, 72738, 102035, 140719, 189144, 247313]` (sum 805,367), PE
    `[5809, 8088, 9849, 11316, 12294, 13272, 14739]` (sum 75,367), leakage 0, ER
    `[4358, 35163, 62889, 90719, 128425, 175872, 232574]` (sum 730,000, average 104,285). A
    one-day 2020-12-31 stub row (BE 14, PE 16, ER −2) is excluded from the published totals.
  - The duplicate `biomethanization_suitable_fraction` key silently overrides a documented
    assumption. Switching to the commented 0.35 moves the 7-year total by +1.8 percentage points.
  - Assumptions adopted there and lifted here: deterministic ranking before embeddings;
    self-exclusion on by default; climate zone declared and sourced rather than derived from a
    dataset; `TOLERANCE` unchanged; no spend.
- From `research/2026-08-27-pdd-assembly-and-defensible-numbers-brainstorm.md`:
  - Oracle discipline: parameters must come from a registered source (an IPCC table, a registered
    PDD table or workbook), never be fitted to make a test pass. When a sourced value disagrees
    with a target, the source wins and the residual is recorded as a dated measurement.
  - The methodology rows lose on BM25 when their `canonical_heading` is the document filename.
    Section-sized chunks with real headings are the precondition for a normative channel.

## Assumptions and Constraints

- **ASM-001:** The registered Inegol ER workbook is available locally at
  `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/inputs/fresh_registry/verra_public_download_3908_20260824/project_3908/extracted/ER Calculation.v04_21.07.2025.xlsx`
  (git-ignored). — **BINDING DEFAULT:** code and tests locate it through the environment variable
  `PDD_INEGOL_ER_WORKBOOK`, falling back to that path. Any test that reads the real file is
  marked `@pytest.mark.corpus` and calls `pytest.skip` when the file is absent. All non-corpus
  tests build a synthetic workbook with openpyxl in `tmp_path`.
- **ASM-002:** Which column of the workbook is "electricity displaced". — **BINDING DEFAULT:** read
  the per-year MWh series from the *Project Emissions* sheet column whose header cell text starts
  with `ECBL` (values 8,395.389 / 43,872.46 / 59,455.872 ×5 for 2021–2027). Validate it by checking
  that `MWh × 0.541 × 1.09101` reproduces the *Baseline Emissions (Total)* sheet's "separated"
  column to within ±1 tCO2e per year. If the check fails, the reader raises `ValueError` naming both
  cells.
- **ASM-003:** Inegol's `biomethanization_suitable_fraction`. — **BINDING DEFAULT:** `0.4312`, the
  ratio of the *Waste Projection* sheet's "Biomethanization" column to its "Total Waste (A)" column
  (129,058.16 / 299,300 = 0.4312 in 2021, the same ratio in every year). Remove both the `0.35`
  and `0.45` lines, and write one line with a YAML comment citing sheet and column.
- **ASM-004:** Composition to use for Inegol. — **BINDING DEFAULT:** the *Waste Projection* sheet's
  facility-level column ("At the Integrated Solid …"): wood 0.0414, paper_cardboard 0.0569,
  food_waste 0.5276, textiles 0.1709, garden_waste 0.0114, inert 0.1918. `inert` is deliberately
  not a key in `DOC_BY_WASTE_TYPE` and contributes no BE_CH4, the same convention the committed Soc
  Son config uses.
- **ASM-005:** How to match the project's own registered PDD in the corpus. — **BINDING DEFAULT:**
  add a `registry_ids:` mapping to `configs/corpus_families.yaml` (document stem → VCS id as a
  digit string): `VCS_Inegol_Project-Description.norm: "3908"` and
  `VCS_Soc_Son_Project-Description.norm: "2567"`. A project id is normalized by stripping every
  non-digit (`"VCS-2567"` → `"2567"`). No other stems get ids in this plan.
- **ASM-006:** Which documents form the normative channel. — **BINDING DEFAULT:** add a
  `methodology_documents:` list to `configs/corpus_families.yaml` containing exactly
  `EB111_repan07_ACM0022_v03.0.norm`. These documents are excluded from the precedent pool and
  searched only by the normative channel.
- **ASM-007:** The one-day 2020-12-31 stub row in the registered schedule. — **BINDING DEFAULT:**
  the reader skips any schedule row whose *Days* cell is below 300. The engine's crediting year 1
  is the 2021 calendar year. No pre-crediting deposit is modelled.
- **ASM-008:** The per-year schedules cover more or fewer years than `crediting_period_years`.
  — **BINDING DEFAULT:** a shorter list carries its last value forward, the same rule
  `capacity_ramp` uses. A longer list is truncated with a dispatch warning.
- **ASM-009:** Inegol's transmission/distribution-loss adjustment (the registered BE_EC multiplies
  by 1.09101). — **BINDING DEFAULT:** not modelled in this plan. The Inegol config's scalar
  `energy_generation_mwh_year: 49935.315` stays unchanged so that
  `TestInegolOracle::test_displaced_grid_electricity_matches_registered_factor` keeps passing. The
  TDL residual is recorded in the reconcile report as a parameter mismatch.
- **ASM-010:** Precedent `k` (examples per section). — **BINDING DEFAULT:** unchanged; the
  orchestrator's existing `self._max_corpus_examples()` value. The normative channel adds up to 3
  more chunks per section.
- **CON-001:** No API keys, network access, or real-model calls anywhere in this plan's tasks or
  tests.
- **CON-002:** `TOLERANCE = 0.20` in `tests/test_registered_pdd_oracle.py` must not change. A
  strict xfail is removed only when its test genuinely passes.
- **CON-003:** `get_examples_for_section()` keeps its current signature and behaviour. It is still
  used by `scripts/build_walkthrough_evidence.py` and by tests. The orchestrator stops calling it.
- **CON-004:** Existing configs other than `configs/demo/inegol_project_input.yaml` and
  `configs/corpus_families.yaml` are not edited.
- **DEC-001:** Ranking is deterministic, feature-based plus a BM25 component (S-1). No embedding
  model is added.
- **DEC-002:** Self-exclusion of the project's own registered PDD is **on by default** whenever the
  project's VCS id matches a `registry_ids` entry. An explicit empty `exclude_documents=()` passed
  by a caller turns it off.
- **DEC-003:** The climate-zone resolver keeps returning today's derived value for undeclared zones
  (to avoid moving Soc Son or the demo configs) but always emits a
  `calc_climate_zone_ambiguous` warning when it derives. Inegol declares its zone.
- **DEC-004:** `TestInegolOracle::test_annual_net_within_tolerance` compares like with like: the
  **mean** of `annual_schedule[*].net_tco2e` against the registered average 104,285. Today it
  compares the year-1 scalar against a 7-year average.
- **DEC-005:** New code lives in two new packages, `src/pdd_agent/grounding/` and
  `src/pdd_agent/reconcile/`. The orchestrator gains no new selection logic of its own.

## Specification

### S-1: Precedent similarity score

For one section (`section_id`, `sub_section_id`) and one project, the candidate pool is every row
returned by `RetrievalIndex.get_section_examples(section_id, sub_section_id, document_family=family,
k=50)`, excluding rows whose `document_name` is in the exclusion set (S-3) or in
`methodology_documents`. If the family-filtered pool is empty, repeat without the family filter
and mark every result `from_fallback_family=True` (today's fallback semantics).

For each candidate chunk `c` from document `d`:

```
score(c) = 3.0 * F(d) + 2.0 * T(c) + 1.0 * C(d) + 1.0 * M(c) + 1.0 * B(c) - 2.0 * D(c)
```

- `F(d)` = 1 if the document's family (from `configs/corpus_families.yaml`) equals the project's
  family slug (`family_slug_for(project.technology.methodology_ids)`), else 0.
- `T(c)` = 1 if the chunk text contains, case-insensitively, any keyword in
  `TECHNOLOGY_KEYWORDS[project.technology.technology_type]`, else 0. The table:
  - `combined_wte_ad` → `["anaerobic digestion", "biomethan", "biogas", "refuse derived", "rdf"]`
  - `anaerobic_digestion` → `["anaerobic digestion", "biogas", "digester"]`
  - `incineration_with_energy_recovery` → `["incinerat", "waste-to-energy", "mass burn", "combustion"]`
  - `landfill_gas_capture` → `["landfill gas", "lfg", "flare"]`
  - `refuse_derived_fuel` → `["refuse derived", "rdf"]`
  - `mechanical_biological_treatment` → `["mechanical biological", "mbt"]`
  - every other value → `[]`
- `C(d)` = 1 if the document mentions the project's country anywhere in the index (FTS `MATCH` on
  the country name, restricted to `document_name = d`), else 0. Country aliases: `Türkiye` ↔
  `Turkey`, `Viet Nam` ↔ `Vietnam`. Matching is on any alias.
- `M(c)` = 1 if the chunk text contains any of the project's `methodology_ids` (e.g. `ACM0022`),
  else 0.
- `B(c)` = rank-normalized BM25. Run `RetrievalIndex.search(query, section_id=section_id, k=50)`
  with `query` = the technology keywords plus methodology ids joined by `" OR "` (each multi-word
  keyword wrapped in double quotes). If `c` is hit at 0-based rank `r` of `n` hits,
  `B(c) = 1 - r / n`; if not hit, `B(c) = 0`.
- `D(c)` = 1 if the chunk's U+FFFD ratio (count of `"\ufffd"` / `len(text)`) is above `0.005`,
  else 0.

Selection, in order:

1. Sort candidates by `score` descending, then `document_name` ascending, then `chunk_index`
   ascending (fully deterministic).
2. First pass: take the highest-scoring chunk from each distinct document until `k` chunks are
   chosen.
3. Second pass (only if fewer than `k`): take remaining chunks in sorted order.
4. For each selected chunk, set `RetrievalResult.score = score(c)` and `matched_terms` to the list
   of feature labels that fired, in this fixed order and format: `family:<slug>`,
   `tech:<first matching keyword>`, `country:<country as written in ProjectInput>`,
   `methodology:<id>`, `bm25:<B rounded to 2 dp>`, `damaged-text`.

### S-2: Normative channel

1. If `methodology_documents` is empty, return `[]`.
2. Build `query` = the section heading's words (lower-cased, words of length ≥ 4, stop-words
   removed) plus the project's `methodology_ids`, joined by `" OR "`.
3. Call `RetrievalIndex.search(query, document_names=methodology_documents, k=3)`. There is no
   `section_id` filter: methodology rows carry `section_id=""`.
4. Return the hits as `RetrievalResult` with `channel="normative"`. They are injected under a
   `## Methodology Requirements (normative)` prompt heading placed **before** the precedent block,
   and recorded in provenance as `[METHODOLOGY: <document_name>, <canonical_heading>]`.

### S-3: Self-exclusion

1. `project_vcs = re.sub(r"\D", "", project.project.project_id_vcs or "")`.
2. If `project_vcs` is empty, the exclusion set is empty.
3. Otherwise, the exclusion set is every stem `s` in `registry_ids` with
   `registry_ids[s] == project_vcs`.
4. A caller-supplied `exclude_documents` replaces steps 1–3 entirely (use `()` to disable).
5. Every excluded stem is logged once per section as
   `logger.info("grounding_self_excluded", document=..., section_id=...)` and recorded in
   `Grounding.excluded_documents`.

### S-4: FOD with a per-year deposit

Tool 04 Eq. 2, with the constant deposit `W` generalised to a per-year series:

```
BE_CH4,y = φ · (1 − f_y) · GWP_CH4 · (1 − OX) · (16/12) · F · DOC_f · MCF
           · Σ_{x=1..y} Σ_j  W_j,x · DOC_j · e^(−k_j · (y − x)) · (1 − e^(−k_j))
```

- `y` = crediting-period year being calculated (1-based). `x` = deposit year (1-based).
- `W_j,x` = tonnes of waste type `j` diverted from the SWDS in year `x`:
  `annual_tonnes_by_year[x−1] × swds_diversion_fraction` when a per-year series is supplied (last
  value carried forward past its end), else the constant `annual_tonnes × swds_diversion_fraction`
  (today's behaviour, byte-identical results).
- `k_j` = decay rate for type `j` in 1/year from `DECAY_RATE_BY_CLIMATE_ZONE[zone]`.
- `DOC_j` = degradable organic carbon fraction for type `j`.
- `φ, f_y, OX, F, DOC_f, MCF, GWP_CH4` = the engine's existing parameters (unchanged).

For year `y`, every other waste-mass-dependent term (biogas / AD project emissions, incineration)
uses that year's mass `annual_tonnes_by_year[y−1]`. BE_EC uses `energy_generation_mwh_by_year[y−1]`
when supplied. `capacity_ramp` and a per-year series are mutually exclusive: `ProjectTechnology`
rejects a config that sets `capacity_ramp` together with `annual_waste_by_year`.

### S-5: Climate-zone inference from registered decay rates

`infer_climate_zone(decay_rates)` receives the workbook's `k` per engine waste type (only
`wood`, `paper_cardboard`, `food_waste`, `textiles`, `garden_waste`). It returns the single zone in
`DECAY_RATE_BY_CLIMATE_ZONE` whose table matches **all** supplied values within `1e-9`, and `None`
if zero or more than one zone matches.

### S-6: Reconcile verdict

1. For each crediting year `i` (1-based) and component in (`baseline`, `project`, `leakage`,
   `net`), compute `abs_diff = engine − registered` and
   `rel_diff = abs_diff / registered` (`None` when `registered == 0`).
2. Per-row `within_tolerance` = `rel_diff is None or abs(rel_diff) <= tolerance`. Rows are
   informational: early crediting years have small denominators.
3. The **verdict** uses only the crediting-period totals of `net`:
   `abs(total_engine − total_registered) / total_registered <= tolerance`.
4. CLI exit code: `0` if the verdict passes, `3` if it fails, `1` on any exception.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Hygiene opener: honest exit codes, a crash-free `--help`, a test suite that stays out of `data/runs/` | None | `src/pdd_agent/paths.py`, `tests/conftest.py`, `tests/test_cli_hygiene.py`, export exit 2 |
| PHASE-02 | Get the ACM0022 methodology and the other text/plain documents into the index | PHASE-01 (recommended, not required) | Parser fix, zero-row warning, 17/17 documents indexed |
| PHASE-03 | Ranked, self-excluding precedent plus a normative methodology channel, behind a `grounding/` module | PHASE-02 | `src/pdd_agent/grounding/`, orchestrator wiring, prompt header fix |
| PHASE-04 | Honest climate zones, per-year deposit and electricity schedules, duplicate-key-rejecting YAML | PHASE-01 | Engine and schema changes, `src/pdd_agent/config_io.py` |
| PHASE-05 | Read the registered Inegol workbook with lineage, re-source the Inegol config, add a year-by-year Inegol oracle | PHASE-04 | `src/pdd_agent/reconcile/workbook.py`, updated Inegol config, `TestInegolAnnualSchedule` |
| PHASE-06 | `pdd-agent reconcile` and the documentation resync | PHASE-05 | `src/pdd_agent/reconcile/diff.py`, `reconcile` subcommand, README updates |

PHASE-02/03 (grounding) and PHASE-04/05/06 (reconciliation) are independent tracks and may be
executed in either order after PHASE-01.

## Detailed Phases

### PHASE-01 - Hygiene Opener

**Goal**
Make `pdd-agent export` report a block through its exit code, make `pdd-agent --help` work on a
cp1252 console, and route every default run-store path through one resolver, so the test suite can
be pointed at a temporary directory and never writes into `data/runs/`.

**Tasks**
- [ ] TASK-01-01: Record the baseline run-store count before any change:
  `python -c "import pathlib; print(len(list(pathlib.Path('data/runs').glob('*.json'))))"`. Keep
  the number for the exit criteria.
- [ ] TASK-01-02: Create `src/pdd_agent/paths.py` with `repo_root()` and `default_runs_dir()`
  (signatures below). `default_runs_dir()` returns `Path(os.environ["PDD_RUNS_DIR"])` when that
  variable is set and non-empty, else `repo_root() / "data" / "runs"`.
- [ ] TASK-01-03: Replace every hard-coded default run-store path with a call to
  `default_runs_dir()` **at call time** (never at import time):
  `src/pdd_agent/llm/provider.py` (`DraftRun.save` and `DraftRun.load`),
  `src/pdd_agent/review/states.py` (`ReviewStateStore.save` and `.load`),
  `src/pdd_agent/export/docx_export.py` (`_DRAFT_RUNS_DIR`: replace the module constant with a
  call inside `export_run_to_docx` where `effective_runs_dir = runs_dir or default_runs_dir()`),
  `src/pdd_agent/export/drive_upload.py` (line ~115),
  `src/pdd_agent/phase05/benchmark.py` (`_DEFAULT_RUNS_DIR`: resolve at call time),
  `src/pdd_agent/agent/section_orchestrator.py` (the two `Path("data/runs")` fallbacks near lines
  1120 and 1166). In `src/pdd_agent/service/main.py`, `_runs_dir()` and `_service_runs_dir()` keep
  honouring `PDD_SERVICE_RUNS_DIR` first, then fall back to `default_runs_dir()`.
- [ ] TASK-01-04: Create `tests/conftest.py` with an autouse, session-scoped fixture that sets
  `PDD_RUNS_DIR` to a `tmp_path_factory.mktemp("runs")` directory for the whole session, restoring
  the previous value afterwards. Also set `PDD_SERVICE_RUNS_DIR` to the same directory unless a
  test overrides it.
- [ ] TASK-01-05: Run the full suite. For every test that fails because it expected to *read* a file
  committed under `data/runs/`, give that test an explicit directory argument, or `monkeypatch`
  `PDD_RUNS_DIR` to the committed path inside that test only. Do not remove the autouse fixture.
- [ ] TASK-01-06: In `src/pdd_agent/cli.py`, change `_run_export(args, log) -> None` to return `int`:
  `2` in the `except ExportBlockedError` branch (keep the existing `log.error` and `print`), `0`
  at the normal end. `main()` already propagates an `int` result.
- [ ] TASK-01-07: In `src/pdd_agent/cli.py`, replace the `→` characters in the `ingest` help string
  (line ~48) with `->`. At the top of `main()`, before `parser.parse_args()`, reconfigure
  `sys.stdout` and `sys.stderr` with `errors="replace"` when the stream supports `reconfigure`
  (wrap in `try/except (AttributeError, ValueError)`), so any other non-ASCII output degrades
  instead of crashing.
- [ ] TASK-01-08: Create `tests/test_cli_hygiene.py` with the tests specified below.

**File Changes**
- `src/pdd_agent/paths.py` (create): `repo_root()` and `default_runs_dir()`; no other helpers.
- `src/pdd_agent/llm/provider.py` (modify): `DraftRun.save` / `DraftRun.load` default `output_dir`
  → `default_runs_dir()`. Leave serialization untouched.
- `src/pdd_agent/review/states.py` (modify): `ReviewStateStore.save` / `.load` default
  `output_dir` → `default_runs_dir()`.
- `src/pdd_agent/export/docx_export.py` (modify): remove the import-time `_DRAFT_RUNS_DIR` default
  from the call path. If other modules or tests import `_DRAFT_RUNS_DIR`, keep the name defined for
  compatibility, but `export_run_to_docx` must call `default_runs_dir()` when `runs_dir` is `None`.
- `src/pdd_agent/export/drive_upload.py` (modify): default `runs_dir` → `default_runs_dir()`.
- `src/pdd_agent/phase05/benchmark.py` (modify): resolve the default runs dir at call time.
- `src/pdd_agent/agent/section_orchestrator.py` (modify): `self._runs_dir or default_runs_dir()`
  in both places. No other change in this phase.
- `src/pdd_agent/service/main.py` (modify): `RUNS_DIR` fallback → `default_runs_dir()` inside
  `_runs_dir()` and `_service_runs_dir()`; keep `PDD_SERVICE_RUNS_DIR` precedence.
- `src/pdd_agent/cli.py` (modify): `_run_export` returns `int` (2 on block); ASCII `->` in the
  `ingest` help; stream reconfigure in `main()`.
- `tests/conftest.py` (create): the autouse session fixture described in TASK-01-04.
- `tests/test_cli_hygiene.py` (create): tests below.

**Function Signatures**
- `repo_root() -> Path` — the checkout root (`Path(__file__).resolve().parents[2]`).
- `default_runs_dir() -> Path` — `$PDD_RUNS_DIR` when set and non-empty, else
  `repo_root() / "data" / "runs"`; evaluated on every call.
- `_run_export(args: argparse.Namespace, log: Any) -> int` — `0` on success, `2` when the export
  gate blocks.

**Test Specs**
- `default_runs_dir()` with `monkeypatch.setenv("PDD_RUNS_DIR", str(tmp_path))` → `tmp_path`.
- `default_runs_dir()` with `monkeypatch.delenv("PDD_RUNS_DIR", raising=False)` →
  `repo_root() / "data" / "runs"`.
- `default_runs_dir()` with `PDD_RUNS_DIR=""` → `repo_root() / "data" / "runs"`.
- `DraftRun(run_id="hygiene-1", project_name="x", provider="noop").save()` under the conftest
  fixture → the returned path's parent equals `os.environ["PDD_RUNS_DIR"]`, and
  `Path("data/runs/hygiene-1.json")` does not exist.
- Every `help=` string reachable from `pdd_agent.cli._build_parser()` (walk
  `parser._subparsers._group_actions[0].choices` and each subparser's `_actions`) encodes with
  `.encode("ascii")` without raising.
- `subprocess.run([sys.executable, "-m", "pdd_agent.cli", "--help"], env={**os.environ,
  "PYTHONIOENCODING": "cp1252"}, capture_output=True)` → `returncode == 0` and `b"inventory"` in
  stdout. (If `pdd_agent.cli` has no `if __name__ == "__main__":` guard, call
  `["pdd-agent", "--help"]` instead, skipping when `shutil.which("pdd-agent")` is `None`.)
- `_run_export(args, log)` with `export_run_to_docx` monkeypatched to raise
  `ExportBlockedError("blocked for test")` and `args.review_output_dir=None`,
  `args.output=None`, `args.force=False`, `args.pdf=False`, `args.run_id="r1"` → returns `2`.

**Dependencies**
- None.

**Exit Criteria**
- [ ] `python -m pytest -m "not corpus" -q` passes: `974 passed` plus the new hygiene tests,
  `2 xfailed`, `0 failed`.
- [ ] The `data/runs/*.json` count after the full suite equals the TASK-01-01 baseline.
- [ ] `PYTHONIOENCODING=cp1252 pdd-agent --help` exits 0.
- [ ] `ruff check .` and `ruff format --check .` pass.

**Phase Risks**
- **RISK-01-01:** Some tests may rely on reading real run JSONs from `data/runs/` (for example
  end-to-end tests). Mitigation: TASK-01-05 pins those tests to an explicit directory; the autouse
  fixture stays.
- **RISK-01-02:** Import-time constants cached elsewhere (e.g. `from ... import _DRAFT_RUNS_DIR`).
  Mitigation: `grep -rn "_DRAFT_RUNS_DIR\|_DEFAULT_RUNS_DIR\|RUNS_DIR" src tests` before and after;
  every default path must resolve at call time.

### PHASE-02 - Get the Methodology into the Index

**Goal**
Make the four text/plain documents, the ACM0022 methodology among them, produce section spans,
and make the index builder say so loudly when any parsed document contributes zero rows.

**Tasks**
- [ ] TASK-02-01: In `src/pdd_agent/parse/section_parser.py::parse_document`, change the strict
  (aligned) branch so the TOC-page test applies only to headings that carry an explicit `page`
  key: `if "page" in h and _is_toc_page(page_texts.get(h["page"], "")): continue`.
- [ ] TASK-02-02: In the same function, skip any heading whose text matches the dotted-leader TOC
  pattern `DOTTED_LEADER_RE = re.compile(r"\.{4,}\s*\d+\s*$")`, in both the strict branch and the
  `sections_mapped` construction. These are table-of-contents entries, not section headings.
- [ ] TASK-02-03: In `_find_content_page` (nested in `parse_document`), when the heading has no
  `page` key and the document has exactly one page, use the aligned text block body for that heading
  as `text_preview` (first 500 characters) instead of the page text.
- [ ] TASK-02-04: Update the stale comment above the misaligned-fallback branch (lines ~241–250) so
  it describes the current shape: text/plain documents now align and are handled by the strict
  branch. Do not change that branch's logic.
- [ ] TASK-02-05: In `src/pdd_agent/retrieval/index.py::RetrievalIndex.build`, after the per-document
  insert loop, emit `logger.warning("document_zero_rows", document=doc_name)` for every document in
  `rows_by_document` with value `0`. Add `"zero_row_documents": [...]` (sorted) to the dict `build`
  returns.
- [ ] TASK-02-06: Add the tests below to `tests/test_section_parser.py` and
  `tests/test_retrieval_search.py`.
- [ ] TASK-02-07: Rebuild the local index and record the result (a data check, not a unit test):
  `pdd-agent build-index` then
  `PYTHONIOENCODING=utf-8 pdd-agent index-report --json > /tmp/index-report.json`.

**File Changes**
- `src/pdd_agent/parse/section_parser.py` (modify): the `page`-key guard, `DOTTED_LEADER_RE`,
  single-page `text_preview`, and the comment refresh. Leave the misaligned-fallback logic, the
  alias matching (`_best_match`) and the chunking (`_chunk_block`) unchanged.
- `src/pdd_agent/retrieval/index.py` (modify): the zero-row warning and the `zero_row_documents`
  return key. Leave the FTS5 schema unchanged.
- `tests/test_section_parser.py` (modify): add parser tests.
- `tests/test_retrieval_search.py` (modify): add the zero-row test, following the existing
  `tmp_path` index-building pattern in that file (e.g. `test_zero_yield_document_reported`).

**Function Signatures**
- `parse_document(norm_json_path: Path, schema_path: Path | None = None) -> dict[str, Any]` —
  unchanged signature; text/plain-shaped records now yield non-empty `section_spans`.
- `RetrievalIndex.build(normalized_dir: Path | None = None, schema_path: Path | None = None) -> dict[str, Any]`
  — unchanged signature; the result gains `zero_row_documents: list[str]`.

**Test Specs**
- Write `tmp_path/Methodology.norm.json` with `mime_type="text/plain"`, one page
  `{"page": 1, "chars": 400, "text": "CONTENTS\n1. INTRODUCTION ........ 4\n2. SCOPE ........ 5\n1. INTRODUCTION\nThis methodology applies to ...\n2. SCOPE\nApplicable to MSW ..."}`,
  headings `[{"text": "1. INTRODUCTION ........ 4", "level": 1}, {"text": "2. SCOPE ........ 5", "level": 1}, {"text": "1. INTRODUCTION", "level": 1}, {"text": "2. SCOPE", "level": 1}]`
  (no `page` keys) and text blocks aligned to those headings (the two TOC blocks with empty text).
  `parse_document(path)` → `len(result["section_spans"]) >= 2`; no span's `heading_text` matches
  `DOTTED_LEADER_RE`; a span's `text` contains `"This methodology applies to"`.
- The same record but with a heading carrying `"page": 1` and page 1 containing `"CONTENTS"` →
  that heading is still skipped (the TOC test still applies when `page` is present).
- An existing PDF-shaped fixture in `tests/test_section_parser.py` → its `section_spans` count is
  unchanged (regression guard: record the count before the change and assert equality).
- `RetrievalIndex(db_path=tmp_path/"i.db").build(normalized_dir=d, schema_path=...)` where `d`
  holds one normal document and one whose record has `text=""`, `text_blocks=[]`, `headings=[]`
  → the returned dict has `zero_row_documents == ["<empty doc stem>"]`, and a `document_zero_rows`
  warning is logged (capture with `structlog.testing.capture_logs()`).

**Dependencies**
- PHASE-01 recommended (so the suite run does not pollute `data/runs/`), not required.

**Exit Criteria**
- [ ] `python -m pytest tests/test_section_parser.py tests/test_retrieval_search.py -v` passes.
- [ ] After TASK-02-07 on a machine that has `data/corpus/normalized/`: `index-report --json`
  shows `"documents": 17` and `EB111_repan07_ACM0022_v03.0.norm` present in `rows_by_document`
  with a value above 0; `missing_documents` is `[]`.
- [ ] `build-index` logs no `document_zero_rows` warning on the local corpus.
- [ ] Full suite still `0 failed`.

**Phase Risks**
- **RISK-02-01:** Newly indexed documents change what every later retrieval returns. Mitigation:
  accepted. No committed artifact depends on retrieval byte-stability (committed demo packages are
  out of scope).
- **RISK-02-02:** `DOTTED_LEADER_RE` could match a real heading that ends in a number after dots.
  Mitigation: the pattern requires at least four consecutive dots, which real headings do not use.

### PHASE-03 - Ranked, Self-Excluding Grounding with a Normative Channel

**Goal**
Replace the orchestrator's alphabetical precedent lookup with one call to a new
`grounding.ground_section()` that implements `## Specification` S-1, S-2 and S-3. Fix the
prompt-header numbering. Show honest scores in the prompt and in provenance.

**Tasks**
- [ ] TASK-03-01: Extend `configs/corpus_families.yaml` with two new top-level keys (leave
  `default_family` and `documents` untouched):
  ```yaml
  registry_ids:
    VCS_Inegol_Project-Description.norm: "3908"
    VCS_Soc_Son_Project-Description.norm: "2567"
  methodology_documents:
    - EB111_repan07_ACM0022_v03.0.norm
  ```
- [ ] TASK-03-02: In `src/pdd_agent/retrieval/index.py`, add a `document_names: Sequence[str] | None = None`
  filter parameter to `RetrievalIndex.search` (SQL `document_name IN (…)` with bound parameters)
  and add `RetrievalIndex.document_mentions(document_name, terms)`. Add
  `load_corpus_config(path)` returning families, registry ids and methodology documents (reuse the
  existing YAML-loading code near line 53; keep the existing family-map function working for its
  current callers).
- [ ] TASK-03-03: In `src/pdd_agent/retrieval/search.py`, add an optional
  `channel: str = "precedent"` constructor argument and attribute to `RetrievalResult`, and include
  it in `to_dict()`. When `channel == "normative"`, `to_dict()["provenance"]` becomes
  `"[METHODOLOGY: {document_name}, {canonical_heading}]"`.
- [ ] TASK-03-04: Create `src/pdd_agent/grounding/__init__.py` (re-exporting `ground_section`,
  `Grounding`, `ProjectProfile`, `profile_from_project`) and
  `src/pdd_agent/grounding/selection.py`, implementing S-1 (`TECHNOLOGY_KEYWORDS`, country
  aliases, scoring, two-pass selection, `matched_terms` labels), S-2 (normative query and
  retrieval) and S-3 (self-exclusion). When `index.is_built()` is False, return an empty
  `Grounding` and reuse `retrieval.search._warn_no_index_once()`.
- [ ] TASK-03-05: If the precedent list has fewer than 2 entries after selection, append up to
  `min(3, k)` results from `get_section_heading_examples(heading, k=min(3, k), index=index)` that
  are not excluded and not already selected, with `score=0.0` and `matched_terms=["heading-fallback"]`.
  This preserves today's heading-example top-up behaviour.
- [ ] TASK-03-06: In `src/pdd_agent/agent/section_orchestrator.py::draft_section`, replace both
  `get_examples_for_section(...)` branches (lines ~795–812) with one
  `ground_section(section_id, sub_section_id, heading, self._project, k=k)` call. Set
  `examples = grounding.precedent`, keep the existing `from_fallback_family` →
  `GROUNDING:` issue logic, and pass `grounding.normative` into prompt building. Replace the second
  call site near line ~1204 the same way. Remove the now-unused `get_examples_for_section` import
  only if nothing else in the module uses it.
- [ ] TASK-03-07: Add `normative: Sequence[Any] = ()` as a keyword argument to `_build_prompt`. Add
  `_format_normative_results(normative, max_chars)`, which renders
  `## Methodology Requirements (normative)` with one `### Requirement {i} [{doc}]` sub-block per
  hit, placed immediately before the precedent block. Change `_format_retrieval_results`' heading
  to `## Precedent Evidence (ranked by project similarity)` and its per-item label from
  `(BM25 score: …)` to `(similarity score: {score:.2f}; matched: {", ".join(matched_terms)})`.
- [ ] TASK-03-08: Build provenance as the precedent `[CORPUS: …]` markers followed by the normative
  `[METHODOLOGY: …]` markers. When `grounding.excluded_documents` is non-empty, append
  `f"[GROUNDING: self-excluded {', '.join(excluded)}]"`.
- [ ] TASK-03-09: Fix the prompt header (line ~616): `label = sub_section_id or section_id`, then
  `f"## Section: {heading} ({label})\n"`.
- [ ] TASK-03-10: Find every test that patches the old call site:
  `grep -rn "section_orchestrator.get_examples_for_section\|get_examples_for_section" tests`.
  Tests that patch `pdd_agent.agent.section_orchestrator.get_examples_for_section` must now patch
  `pdd_agent.agent.section_orchestrator.ground_section`, returning a `Grounding` whose `precedent`
  holds the same fake examples. Update any assertion expecting `"(4.4.1)"`,
  `"Corpus Evidence (FTS5/BM25 retrieval)"` or `"BM25 score"` in prompt text to the new strings.
- [ ] TASK-03-11: Create `tests/test_grounding_selection.py` with the tests below.

**File Changes**
- `configs/corpus_families.yaml` (modify): add `registry_ids` and `methodology_documents` only. Do
  not retype the mojibake stem.
- `src/pdd_agent/retrieval/index.py` (modify): `search(..., document_names=None)`,
  `document_mentions`, `load_corpus_config`. Leave `get_section_examples` unchanged.
- `src/pdd_agent/retrieval/search.py` (modify): `RetrievalResult.channel`. Leave
  `get_examples_for_section` unchanged (CON-003).
- `src/pdd_agent/grounding/__init__.py` (create), `src/pdd_agent/grounding/selection.py` (create).
- `src/pdd_agent/agent/section_orchestrator.py` (modify): the two retrieval call sites,
  `_build_prompt(normative=...)`, `_format_normative_results`, the renamed precedent heading and
  score label, provenance, header numbering. No other behaviour change.
- `tests/test_grounding_selection.py` (create).
- `tests/test_section_orchestrator.py`, `tests/test_prompt_assembly.py` and any other test found by
  TASK-03-10 (modify): repoint patches and update literal strings only.

**Function Signatures**
- `@dataclass(frozen=True) class ProjectProfile: family: str; technology_type: str; methodology_ids: tuple[str, ...]; country: str; vcs_id: str`
  — the project facts that drive ranking (`vcs_id` is digits only, possibly `""`).
- `profile_from_project(project_input: ProjectInput | None) -> ProjectProfile` — a profile built
  from `ProjectInput`; `None` yields `ProjectProfile("wte", "other", (), "", "")`.
- `@dataclass class Grounding: precedent: list[RetrievalResult]; normative: list[RetrievalResult]; excluded_documents: list[str]; from_fallback_family: bool`
  — everything retrieved for one section.
- `ground_section(section_id: str, sub_section_id: str | None, heading: str, project_input: ProjectInput | None, k: int = 5, index: RetrievalIndex | None = None, exclude_documents: Sequence[str] | None = None, config_path: Path | None = None) -> Grounding`
  — ranked precedent (S-1), normative hits (S-2) and the exclusion set applied (S-3).
- `select_precedent(section_id: str, sub_section_id: str | None, profile: ProjectProfile, k: int, index: RetrievalIndex, excluded: frozenset[str], methodology_documents: frozenset[str], families: dict[str, str]) -> list[RetrievalResult]`
  — S-1 selection with scores and `matched_terms`.
- `select_normative(heading: str, profile: ProjectProfile, index: RetrievalIndex, methodology_documents: Sequence[str], k: int = 3) -> list[RetrievalResult]`
  — S-2 hits with `channel="normative"`.
- `exclusion_set(project_vcs_id: str | None, registry_ids: dict[str, str]) -> frozenset[str]` — S-3.
- `score_chunk(text: str, document_name: str, profile: ProjectProfile, families: dict[str, str], country_hit: bool, bm25_norm: float) -> tuple[float, list[str]]`
  — the S-1 score and its fired feature labels.
- `RetrievalIndex.search(query: str, section_id: str | None = None, content_class: str | None = None, document_family: str | None = None, k: int = 5, document_names: Sequence[str] | None = None) -> list[dict[str, Any]]`
  — unchanged behaviour when `document_names` is `None`.
- `RetrievalIndex.document_mentions(document_name: str, terms: Sequence[str]) -> bool` — True if
  any term matches any row of that document (FTS `MATCH`, terms quoted).
- `load_corpus_config(path: Path | None = None) -> tuple[dict[str, str], dict[str, str], list[str]]`
  — `(families_by_stem, registry_ids_by_stem, methodology_documents)`, each empty when its key is
  absent.
- `SectionOrchestrator._build_prompt(self, section_id: str, sub_section_id: str | None, examples: Sequence[Any], project_input: ProjectInput | None = None, normative: Sequence[Any] = ()) -> str`
  — prompt text including the normative block when `normative` is non-empty.

**Test Specs**
Build one FTS5 index in `tmp_path` from synthetic `.norm.json` files, following the helper pattern
already used in `tests/test_retrieval_search.py`. Include four documents with a section-`3.4`
span each, plus a family config written to `tmp_path/families.yaml`:
- `A_Alpha_Project-Description.norm` — text "Mass burn incineration plant in China …", family `wte`.
- `B_Beta_Project-Description.norm` — text "Anaerobic digestion and biogas engines in Turkey under ACM0022 …", family `wte`.
- `Z_Zulu_Project-Description.norm` — text "Anaerobic digestion, biomethanization and RDF in Turkey, ACM0022 …", family `wte`, `registry_ids: {"Z_Zulu_Project-Description.norm": "3908"}`.
- `M_Method.norm` — methodology text "Baseline emissions from solid waste disposal sites … ACM0022 applicability conditions …" with `section_id=""`, listed in `methodology_documents`.

Profile: `technology_type="combined_wte_ad"`, `country="Türkiye"`, `methodology_ids=("ACM0022",)`,
`vcs_id="3908"`.

- `exclusion_set("VCS-3908", {"Z_Zulu_Project-Description.norm": "3908"})` →
  `frozenset({"Z_Zulu_Project-Description.norm"})`.
- `exclusion_set(None, {...})` → `frozenset()`; `exclusion_set("", {...})` → `frozenset()`.
- `ground_section("3", "3.4", "Baseline Scenario", project_input, k=5, index=idx, config_path=cfg).precedent`
  → document order `["B_Beta_Project-Description.norm", "A_Alpha_Project-Description.norm"]`.
  `Z_Zulu` is absent (self-excluded), `M_Method` is absent (methodology), every `score > 0`, and
  `B_Beta`'s `matched_terms` contains `"family:wte"`, `"tech:anaerobic digestion"`,
  `"country:Türkiye"` and `"methodology:ACM0022"`.
- The same call's `.excluded_documents` → `["Z_Zulu_Project-Description.norm"]`.
- The same call with `exclude_documents=()` → `Z_Zulu` is present and ranked first (it matches
  more features than `B_Beta`).
- The same call's `.normative` → exactly one result, `document_name == "M_Method.norm"`,
  `channel == "normative"`, `to_dict()["provenance"].startswith("[METHODOLOGY: M_Method.norm")`.
- `score_chunk("text with \ufffd" * 50, "A_Alpha_Project-Description.norm", profile, families, False, 0.0)`
  → `"damaged-text"` in the labels and the score includes the −2.0 penalty.
- Two runs of the same `ground_section` call → identical lists (determinism).
- `ground_section(...)` with an unbuilt index (`RetrievalIndex(db_path=tmp_path/"none.db")`) →
  `Grounding([], [], [], False)`.
- Prompt header: `SectionOrchestrator(project_input=pi)._build_prompt("4", "4.1", [])` contains
  `"(4.1)"` and does not contain `"4.4.1"`.
- Prompt blocks: `_build_prompt("4", "4.1", [precedent_result], pi, normative=[normative_result])`
  contains `"## Methodology Requirements (normative)"` before
  `"## Precedent Evidence (ranked by project similarity)"`.

**Dependencies**
- PHASE-02 (the methodology must be indexed for the normative channel to return anything on the
  real corpus; unit tests use synthetic indexes and do not depend on it).

**Exit Criteria**
- [ ] `python -m pytest tests/test_grounding_selection.py tests/test_section_orchestrator.py tests/test_prompt_assembly.py tests/test_retrieval_search.py -v` passes.
- [ ] Full suite `0 failed`.
- [ ] Data check on a machine with the real index (after PHASE-02):
  `PYTHONIOENCODING=utf-8 python -c "import yaml; from schemas.project_input import ProjectInput; from pdd_agent.grounding import ground_section; pi=ProjectInput.model_validate(yaml.safe_load(open('configs/demo/inegol_project_input.yaml',encoding='utf-8'))); g=ground_section('4','4.1','Baseline Emissions',pi,k=5); print([r.document_name for r in g.precedent]); print([r.document_name for r in g.normative]); print(g.excluded_documents); print([round(r.score,2) for r in g.precedent])"`
  → the precedent list does not contain `VCS_Inegol_Project-Description.norm`; the normative list
  contains `EB111_repan07_ACM0022_v03.0.norm`; the excluded list is
  `['VCS_Inegol_Project-Description.norm']`; every printed score is above 0.
- [ ] `ruff check .` and `ruff format --check .` pass.

**Phase Risks**
- **RISK-03-01:** Many orchestrator tests patch the old import path. Mitigation: TASK-03-10
  enumerates them by grep. The patch target moves; fake data stays the same.
- **RISK-03-02:** `document_mentions` runs one FTS query per candidate document per section (at most
  17 per section, 36 sections). Mitigation: memoize per `(document_name, country)` inside
  `ground_section` for the lifetime of one `SectionOrchestrator` (a module-level
  `functools.lru_cache` keyed on the db path, document name and terms tuple is acceptable).

### PHASE-04 - Honest Climate Zones, Per-Year Schedules, Strict YAML

**Goal**
Stop the resolver from silently guessing wet vs dry. Let the engine model a growing waste deposit
and a changing electricity output year by year (S-4). Make project-input YAML with duplicate keys
fail to load.

**Tasks**
- [ ] TASK-04-01: In `src/pdd_agent/calc/constants.py`, add
  `climate_zone_resolution(latitude, declared) -> tuple[str, bool]` returning `(zone, derived)`.
  Keep `climate_zone_for(latitude, declared)` as a thin wrapper returning only the zone (existing
  callers unchanged).
- [ ] TASK-04-02: In `src/pdd_agent/calc/dispatch.py` (around line 246), when `derived` is True,
  append the warning
  `f"calc_climate_zone_ambiguous: latitude={lat} derived={zone}; IPCC wet vs dry depends on precipitation/PET and cannot be derived from latitude - declare location.climate_zone"`
  in addition to the existing `calc_climate_zone_resolved` warning. The derived value itself is
  unchanged (DEC-003).
- [ ] TASK-04-03: In `schemas/project_input.py::ProjectTechnology`, add two optional fields:
  `annual_waste_by_year: list[float] | None = None` (tonnes/year received by the project in each
  crediting-period year, index 0 = year 1, each value > 0) and
  `energy_generation_mwh_by_year: list[float] | None = None` (MWh/year net electricity displaced
  in each crediting-period year, each value ≥ 0). Add a `model_validator(mode="after")` that raises
  `ValueError("capacity_ramp and annual_waste_by_year are mutually exclusive")` when both
  `capacity_ramp` and `annual_waste_by_year` are set.
- [ ] TASK-04-04: In `src/pdd_agent/calc/models.py::WasteStream`, add
  `annual_tonnes_by_year: list[float] | None = None`.
- [ ] TASK-04-05: In `src/pdd_agent/calc/cdm_tool_04.py::methane_from_swds`, add the keyword
  parameter `annual_waste_by_year: Sequence[float] | None = None`. Inside the FOD sum,
  `w_j_x = annual_waste_by_year[min(x, len(annual_waste_by_year)) - 1]` when provided, else
  `annual_waste_tonnes`. Results with `None` must be identical to today's.
- [ ] TASK-04-06: In `src/pdd_agent/calc/acm0022.py::ACM0022Calculator.calculate`, pass
  `annual_waste_by_year=[t * self._inp.swds_diversion_fraction for t in ws.annual_tonnes_by_year]`
  when `ws.annual_tonnes_by_year` is set. For `total_waste` (the AD/biogas pathway), when every
  stream has `annual_tonnes_by_year`, use each stream's value for `calculation_year` (last value
  carried forward) instead of `annual_tonnes`.
- [ ] TASK-04-07: In `src/pdd_agent/calc/dispatch.py::_map_acm0022`, when
  `tech.annual_waste_by_year` is set, give every waste stream (composition or even-split path)
  `annual_tonnes_by_year = [t * fraction for t in schedule]`, where `fraction` is the stream's share
  of throughput. Truncate the schedule to `crediting_period_years` with a warning when longer
  (ASM-008). In `compute_for`'s year loop, when `tech.energy_generation_mwh_by_year` is set, set
  `year_inputs["electricity_exported_mwh_per_year"]` to that year's value (last carried forward).
  The year-1 scalar fields of `PddCalcResult` stay computed from the unscheduled `engine_inputs`.
- [ ] TASK-04-08: Create `src/pdd_agent/config_io.py` with a duplicate-key-rejecting YAML loader
  and `load_project_input()`.
- [ ] TASK-04-09: Replace every `ProjectInput.model_validate(yaml.safe_load(...))` and every
  YAML-to-ProjectInput load with `load_project_input(path)` in: `src/pdd_agent/cli.py` (the loads
  near lines 588, 736, 826, 847, 894; line 1161 only if it loads a ProjectInput),
  `src/pdd_agent/phase05/benchmark.py:535`, `src/pdd_agent/phase05/provider_scorecard.py:285`,
  `src/pdd_agent/phase06/vietnam_workflow.py:77`, `src/pdd_agent/service/main.py:206` (only if it
  loads a ProjectInput) and `tests/test_registered_pdd_oracle.py::_load_pi`. Leave loads of
  schemas, rules and other configs on `yaml.safe_load`.
- [ ] TASK-04-10: Before loading Inegol through the strict loader, resolve the duplicate key in
  `configs/demo/inegol_project_input.yaml`: delete both `biomethanization_suitable_fraction` lines
  and their comment, and add one line
  `biomethanization_suitable_fraction: 0.4312  # registered ER workbook, sheet "Waste Projection": Biomethanization / Total Waste (A), constant 0.4312 in every year 2021-2027`
  (ASM-003).
- [ ] TASK-04-11: Add the tests below (`tests/test_config_io.py`, plus additions to
  `tests/test_cdm_tools.py`, `tests/test_calc_dispatch.py` and `tests/test_input_schema.py`).
- [ ] TASK-04-12: Re-measure and record (do not assert yet):
  `PYTHONIOENCODING=utf-8 pdd-agent calc --input configs/demo/inegol_project_input.yaml`.
  Record the crediting-period total in the phase's commit message.

**File Changes**
- `src/pdd_agent/calc/constants.py` (modify): `climate_zone_resolution`; the `climate_zone_for`
  wrapper. Decay tables unchanged.
- `src/pdd_agent/calc/dispatch.py` (modify): the ambiguous-zone warning, per-year stream mapping,
  per-year electricity in the schedule loop.
- `src/pdd_agent/calc/cdm_tool_04.py` (modify): the `annual_waste_by_year` parameter.
- `src/pdd_agent/calc/acm0022.py` (modify): thread the per-year series; per-year `total_waste`.
- `src/pdd_agent/calc/models.py` (modify): `WasteStream.annual_tonnes_by_year`.
- `schemas/project_input.py` (modify): two optional `ProjectTechnology` fields plus the validator.
- `src/pdd_agent/config_io.py` (create).
- `src/pdd_agent/cli.py`, `src/pdd_agent/phase05/benchmark.py`,
  `src/pdd_agent/phase05/provider_scorecard.py`, `src/pdd_agent/phase06/vietnam_workflow.py`,
  `src/pdd_agent/service/main.py`, `tests/test_registered_pdd_oracle.py` (modify): switch
  ProjectInput loads to `load_project_input`.
- `configs/demo/inegol_project_input.yaml` (modify): the single sourced
  `biomethanization_suitable_fraction`. The climate zone and schedules come in PHASE-05.
- `tests/test_config_io.py` (create); `tests/test_cdm_tools.py`, `tests/test_calc_dispatch.py`,
  `tests/test_input_schema.py` (modify).

**Function Signatures**
- `climate_zone_resolution(latitude: float, declared: str | None = None) -> tuple[str, bool]` —
  `(zone, derived)`; `derived` is False when `declared` was used.
- `climate_zone_for(latitude: float, declared: str | None = None) -> str` — unchanged behaviour.
- `methane_from_swds(waste_type: str, annual_waste_tonnes: float, year: int, crediting_start_year: int = 1, doc_override: float | None = None, decay_rate_override: float | None = None, model_correction_factor: float = MODEL_CORRECTION_FACTOR_DEFAULT, baseline_capture_fraction: float = 0.0, mcf: float = MCF_DEFAULT, oxidation_factor: float = OX_DEFAULT, doc_f: float = DOC_F_DEFAULT, f_ch4: float = F_CH4_DEFAULT, climate_zone: str | None = None, annual_waste_by_year: Sequence[float] | None = None) -> float`
  — BE_CH4 in tCO2e for year `year` per S-4.
- `class UniqueKeyLoader(yaml.SafeLoader)` — a SafeLoader whose mapping constructor raises
  `yaml.constructor.ConstructorError` naming the duplicate key and its line.
- `load_yaml_unique(path: Path | str) -> Any` — the parsed YAML, rejecting duplicate keys.
- `load_project_input(path: Path | str) -> ProjectInput` — a validated `ProjectInput` from a
  duplicate-free YAML file (UTF-8).

**Test Specs**
- `climate_zone_resolution(40.15, None)` → `("boreal_temperate_wet", True)`;
  `climate_zone_resolution(40.15, "boreal_temperate_dry")` → `("boreal_temperate_dry", False)`;
  `climate_zone_resolution(21.2, None)` → `("tropical_wet", True)`.
- `compute_for(<vietnam_socson_from_sheet.yaml>)` → `warnings` contains an entry starting
  `calc_climate_zone_ambiguous`, and `crediting_period_total_tco2e` is unchanged from before this
  phase (record the pre-change value in the test as a constant, measured at the start of the phase).
- `methane_from_swds("food_waste", 1000.0, 3)` equals
  `methane_from_swds("food_waste", 1000.0, 3, annual_waste_by_year=[1000.0, 1000.0, 1000.0])`
  (within `1e-9`).
- `methane_from_swds("food_waste", 0.0, 2, annual_waste_by_year=[1000.0, 0.0], climate_zone="boreal_temperate_dry")`
  equals the hand value `0.9 * GWP_CH4 * (1-OX) * (16/12) * F * DOC_f * MCF * 1000 * DOC_food * exp(-0.06*1) * (1-exp(-0.06))`
  computed in the test from the module constants (`f_y = 0`).
- `methane_from_swds(..., year=5, annual_waste_by_year=[100.0, 200.0])` treats years 3–5 as `200.0`
  (carry-forward): equal to passing `[100.0, 200.0, 200.0, 200.0, 200.0]`.
- `ProjectTechnology(..., capacity_ramp=[0.5, 1.0], annual_waste_by_year=[1.0, 2.0])` → raises
  `ValidationError` whose message contains `"mutually exclusive"`.
- `compute_for` on a copy of the Inegol input with `annual_waste_by_year=[100000.0, 200000.0, 300000.0, 300000.0, 300000.0, 300000.0, 300000.0]`
  → `annual_schedule[1].baseline_tco2e > annual_schedule[0].baseline_tco2e`, and the year-1
  scalar `baseline_emissions_tco2e` is unchanged from the same input without the schedule.
- `compute_for` with `energy_generation_mwh_by_year=[1000.0, 2000.0]` → the BE_EC share of
  `annual_schedule[1]` exceeds that of `annual_schedule[0]` by `1000 × grid EF` (±1e-6), checked by
  subtracting two runs that differ only in the electricity series.
- `load_yaml_unique` on `tmp_path/"d.yaml"` containing `a: 1\na: 2\n` → raises `ConstructorError`
  whose message contains `"a"` and a line number.
- `load_yaml_unique` on a nested duplicate `t:\n  x: 1\n  x: 2\n` → raises.
- `load_project_input(p)` for every file matching `configs/**/*project*.yaml` and `configs/projects/*.yaml`
  that is a ProjectInput (i.e. not `*.assumptions.yaml`) → loads without error. This catches any
  other latent duplicate.

**Dependencies**
- PHASE-01 (the suite must not write to `data/runs/` while calc tests churn).

**Exit Criteria**
- [ ] `python -m pytest tests/test_config_io.py tests/test_cdm_tools.py tests/test_calc_dispatch.py tests/test_input_schema.py tests/test_registered_pdd_oracle.py -v` passes.
  The two Inegol xfails are still xfailed (the Inegol config gains its zone and schedules only in
  PHASE-05).
- [ ] Soc Son's crediting-period total is unchanged to the tCO2e (regression guard test passes).
- [ ] Full suite `0 failed`; `ruff check .` and `ruff format --check .` pass.

**Phase Risks**
- **RISK-04-01:** Tests may assert the exact `warnings` list of `compute_for`. Mitigation: search
  `grep -rn "calc_climate_zone_resolved\|warnings ==" tests` and change exact-list assertions to
  membership assertions.
- **RISK-04-02:** The strict loader may reject an existing config nobody knew was broken.
  Mitigation: that is the intended outcome. Fix the config by keeping the value that has a source
  comment, and record the change in the commit message.

### PHASE-05 - Read the Registered Workbook and Re-Source Inegol

**Goal**
Read the registered Inegol ER workbook into typed values with sheet/cell lineage. Re-source the
Inegol config from it (climate zone, composition, per-year waste, per-year electricity). Add a
year-by-year Inegol oracle. Remove the strict xfails only where the tests now genuinely pass.

**Tasks**
- [ ] TASK-05-01: Create `src/pdd_agent/reconcile/__init__.py` and
  `src/pdd_agent/reconcile/workbook.py`. Implement `read_acm0022_workbook()`. It opens with
  `openpyxl.load_workbook(path, read_only=True, data_only=True)` and locates sheets by exact name:
  `"SUMMARY (ER)"`, `"Waste Parameters"`, `"Waste Projection"`, `"Project Emissions"`,
  `"Baseline Emissions (Total)"`. Columns are located by header cell text, never by fixed letters:
  - schedule: in `"SUMMARY (ER)"`, the header row containing `"Days"` and `"Year"`; columns
    containing `"Baseline Emissions"`, `"Project Emissions"`, `"Leak"` and `"Emission Reductions"`.
    Stop at the row whose first cell is `"TOTAL"`. Skip rows with `Days < 300` (ASM-007).
  - decay rates and DOC: `"Waste Parameters"`, the rows under the header containing `"DOCj"` and
    `"kj"`. Map row labels to engine keys by prefix: `"Wood"` → `wood`, `"Pulp, paper"` →
    `paper_cardboard`, `"Food"` → `food_waste`, `"Textiles"` → `textiles`, `"Garden"` →
    `garden_waste`. Divide DOC by 100.
  - composition: `"Waste Projection"`, the table whose header row contains `"Waste Type"` and a
    column starting with `"At the Integrated Solid"`. Use the same label mapping, plus
    `"Glass, plastic, metal"` → `inert`.
  - waste by year: `"Waste Projection"`, column starting with `"Total Waste"`, rows whose year
    label starts with `"01/01/2021"` through `"01/01/2027"`.
  - biomethanization fraction: the `"Biomethanization"` column divided by the `"Total Waste"`
    column for the first crediting year (ASM-003).
  - electricity by year: per ASM-002, including its cross-check.
- [ ] TASK-05-02: Implement `infer_climate_zone()` per S-5 and `to_project_input_patch()`, which
  returns a nested dict:
  `{"location": {"climate_zone": zone}, "technology": {"waste_composition": [...], "annual_waste_by_year": [...], "energy_generation_mwh_by_year": [...], "biomethanization_suitable_fraction": value}}`.
  Every `waste_composition` entry's `source` string is
  `f"registered ER workbook, sheet \"Waste Projection\", cell {cell}"`.
- [ ] TASK-05-03: Resolve the workbook path with `inegol_workbook_path()` (ASM-001).
- [ ] TASK-05-04: On a machine with the workbook, print the patch:
  `PYTHONIOENCODING=utf-8 python -c "from pdd_agent.reconcile.workbook import read_acm0022_workbook, to_project_input_patch, inegol_workbook_path; import json; print(json.dumps(to_project_input_patch(read_acm0022_workbook(inegol_workbook_path())), indent=2))"`.
  Apply its values to `configs/demo/inegol_project_input.yaml` by hand:
  - `location.climate_zone: boreal_temperate_dry`, with a comment citing the *Waste Parameters*
    sheet.
  - `technology.waste_composition` (six entries per ASM-004, `source` strings as produced).
  - `technology.annual_waste_by_year: [299300, 365000, 419750, 456250, 492750, 547500, 456250]`
    with a comment citing the *Waste Projection* column.
  - `technology.energy_generation_mwh_by_year: [8395.389, 43872.46, 59455.872, 59455.872, 59455.872, 59455.872, 59455.872]`
    with a comment citing the *Project Emissions* `ECBL` column.

  Leave `annual_waste_throughput` and `energy_generation_mwh_year` unchanged (ASM-009). If the
  printed values differ from the literals above, the printed values win; record the difference in
  the commit message.
- [ ] TASK-05-05: In `tests/test_registered_pdd_oracle.py`, add constants
  `INEGOL_REGISTERED_BE_BY_YEAR = [10167, 43251, 72738, 102035, 140719, 189144, 247313]`,
  `INEGOL_REGISTERED_PE_BY_YEAR = [5809, 8088, 9849, 11316, 12294, 13272, 14739]` and
  `INEGOL_REGISTERED_ER_BY_YEAR = [4358, 35163, 62889, 90719, 128425, 175872, 232574]`, each with
  a comment naming the workbook file and the `"SUMMARY (ER)"` sheet.
  Add `class TestInegolAnnualSchedule` with the tests below.
- [ ] TASK-05-06: Change `TestInegolOracle::test_annual_net_within_tolerance` per DEC-004 to
  compare `mean(e.net_tco2e for e in result.annual_schedule)` against `INEGOL_ANNUAL_ERS`.
- [ ] TASK-05-07: Run `python -m pytest tests/test_registered_pdd_oracle.py -v -rxX`. For each
  `XPASS(strict)` Inegol test, remove its `@_YEAR_ONE_XFAIL` decorator. For each test still
  failing, keep or add a `strict=True` xfail whose `reason` records the 2026-09-11-onward measured
  value (the exact engine number, the registered number and the relative error). Never change
  `TOLERANCE`.
- [ ] TASK-05-08: Create `tests/test_reconcile_workbook.py` with the synthetic-workbook tests below
  and one `@pytest.mark.corpus` test against the real workbook.

**File Changes**
- `src/pdd_agent/reconcile/__init__.py` (create): re-export the reader API.
- `src/pdd_agent/reconcile/workbook.py` (create): dataclasses, reader, `infer_climate_zone`,
  `to_project_input_patch`, `inegol_workbook_path`.
- `configs/demo/inegol_project_input.yaml` (modify): the four sourced additions from TASK-05-04.
  Leave all other keys unchanged.
- `tests/test_registered_pdd_oracle.py` (modify): new constants, `TestInegolAnnualSchedule`, the
  DEC-004 change, xfail decorators per TASK-05-07. `TOLERANCE` unchanged.
- `tests/test_reconcile_workbook.py` (create).

**Function Signatures**
- `@dataclass(frozen=True) class LineageValue: value: float; sheet: str; cell: str` — one number
  and where it came from (cell in A1 notation, e.g. `"D7"`).
- `@dataclass class RegisteredSchedule: year_labels: list[str]; baseline: list[LineageValue]; project: list[LineageValue]; leakage: list[LineageValue]; net: list[LineageValue]`
  — crediting years only, stub rows removed.
- `@dataclass class RegisteredAcm0022Workbook: path: Path; schedule: RegisteredSchedule; decay_rates: dict[str, LineageValue]; doc_fractions: dict[str, LineageValue]; composition: dict[str, LineageValue]; waste_by_year: list[LineageValue]; electricity_mwh_by_year: list[LineageValue]; biomethanization_fraction: LineageValue | None`
  — everything the engine and the reconcile report need.
- `read_acm0022_workbook(path: Path | str) -> RegisteredAcm0022Workbook` — the parsed workbook;
  raises `ValueError` naming the sheet and the header text sought when a required table is not
  found.
- `infer_climate_zone(decay_rates: dict[str, float]) -> str | None` — S-5.
- `to_project_input_patch(workbook: RegisteredAcm0022Workbook) -> dict[str, Any]` — the nested
  patch described in TASK-05-02.
- `inegol_workbook_path() -> Path` — `$PDD_INEGOL_ER_WORKBOOK` or the ASM-001 default path.

**Test Specs**
Synthetic workbook, built in `tmp_path` with openpyxl by a test helper
`_make_workbook(path, *, years=2)`. It has the five sheets, the same header texts as above, a
stub row (Days = 1), two crediting rows (Days = 365) with BE `[1000, 2000]`, PE `[100, 200]`,
leakage `[0, 0]`, ER `[900, 1800]`, then `TOTAL`. *Waste Parameters*: DOC/k rows with the
`boreal_temperate_dry` values. *Waste Projection*: total waste `[10000, 20000]`, biomethanization
`[4312, 8624]`, composition wood 0.1 / food 0.6 / glass 0.3. *Project Emissions*: an `ECBL`
column `[100.0, 200.0]`. *Baseline Emissions (Total)*: separated
`[100*0.541*1.09101, 200*0.541*1.09101]`.

- `read_acm0022_workbook(p).schedule.net` values → `[900.0, 1800.0]`; the stub row is absent;
  `schedule.net[0].sheet == "SUMMARY (ER)"`, and `schedule.net[0].cell` is the A1 address of
  that cell.
- `.decay_rates["food_waste"].value` → `0.06`; `.doc_fractions["wood"].value` → `0.43`.
- `infer_climate_zone({"wood": 0.02, "paper_cardboard": 0.04, "food_waste": 0.06, "textiles": 0.04, "garden_waste": 0.05})`
  → `"boreal_temperate_dry"`.
- `infer_climate_zone({"food_waste": 0.185})` → `"boreal_temperate_wet"`;
  `infer_climate_zone({"food_waste": 0.123})` → `None`.
- `.biomethanization_fraction.value` → `0.4312`.
- The synthetic workbook with the separated column set to `[999, 999]` → `read_acm0022_workbook`
  raises `ValueError` mentioning `"ECBL"` (ASM-002 cross-check).
- The synthetic workbook without a `"Waste Parameters"` sheet → raises `ValueError` mentioning
  `"Waste Parameters"`.
- `to_project_input_patch(wb)["technology"]["waste_composition"]` → a list of dicts with keys
  `waste_type`, `mass_fraction` and `source`, including `{"waste_type": "inert", "mass_fraction": 0.3, ...}`.
- `@pytest.mark.corpus` real-workbook test (skipped when `inegol_workbook_path()` does not exist)
  → `sum(v.value for v in wb.schedule.net) == 730000`, `len(wb.schedule.net) == 7`, and
  `infer_climate_zone({k: v.value for k, v in wb.decay_rates.items()}) == "boreal_temperate_dry"`.
- `TestInegolAnnualSchedule::test_registered_constants_sum_to_published_totals` →
  `sum(INEGOL_REGISTERED_BE_BY_YEAR) == 805367`, `sum(INEGOL_REGISTERED_PE_BY_YEAR) == 75367`,
  `sum(INEGOL_REGISTERED_ER_BY_YEAR) == 730000`.
- `TestInegolAnnualSchedule::test_registered_identity` → for every year,
  `BE − PE == ER` within ±1 (rounding in the published sheet).
- `TestInegolAnnualSchedule::test_engine_schedule_is_back_loaded` →
  `compute_for(inegol).annual_schedule` has strictly increasing `baseline_tco2e` from year 1 to
  year 6 (the registered shape: waste grows through 2026).
- `TestInegolAnnualSchedule::test_engine_years_3_to_7_within_tolerance` → for years 3–7, the
  engine's `net_tco2e` is within `TOLERANCE` of `INEGOL_REGISTERED_ER_BY_YEAR`. If it fails, mark
  it `xfail(strict=True)` with the measured per-year values in `reason` (TASK-05-07).
- `TestInegolOracle::test_crediting_period_total_within_tolerance` → passes, or stays xfail with a
  re-measured reason (TASK-05-07).

**Dependencies**
- PHASE-04 (per-year schedules, strict loader, declared zone honoured).

**Exit Criteria**
- [ ] `python -m pytest tests/test_reconcile_workbook.py tests/test_registered_pdd_oracle.py -v -rxX` passes, with no `XPASS`.
- [ ] `PYTHONIOENCODING=utf-8 pdd-agent calc --input configs/demo/inegol_project_input.yaml`
  prints a crediting-period total. Its relative error against 730,000 is recorded in the
  `TestInegolOracle` test docstring or xfail reason with the date.
- [ ] `grep -c "biomethanization_suitable_fraction" configs/demo/inegol_project_input.yaml` prints `1`.
- [ ] Full suite `0 failed`; `ruff check .` and `ruff format --check .` pass.

**Phase Risks**
- **RISK-05-01:** The engine's AD pathway may not reproduce the registered `PE_CH4` growth (5,809
  to 14,739), so project emissions may be off even with per-year waste. Mitigation: record the
  measured per-year residual in the xfail reason. Do not introduce any unsourced parameter to close
  it.
- **RISK-05-02:** Header texts in the real workbook are truncated or contain line breaks.
  Mitigation: match headers with `str(cell).strip().startswith(prefix)` after collapsing
  whitespace; the corpus-marked test guards the real file.

### PHASE-06 - `pdd-agent reconcile` and Documentation Resync

**Goal**
Ship a model-free command that recomputes a project with the engine and writes a per-year,
per-component diff against its registered workbook (S-6). Then bring the README back in line with
the code.

**Tasks**
- [ ] TASK-06-01: Create `src/pdd_agent/reconcile/diff.py` with `YearDiff`, `ReconcileReport`,
  `reconcile()` and `render_markdown()`. `parameter_mismatches` must list, in plain text:
  - the engine zone vs `infer_climate_zone(...)` (mismatch if they differ, or if inference returns
    `None`);
  - each composition fraction in the config vs the workbook (mismatch if the absolute difference
    exceeds 0.001);
  - `biomethanization_suitable_fraction` vs the workbook (mismatch if the absolute difference
    exceeds 0.001);
  - the TDL note (ASM-009) whenever the workbook's separated baseline ÷ (MWh × EF) exceeds 1.001.
- [ ] TASK-06-02: Add the `reconcile` subcommand to `src/pdd_agent/cli.py::_build_parser` with
  arguments `--input` (required, ProjectInput YAML), `--workbook` (optional; default
  `inegol_workbook_path()`), `--tolerance` (float, default `0.20`), `--output` (optional path for
  the Markdown report; default `reports/reconcile/<project-slug>-<YYYY-MM-DD>.md`, date in UTC) and
  `--json` (print the report as JSON to stdout instead of writing Markdown). Register
  `"reconcile": lambda: _run_reconcile(args, log)` in `main()`. Every help string must be ASCII.
- [ ] TASK-06-03: `_run_reconcile` loads the input with `load_project_input`, reads the workbook,
  calls `reconcile`, writes or prints the report, and returns `0` or `3` per S-6.
- [ ] TASK-06-04: Update `README.md`:
  - the **Status** paragraph (live-run wording: `claude-code` is keyless and has run; no paid
    provider has run);
  - **Known Gaps**: remove the "`ingest/registry_download.py` … is a stub" bullet and replace it
    with "best-effort registry search with a manual-download fallback";
  - **Key Files**: `cli.py` is no longer "(6 commands)"; add `grounding/` and `reconcile/`;
  - a new **Grounding** subsection under Architecture that summarizes S-1/S-2/S-3 in 5–8 lines;
  - a new **Reconcile** subsection with the exact command
    `pdd-agent reconcile --input configs/demo/inegol_project_input.yaml`;
  - add `reconcile` to the CLI table.
- [ ] TASK-06-05: Create `tests/test_reconcile_diff.py` with the tests below.
- [ ] TASK-06-06: On a machine with the workbook, run
  `PYTHONIOENCODING=utf-8 pdd-agent reconcile --input configs/demo/inegol_project_input.yaml; echo "exit=$?"`
  and keep the generated `reports/reconcile/*.md` as the phase's evidence.

**File Changes**
- `src/pdd_agent/reconcile/diff.py` (create).
- `src/pdd_agent/reconcile/__init__.py` (modify): re-export `reconcile`, `render_markdown`,
  `ReconcileReport`.
- `src/pdd_agent/cli.py` (modify): the `reconcile` subparser, `_run_reconcile` and the dispatch
  entry. No other subcommand changes.
- `README.md` (modify): the sections listed in TASK-06-04 only.
- `tests/test_reconcile_diff.py` (create).
- `reports/reconcile/` (create, via the TASK-06-06 run): one Markdown report.

**Function Signatures**
- `@dataclass class YearDiff: year_index: int; year_label: str; component: str; registered: float; engine: float; abs_diff: float; rel_diff: float | None; within_tolerance: bool; lineage: str`
  — one row of the per-year table (`component` ∈ `baseline|project|leakage|net`; `lineage` =
  `"<sheet>!<cell>"`).
- `@dataclass class ReconcileReport: project_name: str; workbook_path: str; tolerance: float; rows: list[YearDiff]; total_registered: float; total_engine: float; total_rel_diff: float; verdict_pass: bool; parameter_mismatches: list[str]; engine_warnings: list[str]`
  — the complete comparison.
- `reconcile(project_input: ProjectInput, workbook: RegisteredAcm0022Workbook, tolerance: float = 0.20) -> ReconcileReport`
  — the S-6 comparison; raises `ValueError` if `compute_for` returns `None` or the methodology is
  not ACM0022.
- `render_markdown(report: ReconcileReport) -> str` — a Markdown report: a header with the
  verdict, a totals line, a per-year table (years × components), then parameter mismatches and
  engine warnings.
- `report_to_dict(report: ReconcileReport) -> dict[str, Any]` — a JSON-serializable form used by
  `--json`.
- `_run_reconcile(args: argparse.Namespace, log: Any) -> int` — `0` if the verdict passes, `3` if
  it fails.

**Test Specs**
- `reconcile(pi, wb, tolerance=0.20)` with `compute_for` monkeypatched (in
  `pdd_agent.reconcile.diff`) to return a `PddCalcResult` whose `annual_schedule` nets are
  `[950.0, 1750.0]`, against the synthetic workbook (nets `[900, 1800]`) →
  `total_registered == 2700.0`, `total_engine == 2700.0`, `total_rel_diff == 0.0`,
  `verdict_pass is True`, and the `net` row for year 1 has `abs_diff == 50.0` and
  `rel_diff == pytest.approx(50/900)`.
- The same with engine nets `[500.0, 900.0]` → `total_rel_diff == pytest.approx((1400-2700)/2700)`
  and `verdict_pass is False`.
- Registered leakage `0` → the leakage rows have `rel_diff is None` and `within_tolerance is True`.
- A ProjectInput whose `location.climate_zone` is `None`, against the dry-zone synthetic workbook →
  `parameter_mismatches` contains an entry mentioning both `"boreal_temperate_wet"` and
  `"boreal_temperate_dry"`.
- `render_markdown(report)` → contains `"| Year |"`, the string `"PASS"` or `"FAIL"` matching
  `verdict_pass`, and each mismatch line.
- `main()` with `sys.argv = ["pdd-agent", "reconcile", "--input", <tmp inegol copy>, "--workbook", <synthetic>, "--json"]`
  and engine nets forced outside tolerance → returns `3`, and stdout parses as JSON with key
  `"verdict_pass": false`.
- The `reconcile` subparser's help strings encode as ASCII (covered by the PHASE-01 test once the
  subcommand exists; confirm it passes).

**Dependencies**
- PHASE-05.

**Exit Criteria**
- [ ] `python -m pytest tests/test_reconcile_diff.py tests/test_cli_hygiene.py -v` passes.
- [ ] `PYTHONIOENCODING=utf-8 pdd-agent reconcile --input configs/demo/inegol_project_input.yaml`
  runs on a machine with the workbook, writes `reports/reconcile/<slug>-<date>.md`, and exits
  `0` or `3` consistently with the printed verdict.
- [ ] `grep -n "is a stub" README.md` prints nothing; `grep -n "reconcile" README.md` prints at
  least two lines.
- [ ] Full suite `0 failed`; `ruff check .`, `ruff format --check .` and `uv lock --check` pass.

**Phase Risks**
- **RISK-06-01:** The reconcile report may publish numbers from a client-adjacent workbook.
  Mitigation: the report contains only schedule values, parameter comparisons and cell addresses,
  all of which also appear in the publicly registered PDD. The workbook file itself stays
  git-ignored.

## Gotchas

- `sub_section_id` in this codebase already contains the section prefix (`"4.1"`, not `"1"`).
  Never format `f"{section_id}.{sub_section_id}"`; that is exactly the "4.4.1" bug fixed in
  TASK-03-09.
- The registered workbook writes DOC as a **percentage** (`43`) and k as a **fraction** (`0.02`).
  Divide DOC by 100 and never divide k.
- The registered schedule's first row is a one-day stub (2020-12-31, Days = 1). Including it
  shifts every year by one and breaks the published totals (805,367 / 75,367 / 730,000 exclude it).
- The registered 2027 row covers 364 days (`01/01/2027 - 12/30/2027`). Treat it as a full
  crediting year: the Days filter is `< 300`, not `!= 365`.
- `INEGOL_ANNUAL_ERS = 104_285` is a 7-year **average**; `PddCalcResult.net_emission_reductions_tco2e`
  is a **year-1** scalar. Compare means with means (DEC-004).
- PyYAML's `safe_load` silently keeps the last of duplicate keys. Only `load_yaml_unique` catches
  them; configs loaded any other way are still exposed.
- The strict Inegol xfails turn the suite **red** when they start passing (`XPASS(strict)`).
  Removing the decorator is part of the fix, not a workaround.
- `configs/corpus_families.yaml` contains a mis-encoded stem (`"VCS_\xC3_demis_Project-Description.norm"`)
  copied byte-for-byte from the filesystem. Never retype or reformat that line when editing the file.
- The FTS5 table's `section_id` is `""` for methodology rows. Any `section_id = ?` filter hides
  them, which is why the normative channel searches without one.
- FTS5 `MATCH` syntax treats bare `-`, `"`, `(`, `)` and `*` as operators. Quote every multi-word
  term (`"anaerobic digestion"`), and reuse `search._clean_query` rules for single words.
- Per-year lists are indexed with **index 0 = crediting year 1**, the same convention as
  `capacity_ramp`. Carry the last value forward past the end.
- Windows consoles default to cp1252. Keep every new CLI help string and log event name ASCII, and
  pass `encoding="utf-8"` to every `open()` that reads YAML or writes reports.
- `data/runs/` also contains a large git-ignored staging folder (`data/runs/tinh-20260827/`, about
  1.4 GB). Never glob `data/runs/**` recursively in code or tests.

## Verification Strategy

- **TEST-001:** `python -m pytest -m "not corpus" -q` → ends with `0 failed`. The pass count is at
  least 974 plus the tests added by this plan. The number of xfails is at most 2, and every
  remaining xfail's reason carries a date on or after 2026-09-11.
- **TEST-002:** `ruff check . && ruff format --check . && uv lock --check` → all exit 0.
- **TEST-003:** `python -c "import pathlib; print(len(list(pathlib.Path('data/runs').glob('*.json'))))"`
  before and after TEST-001 → identical numbers (PHASE-01).
- **TEST-004:** `PYTHONIOENCODING=cp1252 pdd-agent --help > /dev/null; echo $?` → `0` (PHASE-01).
- **TEST-005:** `python -m pytest -m corpus -q tests/test_reconcile_workbook.py` on a machine with the
  workbook → passes. Without the workbook → skipped, not failed (PHASE-05).
- **MANUAL-001:** after PHASE-02, `pdd-agent build-index && PYTHONIOENCODING=utf-8 pdd-agent index-report --json`
  → `"documents": 17`, `"missing_documents": []`, and `EB111_repan07_ACM0022_v03.0.norm` in
  `rows_by_document` above 0.
- **MANUAL-002:** after PHASE-03, run the PHASE-03 data-check one-liner → precedent excludes
  `VCS_Inegol`, normative includes `EB111…`, and all scores are above 0.
- **MANUAL-003:** after PHASE-03, draft one section with the free `demo` provider and inspect the
  prompt capture: `pdd-agent draft --input configs/demo/inegol_project_input.yaml --provider demo --run-id verify-grounding`
  (all three flags exist on the `draft` subcommand). Open `data/runs/verify-grounding.json` and confirm section
  `4.1`'s `provenance` contains at least one `[METHODOLOGY:` entry and a
  `[GROUNDING: self-excluded VCS_Inegol_Project-Description.norm]` entry.
- **MANUAL-004:** after PHASE-06, `PYTHONIOENCODING=utf-8 pdd-agent reconcile --input configs/demo/inegol_project_input.yaml; echo "exit=$?"`
  → a Markdown report under `reports/reconcile/`. Its verdict line matches the exit code (`0` =
  PASS, `3` = FAIL), and its parameter-mismatch section lists no climate-zone mismatch.
- **OBS-001:** `pdd-agent build-index` output contains no `document_zero_rows` event on the local
  corpus. Every `compute_for` call on a config without a declared zone emits
  `calc_climate_zone_ambiguous` in its warnings.

## Risks and Alternatives

- **RISK-001:** Ranking and new documents change what every run retrieves, so drafts made after
  PHASE-03 are not comparable with earlier drafts. Mitigation: accepted. Committed demo and review
  packages are not regenerated by this plan.
- **RISK-002:** The per-year Inegol model may land outside tolerance even with sourced inputs
  (AD-pathway project emissions, TDL). Mitigation: the plan's exit criteria record measured
  residuals as dated strict xfails. Flipping tests green is not the goal; a sourced and measured
  engine is.
- **RISK-003:** The feature weights in S-1 are judgement, not calibration. Mitigation: they are
  module-level constants in `grounding/selection.py`, covered by tests that pin behaviour
  (ordering and exclusion), not exact score values beyond `> 0`, so they can be retuned later
  against a leave-one-out evaluation.
- **ALT-001:** Rank precedent with an embedding model. Rejected for this plan: it adds a model
  dependency and non-deterministic test fixtures, and deterministic features have not been tried.
- **ALT-002:** Only add `exclude_documents=` to the existing alphabetical lookup. Rejected:
  exclusion on top of an alphabetical sort just promotes the next document alphabetically.
- **ALT-003:** Derive wet vs dry from a bundled precipitation dataset. Rejected: a new data
  dependency. Declaring the zone from the project's own registered workbook is sourced and exact.
- **ALT-004:** Model a growing deposit by reusing `capacity_ramp`. Rejected: the ramp scales every
  past deposit by the current year's factor, which is wrong for FOD, where each year's deposit
  decays independently (S-4).
- **ALT-005:** Set Inegol's zone to dry and flip the xfail with no workbook reader. Rejected: it
  leaves the year-by-year shape unmeasured, and the next registered project would need the same
  manual transcription.

## Suggested Next Step

Execute PHASE-01. It is small, and it stops every later phase's test runs from writing into the run
store they measure. Then run the grounding track (PHASE-02 → PHASE-03) and the reconciliation
track (PHASE-04 → PHASE-05 → PHASE-06) in either order. Verify each phase's exit criteria before
starting the next phase in the same track.
