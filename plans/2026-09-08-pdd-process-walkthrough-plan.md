---
title: "Interactive Inegol PDD Walkthrough and Two-Track Practicality Comparison"
date: "2026-09-08"
status: "complete — all 5 phases shipped in 3a44a96 + e71f470 (reports/walkthrough/ page, bundle, scripts, 14 passing tests; phase-01..05 reports all PASS)"
request: "Build an interactive, step-by-step HTML walkthrough of the full PDD creation process (start to finish) with user input required at each step, following one real project end to end, so the reader can re-onboard on the process and compare the pdd-auto repo pipeline against the portable Codex workspace track on practicality."
plan_type: "multi-phase"
research_inputs:
  - "research/2026-09-08-pdd-process-walkthrough-brainstorm.md"
  - "research/2026-08-27-pdd-assembly-and-defensible-numbers-brainstorm.md"
---

# Plan: Interactive Inegol PDD Walkthrough and Two-Track Practicality Comparison

## Objective

Produce a single self-contained HTML page, committed at `reports/walkthrough/pdd-walkthrough.html`,
that walks a reader through how a Verra VCS Project Design Document (PDD) is actually
produced for one real project — **Inegol Integrated Solid Waste Storage and Disposal
Facility, VCS project ID 3908** — in 14 gated screens. At each screen the reader records a
prediction, is shown the real artifact produced by both production tracks, and scores the two
tracks against each other on four practicality axes. The page ends by rendering a copyable
decision brief.

Every fact shown on the page must come from a machine-generated evidence bundle
(`reports/walkthrough/inegol-evidence.json`) captured from real executions, so the page can be
regenerated after future runs instead of silently going stale.

## Context Snapshot

- **Current state:**
  - The PDD pipeline in this repository exists only as code plus partly stale prose docs.
    `activeContext.md` documents a plan two iterations old; `lessons.md` is empty;
    `README.md` line ~397 still describes `src/pdd_agent/ingest/registry_download.py` as a
    stub, which is no longer true.
  - `scripts/run_inegol_demo.py` already runs the Inegol project end to end with the `demo`
    provider and exports a DOCX to `output/latest-inegol-demo.docx`, but it does not publish a
    package folder, does not run the `noop` provider, and captures no structured evidence.
  - `scripts/compare_codex_vs_pipeline.py` produces a coarse metric comparison against a
    "Codex reference" but reads whichever run JSON happens to be newest in `data/runs/`, is not
    pinned to Inegol, and does not compare against the current portable workspace.
  - The second track — a portable Codex workspace — is staged (git-ignored) at
    `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/`. Its mechanical packaging
    pipeline has never completed on this machine because Poppler (`pdftoppm`) is absent.
  - No directory `reports/walkthrough/` exists.
- **Desired state:**
  - `reports/walkthrough/` contains a committed, regenerable interactive walkthrough plus the
    evidence bundle it renders from, plus two scripts that reproduce both.
  - Both tracks' Inegol artifacts have been produced by real execution on this machine, with
    measured wall-clock timings and file sizes.
- **Key repo surfaces:**
  - `src/pdd_agent/cli.py` — 25 subcommands; `calc`, `draft`, `review`, `export` are the ones used here.
  - `src/pdd_agent/agent/section_orchestrator.py` — `SectionOrchestrator.run()`,
    `.run_review()`, `._build_prompt()`, `.set_calc_result()`.
  - `src/pdd_agent/calc/dispatch.py` — `compute_for()`, `PddCalcResult`, `CalcComponent`, `AnnualErEntry`.
  - `src/pdd_agent/retrieval/search.py` — `get_examples_for_section()`, `RetrievalResult`.
  - `src/pdd_agent/export/docx_export.py` — `check_export_gate()`, `export_run_to_docx()`.
  - `src/pdd_agent/export/review_package.py` — `publish_review_package()`, `publish_demo_package()`.
  - `src/pdd_agent/llm/provider.py` — `DraftSection`, `DraftRun`, `get_provider_registry()`.
  - `schemas/project_input.py` — `ProjectInput` (top-level package, outside `src/`).
  - `configs/demo/inegol_project_input.yaml` — the subject project input.
  - `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/` — the second track.
  - `scripts/`, `tests/`, `reports/` — where new files land.
- **Out of scope:**
  - Any run using a metered or model-backed drafting provider (`openai`, `anthropic`,
    `ollama`, `claude-code`). Providers are restricted to `noop` and `demo`.
  - Launching or executing a Codex authoring session in the portable workspace.
  - Repairing defects the walkthrough surfaces: retrieval-index reachability, the two
    `xfail`s in `tests/test_registered_pdd_oracle.py`, the three unwired Verra table
    renderers (`risk_assessment`, `sustainable_development`, `data_gaps`), the uncalibrated
    LLM judge prompt, stale `docs/vietnam-pdd-*.md`.
  - Updating `activeContext.md` or `README.md` inconsistencies.
  - Any change to the FastAPI service under `src/pdd_agent/service/`.
  - Cross-validating the repository calculator against the five reconciled registered
    projects (VCS 4818 x2, 5040, 4940, 4921) held in the portable workspace. The walkthrough
    recommends this as follow-up work; it does not perform it.
  - Uploading anything to Google Drive, or sharing the page with anyone.

## Environment & Conventions

- **Stack:** Python >= 3.11 (`pyproject.toml` `requires-python`). Package `pdd_agent` under
  `src/`, plus a second top-level package `schemas/` that is deliberately outside `src/`
  (`[tool.hatch.build.targets.wheel] packages = ["src/pdd_agent", "schemas"]`). Build backend
  hatchling. Dependency manager for reproducible runs is **uv** with a committed `uv.lock`;
  a `.venv/` running Python 3.13.12 already exists in the repo root.
- **Setup:** `pip install -e ".[dev,service,export,llm,ingest]"` installs everything CI installs.
  If `.venv/` and `uv.lock` are present, prefer `uv sync --locked --all-extras`.
- **Build / Run:** There is no build step. The CLI entry point is the console script
  `pdd-agent` (`[project.scripts] pdd-agent = "pdd_agent.cli:main"`).
- **CRITICAL — how to invoke anything in this repo:** a stray `PYTHONPATH` on this machine
  pulls in an unrelated virtualenv and shadows the project packages, and the interpreter first
  on `PATH` is a Python 3.14 install that is **not** the project environment. Always clear
  `PYTHONPATH` and go through uv:
  - bash / Git Bash: `PYTHONPATH= uv run --no-sync pdd-agent <subcommand> ...`
  - PowerShell: `$env:PYTHONPATH = ""; uv run --no-sync pdd-agent <subcommand> ...`
  - `--no-sync` is required: without it uv may re-resolve and mutate `.venv/`.
  Every command in this plan is written in the bash form. Translate the `PYTHONPATH= ` prefix
  to the PowerShell form shown above when running on PowerShell.
- **Test:** full suite `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q`.
  Single file: `PYTHONPATH= uv run --no-sync python -m pytest tests/test_service.py -v`.
  Single test: `PYTHONPATH= uv run --no-sync python -m pytest tests/test_service.py::test_name -v`.
  The `corpus` marker is declared in `pyproject.toml` and marks tests that require
  `data/corpus/normalized/`; CI always deselects them. Baseline before this work:
  **960 passed, 2 xfailed, 7 deselected**.
- **Lint / format:** `PYTHONPATH= uv run --no-sync ruff check .` and
  `PYTHONPATH= uv run --no-sync ruff format --check .`. Line length **100**,
  target-version `py311`, `E402` ignored repo-wide, `.claude` excluded.
- **Lockfile:** `PYTHONPATH= uv run --no-sync uv lock --check` must stay clean. This plan adds
  **no** new Python dependencies, so the lockfile must not change.
- **Conventions & traps:**
  - Logging is structlog event-style: `logger.warning("event_name", key=value)` — an
    event-name string first, never an f-string sentence.
  - Pydantic v2 only for `ProjectInput` in `schemas/project_input.py`. Everything else uses
    stdlib `dataclasses`.
  - Emissions units are **tCO2e**; annual figures are **tCO2e/year**; crediting-period totals
    are **tCO2e** over the whole period. Grid emission factor is **tCO2e/MWh**. Waste
    throughput is **tonnes/year**. Installed capacity is **MW**. Generation is **MWh/year**.
    Never mix per-year and period totals in the same field.
  - Dates in `ProjectInput` are ISO `YYYY-MM-DD` strings.
  - Artifact areas have contracts: `reports/review-packages/` is the internal reviewer area
    where placeholder bodies and unresolved review notes are expected (`noop` provider);
    `reports/demo-packages/` is the client-demo area that must contain zero placeholders and
    carry synthetic-content disclosure (`demo` provider), and its run folders **are** committed.
  - `.gitignore` ignores `data/runs/*`, `data/index/*`, `data/corpus/raw/`,
    `data/corpus/normalized/`, `data/corpus/manifest.jsonl`, `output/`, and `ref/`.
    `reports/` is **not** ignored — everything written under `reports/walkthrough/` will be committed.
  - Optional external tools (`gws`, LibreOffice, Poppler) must degrade gracefully and must
    never become hard requirements of the package.
- **Repo map:**
  - `src/pdd_agent/{cli.py,agent/,calc/,retrieval/,review/,export/,llm/,ingest/,domain/,phase05/,phase06/,service/}`
  - `schemas/project_input.py` — Pydantic input contract; `schemas/pdd_section_schema.yaml` — the 36-section schema.
  - `configs/demo/inegol_project_input.yaml` — this plan's subject input.
  - `configs/projects/*.yaml` — other project inputs and their `*.assumptions.yaml` siblings.
  - `rules/verra/wte_review_rules.yaml` — rule-based review rules and rubrics.
  - `templates/VCS-Project-Description-Template-v4.4-FINAL2.docx` — the real Verra template used for export.
  - `scripts/` — operational entry points (`run_demo.py`, `run_inegol_demo.py`, `run_vietnam_pdd.py`, ...).
  - `tests/` — pytest suite; fixtures in `tests/fixtures/`.
  - `reports/` — committed HTML session reports and generated markdown reports.
  - `data/runs/` — per-run JSON, review state, exported DOCX (git-ignored).

## Research Inputs

- From `research/2026-09-08-pdd-process-walkthrough-brainstorm.md`:
  - The subject project must be **Inegol / VCS 3908**, because it is the only project present
    on both tracks: this repo holds `configs/demo/inegol_project_input.yaml` and
    `examples/example-inegol-demo.docx`, and the portable workspace holds an August 2026
    Verra pull for project 3908 plus its calculation workbooks.
  - The interaction model is **predict, then reveal, then judge** at every step, gated but
    with a visible skip control, so the reader tests their own model before seeing the answer.
  - Comparison must use exactly four axes at every step: **human minutes, money/token cost,
    defensibility to a validation body, and failure mode when it breaks.**
  - Fairness rule: lead with the `noop` provider output as the repository's honest unaided
    state, show `demo` output beside it explicitly labelled synthetic, and **never compare
    prose quality** — one track has no model-written prose at all in this exercise.
  - The page must carry an inline "reality check" band on every step stating what is
    genuinely true versus what a demo would imply.
  - The two tracks embody opposite philosophies about numbers: this repository **recomputes**
    emission reductions from first principles and validates against a registered project;
    the portable workspace **never recomputes** and instead transfers already-reported values
    with worksheet-cell lineage and attests that no new calculation was created.
  - Deliverable framing for scoring is "one excellent finished document handed over to a
    client", not a live product demo. This framing structurally favours provenance and
    packaging over throughput, and the page must say so explicitly so the reader can discount it.
- From `research/2026-08-27-pdd-assembly-and-defensible-numbers-brainstorm.md`:
  - Both previously open oracle mismatches were traced to **parameter provenance** errors, not
    model-structure errors: a first-order-decay rate column had been mislabelled by climate
    zone, and a plastics mass fraction was wrong. Fitting parameters or widening the tolerance
    was explicitly rejected. The walkthrough's calc step should present the decay-rate
    parameter choice as a first-class, human-owned decision.
  - The standing structural criticism of this repository's approach is that "nobody owns the
    assembled document" — 36 independently generated sections are stapled together. The
    walkthrough's drafting and assembly steps must show this honestly rather than hide it.

## Assumptions and Constraints

- **DEC-001:** Subject project is Inegol / VCS 3908, input file `configs/demo/inegol_project_input.yaml`.
- **DEC-002:** Providers are limited to `noop` and `demo`. No metered or model-backed run.
- **DEC-003:** Fourteen screens: step 00 orientation, steps 01-11 the pipeline, step 12 breadth
  across other methodologies, step 13 verdict.
- **DEC-004:** Four scoring axes per step: `human_minutes`, `cost`, `defensibility`, `failure_mode`.
- **DEC-005:** Output lives at `reports/walkthrough/` as a local HTML file opened from disk and
  committed to git. No hosting, no server, no external network dependency at view time.
- **DEC-006:** Reader state (predictions, scores, notes) persists in browser `localStorage`,
  with an explicit JSON export/import control as the durable fallback.
- **DEC-007:** The page is generated by a render script from an evidence bundle, so it can be
  regenerated when the pipeline changes.
- **DEC-008:** The drafting step shows all 36 subsections in a compact grid, with four opened
  in depth: `4.1` (calc-injected), `3.5` (never auto-approvable), `1.13` (prior conditions),
  and `1.1` as a low-stakes contrast section.
- **ASM-001:** `configs/demo/inegol_project_input.yaml` satisfies the ACM0022 calculation gate.
  **Verified**: it sets `quantification.grid_emission_factor: 0.5410` and a non-empty
  `grid_emission_factor_source`, and `pdd-agent calc` returns a full result (see `## Specification`).
- **ASM-002:** There is **no** `configs/demo/inegol_project_input.assumptions.yaml` sibling file.
  **BINDING DEFAULT:** do not create one. Record in the evidence bundle that the Inegol run has
  no assumption register, and have the walkthrough state that the assumption-gating review path
  is therefore inactive for this project and is shown from the rules file rather than from a run.
- **ASM-003:** The 3908 documents in the portable workspace may be a different revision from the
  source used to author `configs/demo/inegol_project_input.yaml`.
  **BINDING DEFAULT:** do not assert they match. Capture `project.vcs_standard_version` and
  `project.audit_history` from the YAML, and the filenames plus SHA-256 of every file under
  `inputs/fresh_registry/verra_public_download_3908_20260824/project_3908/extracted/`, and render
  a "provenance note: vintages not proven identical" banner on the intake and quantification steps.
- **ASM-004:** Poppler is not installed on this machine and `pdftoppm` is not on `PATH` (verified).
  **BINDING DEFAULT:** install Poppler for Windows as a **portable extraction only**, into
  `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/tools/poppler/`, so that
  `tools/poppler/Library/bin/pdftoppm.exe` exists. That exact path is already a lookup candidate
  inside `scripts/run_pdd_in_place.py` (`find_pdftoppm`). Do **not** modify the system `PATH`, and
  do not add Poppler to any project requirement file. If extraction is impossible, pass the
  binary explicitly with `--pdftoppm <path>` instead.
- **ASM-005:** LibreOffice is installed at `C:\Program Files\LibreOffice\program\soffice.exe`
  (verified), which is the first Windows candidate in `find_soffice`.
- **ASM-006:** The portable-workspace run must execute from a **short** filesystem path.
  **BINDING DEFAULT:** stage the run output under `C:/t3908/job`. LibreOffice's
  `-env:UserInstallation` handling on this machine fails silently with exit code 1 at deep paths
  and succeeds at short ones; a previous attempt reproduced exactly this.
- **ASM-007:** The `noop` provider run may trip export-gate hard blocks.
  **BINDING DEFAULT:** attempt the export without `--force` first and record the exact failure
  text as evidence; then re-run with `--force` and record that the override was required. The
  gate's behaviour is itself a walkthrough finding, not an obstacle to route around silently.
- **ASM-008:** Wall-clock timings measured on one Windows machine are representative enough to
  populate the `human_minutes` axis. **BINDING DEFAULT:** record every timing with the machine's
  OS string and Python version in the bundle's `environment` block, and label all timings on the
  page as "measured once on one machine", never as benchmarks.
- **ASM-009:** The reader's browser is Chromium- or Firefox-based and opens the page over `file://`.
  **BINDING DEFAULT:** the page must not `fetch()` any sibling file — the evidence JSON is
  **embedded** into the HTML at render time. It must not load any external stylesheet, font, or
  script. It must degrade to read-only if `localStorage` throws.
- **CON-001:** No API keys exist in this environment; none may be added. Nothing in this plan may
  require network access at run time or at view time.
- **CON-002:** Tests must never require API keys, network access, a running Ollama instance, or
  the normalized corpus unless marked with the `corpus` marker.
- **CON-003:** New Python must pass `ruff check .` and `ruff format --check .` at line length 100
  and use structlog event-style logging.
- **CON-004:** No new third-party dependency may be introduced; `uv lock --check` must stay clean.
- **CON-005:** Nothing under `data/runs/`, `data/index/`, `data/corpus/`, `output/`, or `ref/` is
  committed. The evidence bundle must therefore be self-contained under `reports/walkthrough/`
  and must not merely point at git-ignored paths for content the page needs to display.
- **CON-006:** The generated HTML must stay under 5 MB so it opens instantly and diffs sanely in
  git. Excerpt long text rather than embedding whole documents.

## Specification

### S1. ACM0022 equation chain for Inegol, with the values this repository actually computes

Command that produces these values (verified on 2026-09-08):

```
PYTHONPATH= uv run --no-sync pdd-agent calc --input configs/demo/inegol_project_input.yaml
```

Emission-reduction identity, evaluated per crediting year `y`:

```
ER_y = BE_y - PE_y - LE_y
```

- `ER_y` — net emission reductions in year `y`, tCO2e.
- `BE_y` — baseline emissions in year `y`, tCO2e: what would have happened without the project.
- `PE_y` — project emissions in year `y`, tCO2e: emissions the project itself causes.
- `LE_y` — leakage in year `y`, tCO2e: emissions displaced outside the project boundary.

Baseline decomposition:

```
BE_y = BE_CH4,y + BE_EC,y
```

- `BE_CH4,y` — methane that the diverted waste would have emitted from the solid-waste disposal
  site, computed by a first-order decay model over the waste already deposited. **32,320.71 tCO2e/year**
  for Inegol year 1. Source: ACM0022 Equation 1 with CDM Tool 04 Equation 2.
- `BE_EC,y` — grid electricity the project displaces, equal to exported MWh multiplied by the
  grid emission factor and by one plus the transmission-and-distribution loss factor.
  **27,015.01 tCO2e/year**. Source: ACM0022 Equation 13 with CDM Tool 05 Equation 2.

Project decomposition:

```
PE_y = PE_EC,y + PE_FC,y + PE_CH4,y + PE_COM_CO2,y + PE_COM_CH4_N2O,y + PE_WW,y
```

- `PE_EC,y` — grid electricity the plant imports. **0.00** for Inegol.
- `PE_FC,y` — fossil fuel burned on site (start-up, auxiliary). **0.00** for Inegol.
- `PE_CH4,y` — methane leaking from the anaerobic digester. **8,645.23 tCO2e/year**.
  Source: CDM Tool 14 Equation 4.
- `PE_COM_CO2,y` — carbon dioxide from the **fossil** carbon fraction of combusted waste
  (plastics, synthetic textiles). **0.00** for Inegol. Source: ACM0022 Equation 22.
- `PE_COM_CH4_N2O,y` — methane and nitrous oxide from combustion. **0.00**. ACM0022 Equation 27.
- `PE_WW,y` — emissions from run-off wastewater. **0.00**. ACM0022 Equation 28.

Leakage decomposition:

```
LE_y = LE_RDF,y + LE_AD,y
```

- `LE_RDF,y` — emissions from end-use of refuse-derived fuel sent off site. **0.00**. ACM0022 Equation 34.
- `LE_AD,y` — emissions from digestate storage. **0.00**. CDM Tool 14 Equation 5.

Totals actually returned for Inegol:

| Quantity | Value | Unit |
|---|---|---|
| Baseline emissions | 59,335.71 | tCO2e/year |
| Project emissions | 8,645.23 | tCO2e/year |
| Leakage | 0.00 | tCO2e/year |
| Net emission reductions | 50,690.48 | tCO2e/year |
| Crediting period total | 893,441.43 | tCO2e over 7 years |

Year-by-year schedule (the first-order decay model means year 1 is the **smallest** year, not
an average — this is the single most misread number in the whole pipeline):

| Year | Net ER (tCO2e) |
|---|---|
| 1 | 50,690.48 |
| 2 | 80,229.38 |
| 3 | 107,225.90 |
| 4 | 131,898.87 |
| 5 | 154,448.26 |
| 6 | 175,056.85 |
| 7 | 193,891.69 |

Calculation warning emitted, which must be shown on the page verbatim:

```
calc_climate_zone_resolved: zone=boreal_temperate_wet derived=True
```

`derived=True` means no `location.climate_zone` was supplied and the zone — which selects the
methane decay-rate column and therefore drives the entire baseline — was inferred from latitude.
This is the exact parameter-provenance class of error that previously caused oracle mismatches,
so the walkthrough must present it as an open human decision, not a solved one.

### S2. Scoring model and aggregation

Each of the twelve judgeable steps (`01` through `12`) records four integer scores on a single
comparative scale. The scale is deliberately relative, not absolute, so the reader makes one
judgement per axis rather than eight:

```
-2 = repository pipeline clearly better
-1 = repository pipeline slightly better
 0 = no meaningful difference
+1 = portable-workspace track slightly better
+2 = portable-workspace track clearly better
```

Axis keys and their exact questions, which must appear as the on-page labels:

1. `human_minutes` — "Which track needs less skilled human time at this step?"
2. `cost` — "Which track costs less in money or tokens at this step?"
3. `defensibility` — "Which track's output at this step is easier to defend to a validation body?"
4. `failure_mode` — "When this step goes wrong, which track fails more safely and more visibly?"

Aggregation, computed in the page at render time of step 13:

1. Per-axis total: sum the axis score across every step the reader scored. Skipped steps
   contribute nothing and are excluded from the divisor.
2. Per-axis mean: per-axis total divided by the number of steps scored on that axis, rounded to
   one decimal place.
3. Overall mean: mean of the four per-axis means, rounded to one decimal place.
4. Deliverable-weighted mean: because the framing deliverable is one finished document handed to
   a client, re-weight the axes as `defensibility` 0.4, `human_minutes` 0.3, `failure_mode` 0.2,
   `cost` 0.1, and compute the weighted sum of the per-axis means.
5. The page must display **both** the unweighted overall mean and the deliverable-weighted mean
   side by side, with a one-sentence caution that the weighting was chosen before the evidence was
   seen and structurally favours the provenance-heavy track.
6. Divergence list: any step where the four axis scores span 3 or more points (that is,
   `max(scores) - min(scores) >= 3`) is listed under "steps where the tracks trade off against
   each other" in the decision brief, because those are the steps where a merged pipeline would
   take one track's approach for one reason and the other's for another.

## Phase Summary

| Phase | Goal | Dependencies | Primary outputs |
|---|---|---|---|
| PHASE-01 | Execute the repository pipeline on Inegol with both `noop` and `demo` providers and capture raw artifacts and timings | None | Run JSONs, review JSONs, DOCX files, published packages, `reports/walkthrough/raw/` capture logs |
| PHASE-02 | Install portable Poppler and complete the portable-workspace mechanical packaging run for project 3908 | None (parallel with PHASE-01) | Merged evidence PDF, run manifest, `reports/walkthrough/raw/tinh-run.json` |
| PHASE-03 | Build the evidence-bundle generator and produce `inegol-evidence.json` | PHASE-01, PHASE-02 | `scripts/build_walkthrough_evidence.py`, `reports/walkthrough/inegol-evidence.json`, tests |
| PHASE-04 | Build the HTML template and renderer, producing the interactive page | PHASE-03 | `reports/walkthrough/template.html`, `scripts/render_walkthrough.py`, `reports/walkthrough/pdd-walkthrough.html`, tests |
| PHASE-05 | Verify end to end, document, and commit | PHASE-04 | `reports/walkthrough/README.md`, clean test/lint/lock run, single commit |

## Detailed Phases

### PHASE-01 - Capture the repository lane on Inegol

**Goal**
Produce real Inegol artifacts from this repository using only the `noop` and `demo` providers,
and record the timings, exit codes, and gate behaviour that the walkthrough will display.

**Tasks**
- [x] TASK-01-01: Create directories `reports/walkthrough/` and `reports/walkthrough/raw/`.
  Add `reports/walkthrough/raw/.gitkeep`.
- [x] TASK-01-02: Record the environment. Run each of the following and save the combined output
  to `reports/walkthrough/raw/environment.txt`:
  ```
  PYTHONPATH= uv run --no-sync python -c "import sys, platform; print(sys.version); print(platform.platform())"
  PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q 2>&1 | tail -5
  git rev-parse HEAD
  ```
- [x] TASK-01-03: Capture retrieval-index health as JSON:
  ```
  PYTHONPATH= uv run --no-sync pdd-agent index-report --json > reports/walkthrough/raw/index-report.json
  ```
  If `data/index/corpus.fts.db` is missing, first build the demo index with
  `PYTHONPATH= uv run --no-sync pdd-agent demo-setup` and record in the file which index was used.
- [x] TASK-01-04: Capture the calculation result as JSON and as human-readable text:
  ```
  PYTHONPATH= uv run --no-sync pdd-agent calc --input configs/demo/inegol_project_input.yaml --output reports/walkthrough/raw/calc-inegol.json
  PYTHONPATH= uv run --no-sync pdd-agent calc --input configs/demo/inegol_project_input.yaml > reports/walkthrough/raw/calc-inegol.txt 2>&1
  ```
- [x] TASK-01-05: Run the full 36-section draft with the `noop` provider, using a fixed run id so
  the artifacts are addressable, and time it:
  ```
  PYTHONPATH= uv run --no-sync python -c "import time,subprocess,sys,json,pathlib; t=time.perf_counter(); r=subprocess.run([sys.executable,'-m','pdd_agent.cli','draft','--input','configs/demo/inegol_project_input.yaml','--provider','noop','--run-id','walkthrough-inegol-noop','--no-judge'],capture_output=True,text=True); d=round(time.perf_counter()-t,3); pathlib.Path('reports/walkthrough/raw/draft-noop.json').write_text(json.dumps({'seconds':d,'returncode':r.returncode,'stdout':r.stdout[-8000:],'stderr':r.stderr[-8000:]},indent=2),encoding='utf-8'); print(d, r.returncode)"
  ```
- [x] TASK-01-06: Run review for the `noop` run and save stdout:
  ```
  PYTHONPATH= uv run --no-sync pdd-agent review --run-id walkthrough-inegol-noop --input configs/demo/inegol_project_input.yaml > reports/walkthrough/raw/review-noop.txt 2>&1
  ```
- [x] TASK-01-07: Attempt the `noop` export **without** `--force`, capturing the exact outcome
  (this is evidence, see ASM-007):
  ```
  PYTHONPATH= uv run --no-sync pdd-agent export --run-id walkthrough-inegol-noop --input configs/demo/inegol_project_input.yaml > reports/walkthrough/raw/export-noop-unforced.txt 2>&1; echo "exit=$?" >> reports/walkthrough/raw/export-noop-unforced.txt
  ```
  Then, only if the unforced attempt did not produce `data/runs/walkthrough-inegol-noop.docx`,
  re-run with `--force` into `reports/walkthrough/raw/export-noop-forced.txt`.
- [x] TASK-01-08: Repeat TASK-01-05 through TASK-01-07 for the `demo` provider with run id
  `walkthrough-inegol-demo`, writing to `draft-demo.json`, `review-demo.txt`,
  `export-demo.txt`. Do not pass `--judge` in either run.
- [x] TASK-01-09: Publish both packages **programmatically**, not via `--review-output-dir`
  (see RISK-01-01). Write a one-off snippet that calls `publish_review_package` for the `noop`
  run into `reports/review-packages/` and `publish_demo_package` for the `demo` run into
  `reports/demo-packages/`, passing `project_name` from
  `ProjectInput.project.project_name` (`"INEGOL INTEGRATED SOLID WASTE STORAGE AND DISPOSAL FACILITY"`),
  `project_yaml_path=configs/demo/inegol_project_input.yaml`, `assumptions_yaml_path=Path("")`,
  and `assumption_burden_path=reports/assumption-burden.md`. Save the returned package paths to
  `reports/walkthrough/raw/packages.json`.
- [x] TASK-01-10: Confirm that `data/runs/walkthrough-inegol-noop.json`,
  `data/runs/walkthrough-inegol-demo.json`,
  `data/runs/review-state-walkthrough-inegol-noop.json`, and
  `data/runs/review-state-walkthrough-inegol-demo.json` all exist and are valid JSON.

**File Changes**
- `reports/walkthrough/raw/.gitkeep` (create): empty file so the directory is tracked.
- `reports/walkthrough/raw/environment.txt` (create): interpreter version, platform string,
  test-suite tail, commit SHA.
- `reports/walkthrough/raw/index-report.json` (create): retrieval-index health as emitted by `index-report --json`.
- `reports/walkthrough/raw/calc-inegol.json` (create): serialized `PddCalcResult`.
- `reports/walkthrough/raw/calc-inegol.txt` (create): the human-readable calc printout.
- `reports/walkthrough/raw/draft-noop.json`, `draft-demo.json` (create): `{seconds, returncode, stdout, stderr}`.
- `reports/walkthrough/raw/review-noop.txt`, `review-demo.txt` (create): review stdout.
- `reports/walkthrough/raw/export-noop-unforced.txt`, `export-noop-forced.txt`, `export-demo.txt` (create): export stdout plus exit code.
- `reports/walkthrough/raw/packages.json` (create): published package directory paths for both lanes.
- No existing source file is modified in this phase. Do **not** edit
  `scripts/run_inegol_demo.py` or `scripts/compare_codex_vs_pipeline.py`.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
None — no testable behavior changes in this phase. Correctness is asserted by the exit criteria below.

**Dependencies**
- The project virtualenv at `.venv/` with the package installed in editable mode.
- `data/index/corpus.fts.db` or, failing that, `data/index/demo.fts.db` built by `pdd-agent demo-setup`.

**Exit Criteria**
- [ ] `PYTHONPATH= uv run --no-sync python -c "import json;d=json.load(open('reports/walkthrough/raw/calc-inegol.json'));print(round(d['crediting_period_total_tco2e'],2))"` prints `893441.43`.
- [ ] `data/runs/walkthrough-inegol-noop.json` exists and its `sections` array has length `36`.
- [ ] `data/runs/walkthrough-inegol-demo.json` exists and its `sections` array has length `36`.
- [ ] `data/runs/walkthrough-inegol-noop.docx` and `data/runs/walkthrough-inegol-demo.docx` both exist and are larger than 20,000 bytes.
- [ ] `reports/walkthrough/raw/packages.json` names one directory under `reports/review-packages/` and one under `reports/demo-packages/`, and both directories contain a `manifest.json`.
- [ ] Every confidence value in the `noop` run is `UNSUPPORTED`, and at least 30 of the 36 `demo` sections are `HIGH`.

**Phase Risks**
- **RISK-01-01:** `pdd-agent export --review-output-dir` takes a code path that passes
  `project_name=args.run_id` (so the package folder is named after the run id, not the project)
  **and** calls `export_run_to_docx()` without `project_input` or `force`, so a hard-blocked
  export raises out of that branch instead of being caught. Mitigation: TASK-01-09 publishes
  packages by calling `publish_review_package` / `publish_demo_package` directly, and the plain
  `pdd-agent export` form is used for the DOCX.
- **RISK-01-02:** `pdd-agent --help` raises `UnicodeEncodeError` under the Windows cp1252 console
  because of an arrow glyph, and the `calc` text output renders `→` as a replacement character.
  Mitigation: never depend on `--help` output; set `PYTHONIOENCODING=utf-8` before capturing text
  output, and prefer the `--output`/`--json` machine-readable forms wherever they exist.
- **RISK-01-03:** The `noop` run may write no `reports/assumption-burden.md` because Inegol has no
  assumption register (ASM-002). Mitigation: treat a missing file as expected;
  `publish_review_package` already tolerates missing paths via `_copy_if_exists`.

### PHASE-02 - Capture the portable-workspace lane for project 3908

**Goal**
Complete the mechanical packaging pipeline of the portable Codex workspace for project 3908 so the
comparison rests on measured artifacts rather than on documentation, and record precisely which
stage is executed versus reviewed-from-documentation.

**Tasks**
- [x] TASK-02-01: Confirm the workspace is present and record its inventory:
  ```
  ls "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827"
  ls "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/inputs/fresh_registry/verra_public_download_3908_20260824/project_3908/extracted"
  ```
  Expected in `extracted/`: `INEGOL_PDD_PRR_R3_clean.pdf`, `ER Calculation.v04_21.07.2025.xlsx`,
  `INEGOL_CPA_R3_21.07.2025.xlsx`, `Inegol IRR_R5_22.08.2025.xlsx`, plus approval, deed,
  validation-report and exemption PDFs.
- [x] TASK-02-02: Compute SHA-256 for every file in that `extracted/` directory and save to
  `reports/walkthrough/raw/tinh-3908-hashes.json` as an object mapping filename to
  `{sha256, bytes}`. Use `hashlib.sha256` over 1 MiB chunks.
- [x] TASK-02-03: Install Poppler portably per ASM-004. Download a Poppler-for-Windows release
  archive, extract it so that
  `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/tools/poppler/Library/bin/pdftoppm.exe`
  exists. Verify with:
  ```
  "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/tools/poppler/Library/bin/pdftoppm.exe" -v
  ```
  Record the resolved version string and the exact download URL in
  `reports/walkthrough/raw/tinh-tools.txt`. Do not alter the system `PATH`.
- [x] TASK-02-04: Create the short staging root `C:/t3908/job` (ASM-006).
- [x] TASK-02-05: Run the workspace's own packaging pipeline, timed, from the short path:
  ```
  PYTHONPATH= uv run --no-sync python "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/scripts/run_pdd_in_place.py" --input-dir "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/inputs/fresh_registry/verra_public_download_3908_20260824/project_3908/extracted" --template "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/library/templates/vcs/VCS-Project-Description-Template-v4.4-FINAL2.docx" --output-dir "C:/t3908/job" --soffice "C:/Program Files/LibreOffice/program/soffice.exe" --pdftoppm "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/tools/poppler/Library/bin/pdftoppm.exe"
  ```
  Wrap the invocation in the same timing pattern used in TASK-01-05 and write
  `{seconds, returncode, stdout, stderr}` to `reports/walkthrough/raw/tinh-run.json`.
  If the template path above does not exist, locate the actual template with
  `find "data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/library/templates" -name "*.docx"`
  and use the VCS v4.4 file found there.
- [x] TASK-02-06: Record the output inventory: for every file produced under `C:/t3908/job`,
  capture relative path, byte size, and — for PDFs — page count via `pypdf.PdfReader`. Save to
  `reports/walkthrough/raw/tinh-outputs.json`.
- [x] TASK-02-07: Copy only the run manifest produced by the pipeline (a small JSON) into
  `reports/walkthrough/raw/tinh-run-manifest.json`. Do **not** copy the merged PDF or any
  workbook into `reports/` — they are large and the walkthrough only needs their metadata (CON-006).
- [x] TASK-02-08: Extract, verbatim, the canonical process description and release gates from
  `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/process/PDD_CREATION_PROCESS.md`
  into `reports/walkthrough/raw/tinh-process-excerpt.md`. Cap the excerpt at 400 lines. This is
  the only source for the authoring stage, which is **not** executed.
- [x] TASK-02-09: Write `reports/walkthrough/raw/tinh-execution-status.json` recording, per stage,
  whether it was `executed` or `documented_only`. The authoring stage must be `documented_only`.

**File Changes**
- `reports/walkthrough/raw/tinh-3908-hashes.json` (create): filename to `{sha256, bytes}`.
- `reports/walkthrough/raw/tinh-tools.txt` (create): Poppler version and download URL, LibreOffice path.
- `reports/walkthrough/raw/tinh-run.json` (create): timing, exit code, truncated stdout and stderr.
- `reports/walkthrough/raw/tinh-outputs.json` (create): produced-file inventory with sizes and PDF page counts.
- `reports/walkthrough/raw/tinh-run-manifest.json` (create): copy of the pipeline's own run manifest.
- `reports/walkthrough/raw/tinh-process-excerpt.md` (create): verbatim process and gate text, capped at 400 lines.
- `reports/walkthrough/raw/tinh-execution-status.json` (create): per-stage `executed` / `documented_only`.
- Nothing inside `data/runs/tinh-20260827/` is modified except the addition of the `tools/poppler/`
  directory. That entire tree is git-ignored, so no workspace content enters the repository.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
None — no testable behavior changes in this phase.

**Dependencies**
- LibreOffice at the path in ASM-005.
- A portable Poppler build providing `pdftoppm.exe`.
- Write access to `C:/`.

**Exit Criteria**
- [ ] `pdftoppm -v` succeeds from the portable path and its version string is recorded.
- [ ] `reports/walkthrough/raw/tinh-run.json` contains `"returncode": 0`.
- [ ] `reports/walkthrough/raw/tinh-outputs.json` lists at least one merged PDF with a page count
      of 500 or more, and at least three workbook-derived PDFs.
- [ ] `reports/walkthrough/raw/tinh-3908-hashes.json` contains an entry for `INEGOL_PDD_PRR_R3_clean.pdf`.
- [ ] `reports/walkthrough/raw/tinh-execution-status.json` marks the authoring stage `documented_only`.
- [ ] `git status --porcelain data/runs` prints nothing.

**Phase Risks**
- **RISK-02-01:** LibreOffice conversion fails silently with exit code 1 when the staging path is
  long. Mitigation: ASM-006 mandates `C:/t3908/job`; if conversion still fails, retry at an even
  shorter root such as `C:/t1` before investigating further.
- **RISK-02-02:** The merged output can approach 10 MB and the intermediate page images far more.
  Mitigation: nothing large is copied into `reports/` (TASK-02-07); `C:/t3908/` stays outside the repo.
- **RISK-02-03:** Some manifest entries in the workspace are known to be unverifiable because a
  folder was renamed after the manifest was generated (en-dashes replaced by hyphens). Mitigation:
  hash only the 3908 `extracted/` directory (TASK-02-02) rather than re-verifying the whole
  workspace manifest, and note the known rename defect in the bundle's `tinh_lane.known_defects`.
- **RISK-02-04:** If Poppler cannot be obtained at all, PHASE-02 cannot meet its exit criteria.
  Fallback: set every `tinh_lane` execution field to `documented_only`, populate the lane from
  `reports/2026-09-04-tinh-portable-workspace-test-report.html` and the process excerpt, and set
  `tinh_lane.evidence_grade` to `"documented"` instead of `"measured"`. The page must then display
  a prominent banner on every step saying the second lane is unexecuted. Do not silently omit the banner.

### PHASE-03 - Build the evidence bundle

**Goal**
Turn the raw captures from PHASE-01 and PHASE-02 into one validated, versioned JSON document that
fully determines the walkthrough's content.

**Tasks**
- [x] TASK-03-01: Create `scripts/build_walkthrough_evidence.py`. It must import nothing outside
  the repo's existing dependencies, clear no global state, and write exactly one file.
- [x] TASK-03-02: Implement the raw-artifact readers: load every file written under
  `reports/walkthrough/raw/`, tolerating absent optional files by recording `null` plus a
  `missing_inputs` list rather than raising.
- [x] TASK-03-03: Implement `capture_retrieval(section_ids)` which, for each of the four focus
  subsections `4.1`, `3.5`, `1.13`, `1.1`, calls
  `pdd_agent.retrieval.search.get_examples_for_section` and records for each hit:
  `document_name`, `canonical_heading`, `score`, `matched_terms`, `from_fallback_family`, and a
  400-character excerpt. If the retrieval index is unavailable, record an empty list plus the
  reason string; this is itself a finding.
- [x] TASK-03-04: Implement `capture_prompt(section_id, sub_section_id)` which constructs a
  `SectionOrchestrator` with the `noop` provider and the Inegol `ProjectInput`, attaches the calc
  result via `set_calc_result`, and captures the assembled prompt for subsection `4.1` by calling
  the orchestrator's prompt builder. Store the full prompt text if under 20,000 characters,
  otherwise the first and last 8,000 characters with an elision marker, plus the true character
  count and a per-component character breakdown.
- [x] TASK-03-05: Implement `summarize_sections(run_dict)` producing, for all 36 subsections:
  `sub_section_id`, `heading`, `confidence`, `char_count`, `issue_count`, `provenance_count`,
  `review_state`, and `has_structured_content`. Read review states from
  `data/runs/review-state-{run_id}.json`.
- [x] TASK-03-06: Implement `focus_sections(run_dict)` producing, for `4.1`, `3.5`, `1.13`, `1.1`,
  the full section text capped at 4,000 characters plus the complete `issues`, `provenance`,
  `fact_provenance`, and `synthetic_uses` arrays.
- [x] TASK-03-07: Implement `capture_export_gate()` which calls
  `pdd_agent.export.docx_export.check_export_gate` on both run dicts with the Inegol
  `ProjectInput` and the calc result, and records `hard_blocks`, `required_inputs` count,
  `advisory` count, and whether export would have proceeded without `--force`.
- [x] TASK-03-08: Implement `capture_breadth()` which reads
  `pdd_agent.calc.dispatch.ENGINE_BY_METHODOLOGY` and, for each of `VM0051`, `VM0044`,
  `AMS-II.G`, records the engine module path, the `ProjectInput` field that gates it
  (`technology.rice_cultivation`, `technology.biochar_production`, `technology.cookstove_fleet`),
  and whether any corpus document, registered oracle, or review-rules file exists for it.
- [x] TASK-03-09: Implement `build_reality_checks()` returning the fixed list of honest-state
  statements the page must show. At minimum: no model-backed drafting run has ever been performed
  in this repository beyond a single-section smoke test; all prose shown here is placeholder or
  synthetic; the retrieval index's reachable row count is lower than its headline row count
  (take exact numbers from `index-report.json`); the ACM0022 methodology document itself is not
  reachable through retrieval; three of eleven Verra structured-table renderers are unwired;
  two oracle tests remain `xfail`; the climate zone driving the baseline was derived from
  latitude rather than supplied; the portable-workspace authoring stage was not executed.
- [x] TASK-03-10: Assemble and write `reports/walkthrough/inegol-evidence.json` per the schema in
  the Gotchas section. Include `schema_version: "1.0"` and a UTC `generated_at`.
- [x] TASK-03-11: Add `tests/test_walkthrough_evidence.py` covering the pure helpers only. No test
  may execute the pipeline, touch the network, or require `data/runs/` content.

**File Changes**
- `scripts/build_walkthrough_evidence.py` (create): the capture and assembly script; module
  docstring, `from __future__ import annotations`, structlog logger, `main() -> int`,
  `if __name__ == "__main__": raise SystemExit(main())`. Follow the `sys.path` bootstrap pattern
  already used at the top of `scripts/run_inegol_demo.py` so `schemas` resolves.
- `reports/walkthrough/inegol-evidence.json` (create): the generated bundle.
- `tests/test_walkthrough_evidence.py` (create): unit tests for the pure helpers.

**Function Signatures**
- `load_raw(raw_dir: Path) -> tuple[dict[str, Any], list[str]]` — returns the parsed raw captures keyed by filename stem, and a list of names of files that were expected but absent.
- `summarize_sections(run: dict[str, Any], review_state: dict[str, Any] | None) -> list[dict[str, Any]]` — returns one summary record per drafted subsection, ordered by `sub_section_id` using a natural numeric sort.
- `focus_sections(run: dict[str, Any], sub_section_ids: list[str], max_chars: int = 4000) -> dict[str, dict[str, Any]]` — returns a mapping from subsection id to its truncated text and full issue/provenance arrays.
- `capture_retrieval(sub_section_ids: list[str], family_slug: str = "wte") -> dict[str, Any]` — returns per-subsection retrieval hits with scores and fallback flags, or an empty list plus a reason when no index is available.
- `capture_prompt(project_input_path: Path, sub_section_id: str = "4.1") -> dict[str, Any]` — returns the assembled prompt text (possibly elided), its true character count, and a per-component character breakdown.
- `capture_export_gate(run: dict[str, Any], project_input_path: Path, calc: dict[str, Any] | None) -> dict[str, Any]` — returns hard-block list, required-input count, advisory count, and a boolean `would_export_unforced`.
- `capture_breadth() -> list[dict[str, Any]]` — returns one record per non-ACM0022 engine with its gating field and the presence or absence of corpus, oracle, and review rules.
- `build_reality_checks(index_report: dict[str, Any] | None) -> list[dict[str, str]]` — returns records of `{id, claim, truth, severity}` where severity is one of `info`, `caution`, `material`.
- `build_bundle(raw_dir: Path, project_input_path: Path) -> dict[str, Any]` — returns the complete evidence bundle ready to serialize.
- `main() -> int` — writes the bundle and returns `0` on success, `1` when a mandatory raw input is missing.

**Test Specs**
- `summarize_sections({"sections": [{"section_id": "4", "sub_section_id": "4.1", "text": "abc", "confidence": "UNSUPPORTED", "issues": ["x"], "provenance": [], "structured_content": None}]}, None)` → a one-element list whose single record has `char_count == 3`, `issue_count == 1`, `provenance_count == 0`, `has_structured_content is False`, `review_state is None`.
- `summarize_sections` given subsections in the order `["4.10", "4.2", "1.1"]` → returns them ordered `["1.1", "4.2", "4.10"]`. A plain lexicographic sort would wrongly place `4.10` before `4.2`; the sort must split on `.` and compare integer components.
- `focus_sections({"sections": [{"section_id": "4", "sub_section_id": "4.1", "text": "x" * 5000, "issues": [], "provenance": [], "fact_provenance": [], "synthetic_uses": []}]}, ["4.1"], max_chars=4000)` → `result["4.1"]["text"]` has length `4000` and `result["4.1"]["truncated"] is True`.
- `focus_sections(..., ["9.9"])` for a subsection that does not exist → `result == {}` and no exception.
- `build_reality_checks(None)` → a list of at least 6 records, every record has non-empty `id`, `claim`, `truth`, and a `severity` in `{"info", "caution", "material"}`, and at least one record has severity `material`.
- `build_reality_checks({"headline_rows": 3026, "reachable_rows": 889, "documents": 17, "reachable_documents": 13})` → at least one record whose `truth` contains both `"889"` and `"3026"`.
- `load_raw(tmp_path)` on an empty directory → returns `({}, [...])` where the second element is non-empty and no exception is raised.
- `capture_breadth()` → returns exactly 3 records with `methodology_id` values `{"VM0051", "VM0044", "AMS-II.G"}`, and every record's `gating_field` is a dotted path beginning `technology.`.

**Dependencies**
- PHASE-01 and PHASE-02 outputs under `reports/walkthrough/raw/`.
- Existing modules `pdd_agent.retrieval.search`, `pdd_agent.agent.section_orchestrator`,
  `pdd_agent.export.docx_export`, `pdd_agent.calc.dispatch`, `schemas.project_input`.

**Exit Criteria**
- [ ] `PYTHONPATH= uv run --no-sync python scripts/build_walkthrough_evidence.py` exits `0`.
- [ ] `PYTHONPATH= uv run --no-sync python -c "import json;d=json.load(open('reports/walkthrough/inegol-evidence.json'));print(d['schema_version'], len(d['repo_lane']['drafting']['noop']['sections']))"` prints `1.0 36`.
- [ ] The bundle is valid JSON and smaller than 3 MB.
- [ ] `PYTHONPATH= uv run --no-sync python -m pytest tests/test_walkthrough_evidence.py -q` passes.
- [ ] `PYTHONPATH= uv run --no-sync ruff check scripts/build_walkthrough_evidence.py tests/test_walkthrough_evidence.py` reports no findings.

**Phase Risks**
- **RISK-03-01:** The prompt builder is a private method on `SectionOrchestrator`. If its name or
  signature differs from what the capture expects, capture the prompt instead by running a single
  section with `pdd-agent draft --only-section 4.1 --provider noop` under a temporary run id and
  reading the prompt from the resulting run record; if the prompt is not persisted there, record
  the prompt's **component inventory** (which blocks were included and their character counts)
  rather than the assembled text, and mark `prompt.capture_mode` accordingly. Never fabricate a prompt.
- **RISK-03-02:** `check_export_gate` accepts a `DraftRun` or its serialized dict; passing the raw
  JSON is supported. If reconstruction of the calc result is needed, use
  `PddCalcResult.from_dict`. Do not pass `raw_result`, which is not JSON-serializable.
- **RISK-03-03:** Bundle size can balloon if full section texts are embedded for all 36
  subsections. Only the four focus subsections carry text (TASK-03-06); the other 32 carry
  counts only.

### PHASE-04 - Build the template and renderer

**Goal**
Produce the interactive page: a hand-authored HTML template with a placeholder for the embedded
evidence, and a render script that injects the bundle and writes the final file.

**Tasks**
- [x] TASK-04-01: Create `reports/walkthrough/template.html` as a complete standalone document
  with inline `<style>` and inline `<script>`, no external resources of any kind, and a single
  injection point: `<script type="application/json" id="evidence">__EVIDENCE_JSON__</script>`.
- [x] TASK-04-02: Implement the fourteen screens in the template's JavaScript, driven entirely by
  the bundle. Screen ids and titles, in order: `00` Orientation; `01` Corpus and retrieval index;
  `02` Project intake; `03` Methodology screening; `04` Quantification; `05` Per-section
  retrieval; `06` Prompt assembly; `07` Drafting the 36 subsections; `08` Judge and redraft;
  `09` Review and quality gates; `10` Export gate and document assembly; `11` Packaging and
  delivery; `12` Breadth across other methodologies; `13` Verdict and decision brief.
- [x] TASK-04-03: Implement the per-screen layout in this fixed order: title and one-line purpose;
  a collapsed `<details>` element labelled "Why a validation body cares" carrying the domain note;
  the **predict** panel (a textarea plus a "Lock in prediction" button and a "Skip" link); the
  **reveal** panel, hidden until a prediction is locked or skipped, containing two side-by-side
  lanes; the **reality check** band, always visible, never collapsible; the **judge** panel with
  the four labelled scales from `## Specification` S2 plus a note textarea; and a "Next step"
  button disabled until the judge panel is submitted or skipped.
- [x] TASK-04-04: Implement screen `04` to render the full equation chain from
  `## Specification` S1 using the bundle's calc component values, the seven-year schedule as a
  table, and the `calc_climate_zone_resolved` warning as a callout. State explicitly on this
  screen that the headline "net emission reductions per year" figure is the **year-one** value
  under a first-order decay model, not an average.
- [x] TASK-04-05: Implement screen `07` to render a 36-cell grid coloured by confidence, with each
  cell showing subsection id, confidence and issue count, and to render the four focus subsections
  in full below the grid, each shown for both the `noop` and `demo` lanes with the `demo` lane
  labelled "synthetic — not model output".
- [x] TASK-04-06: Implement `localStorage` persistence under the key `pdd-walkthrough-v1` with the
  shape given in Gotchas. Every read and every write must be wrapped in `try`/`catch`; on failure
  the page must continue in read-only mode and show a single non-blocking banner.
- [x] TASK-04-07: Implement export and import of reader state as JSON: an "Export my answers"
  button that triggers a `Blob` download, and an "Import answers" control that accepts pasted JSON.
  This is the durable path when `localStorage` is unavailable.
- [x] TASK-04-08: Implement screen `13` to compute the aggregation in `## Specification` S2 and
  render a Markdown decision brief into a `<textarea>`, with a copy button that selects the
  textarea and calls `document.execCommand("copy")` — `navigator.clipboard` is unavailable over
  `file://` in Chromium. The brief must contain: date, project, evidence-grade of each lane, a
  per-step table of the four scores and the note, the per-axis means, both overall means, the
  divergence list, and a "recommended follow-up experiments" section seeded with the two
  experiments named in Gotchas.
- [x] TASK-04-09: Implement responsive layout: the two lanes sit side by side above 900 px and
  stack below it; every table and code block scrolls inside its own `overflow-x: auto` container;
  the page body never scrolls horizontally.
- [x] TASK-04-10: Create `scripts/render_walkthrough.py` which reads the template and the bundle,
  replaces the single `__EVIDENCE_JSON__` token with the serialized bundle, and writes
  `reports/walkthrough/pdd-walkthrough.html`.
- [x] TASK-04-11: Add `tests/test_walkthrough_render.py` covering the renderer's pure functions.

**File Changes**
- `reports/walkthrough/template.html` (create): the full page with `__EVIDENCE_JSON__` token.
- `scripts/render_walkthrough.py` (create): the renderer.
- `reports/walkthrough/pdd-walkthrough.html` (create): generated output, committed.
- `tests/test_walkthrough_render.py` (create): renderer unit tests.

**Function Signatures**
- `escape_for_script(payload: str) -> str` — returns the JSON payload with every `</` sequence replaced by `<\/` so an embedded string can never terminate the host `<script>` element.
- `render(template_text: str, evidence: dict[str, Any]) -> str` — returns the template with the single `__EVIDENCE_JSON__` token replaced by the escaped, serialized evidence.
- `main() -> int` — reads `reports/walkthrough/template.html` and `reports/walkthrough/inegol-evidence.json`, writes `reports/walkthrough/pdd-walkthrough.html`, returns `0` on success and `1` when either input is missing or the token is absent.

**Test Specs**
- `escape_for_script('{"a": "</script>"}')` → `'{"a": "<\\/script>"}'`; the returned string contains no literal `</script>` substring.
- `escape_for_script('{"a": 1}')` → unchanged.
- `render("<x>__EVIDENCE_JSON__</x>", {"a": 1})` → `'<x>{"a": 1}</x>'`.
- `render("<x>no token here</x>", {"a": 1})` → raises `ValueError` whose message contains `__EVIDENCE_JSON__`.
- `render("<x>__EVIDENCE_JSON__</x>__EVIDENCE_JSON__", {"a": 1})` → raises `ValueError` mentioning that the token must appear exactly once.
- `render` with evidence containing the non-ASCII strings `"Türkiye"` and `"İnegöl"` → the output contains both verbatim; serialization must use `ensure_ascii=False` and the file must be written with `encoding="utf-8"`.
- Reading the generated `reports/walkthrough/pdd-walkthrough.html` and searching for `http://` or `https://` in `src=` or `href=` attributes → no matches, proving no external resource is referenced.

**Dependencies**
- PHASE-03's `reports/walkthrough/inegol-evidence.json`.

**Exit Criteria**
- [ ] `PYTHONPATH= uv run --no-sync python scripts/render_walkthrough.py` exits `0`.
- [ ] `reports/walkthrough/pdd-walkthrough.html` exists and is smaller than 5 MB.
- [ ] `PYTHONPATH= uv run --no-sync python -c "import re,pathlib;h=pathlib.Path('reports/walkthrough/pdd-walkthrough.html').read_text(encoding='utf-8');print(len(re.findall(r'(?:src|href)=\"https?://', h)))"` prints `0`.
- [ ] `PYTHONPATH= uv run --no-sync python -c "import pathlib;h=pathlib.Path('reports/walkthrough/pdd-walkthrough.html').read_text(encoding='utf-8');print('__EVIDENCE_JSON__' not in h, 'İnegöl' in h)"` prints `True True`.
- [ ] `PYTHONPATH= uv run --no-sync python -m pytest tests/test_walkthrough_render.py -q` passes.
- [ ] Opening the file in a browser shows screen `00`, and screen `04` shows the crediting-period total `893,441.43`.

**Phase Risks**
- **RISK-04-01:** An embedded JSON string containing `</script>` would terminate the script element
  and corrupt the page. Mitigation: `escape_for_script` is mandatory and is directly tested.
- **RISK-04-02:** Chromium treats `file://` as a non-secure context, so `navigator.clipboard` is
  unavailable and `localStorage` may be blocked depending on flags. Mitigation: TASK-04-06 wraps
  all storage access in `try`/`catch`; TASK-04-07 provides JSON export/import; TASK-04-08 uses
  `document.execCommand("copy")`.
- **RISK-04-03:** Gating can trap a reader on a step they cannot judge. Mitigation: every gate has
  a visible "Skip" control, and skipped steps are excluded from the aggregation divisor.

### PHASE-05 - Verify, document, and commit

**Goal**
Prove the whole artifact reproduces from a clean checkout plus the two capture phases, document how
to regenerate it, and land it in one commit.

**Tasks**
- [x] TASK-05-01: Create `reports/walkthrough/README.md` documenting: what the walkthrough is; the
  exact command sequence to re-capture and re-render; the meaning of the four scoring axes; the
  fact that both lanes ran without any model-backed provider; and which portable-workspace stage
  was executed versus documented only.
- [x] TASK-05-02: Delete `reports/walkthrough/pdd-walkthrough.html` and regenerate it with
  `scripts/render_walkthrough.py` to prove the renderer is the sole author of that file.
- [x] TASK-05-03: Run the full verification suite in `## Verification Strategy` and fix anything that fails.
- [x] TASK-05-04: Confirm the working tree contains no unintended additions:
  `git status --porcelain` must show only the files this plan creates, plus the pre-existing
  modification to `plans/2026-08-28-defensible-numbers-and-document-assembly-plan.md` and the
  pre-existing untracked `reports/2026-09-04-tinh-portable-workspace-test-report.html`, which are
  **not** part of this work and must not be staged by it.
- [x] TASK-05-05: Stage and commit only this plan's files, with a message beginning
  `feat(walkthrough): interactive Inegol PDD process walkthrough and track comparison`.

**File Changes**
- `reports/walkthrough/README.md` (create): regeneration instructions and reading guide.
- `reports/walkthrough/pdd-walkthrough.html` (modify): regenerated in place by the renderer.

**Function Signatures**
None — no code interfaces change in this phase.

**Test Specs**
None — no testable behavior changes in this phase.

**Dependencies**
- All prior phases complete.

**Exit Criteria**
- [ ] `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` reports at least `962 passed` and `2 xfailed`, with zero failures.
- [ ] `PYTHONPATH= uv run --no-sync ruff check .` reports no findings.
- [ ] `PYTHONPATH= uv run --no-sync ruff format --check .` reports no files would be reformatted.
- [ ] `PYTHONPATH= uv run --no-sync uv lock --check` succeeds, confirming no dependency changed.
- [ ] `git status --porcelain` after the commit shows only the two pre-existing unrelated entries named in TASK-05-04.
- [ ] `reports/walkthrough/` contains exactly: `README.md`, `template.html`, `pdd-walkthrough.html`, `inegol-evidence.json`, and `raw/` with its capture files.

**Phase Risks**
- **RISK-05-01:** Committing large binaries by accident. Mitigation: TASK-02-07 keeps merged PDFs
  and workbooks out of `reports/`; verify with
  `git diff --cached --stat` before committing and reject any single file above 3 MB.

## Gotchas

- **Evidence bundle schema.** `reports/walkthrough/inegol-evidence.json` must have exactly these
  top-level keys: `schema_version` (string `"1.0"`), `generated_at` (UTC ISO-8601 with `Z`),
  `project`, `environment`, `repo_lane`, `tinh_lane`, `reality_checks`, `breadth`, `missing_inputs`.
  `repo_lane` must have: `corpus_index`, `intake`, `screening`, `calc`, `retrieval`, `prompt`,
  `drafting` (with sub-keys `noop` and `demo`, each carrying `sections`, `focus`, `timing_seconds`,
  `provider`), `judge`, `review` (sub-keys `noop`, `demo`), `export_gate` (sub-keys `noop`, `demo`),
  `package`. `tinh_lane` must have: `evidence_grade` (`"measured"` or `"documented"`),
  `stages` (each with `name`, `status` of `executed` or `documented_only`, `notes`), `inputs`
  (the 3908 hash table), `outputs`, `timing_seconds`, `tools`, `process_excerpt`, `known_defects`.
- **Reader-state schema in `localStorage`.** Key `pdd-walkthrough-v1`, value
  `{"version": 1, "updated_at": "<ISO8601>", "steps": {"<stepId>": {"prediction": "<string>", "scores": {"human_minutes": <int|null>, "cost": <int|null>, "defensibility": <int|null>, "failure_mode": <int|null>}, "note": "<string>", "skipped": <bool>}}}`.
  Step ids are the two-character strings `"01"` through `"12"`; `"00"` and `"13"` are not scored.
- **Subsection sorting.** Subsection ids are dotted decimals like `1.1`, `1.13`, `4.1`, `4.10`.
  Sorting them as strings puts `1.13` before `1.2` and `4.10` before `4.2`. Always split on `.`
  and compare integer components, in both Python and JavaScript.
- **The headline ER number is year one, not an average.** Under first-order decay the baseline
  methane term grows every year: Inegol runs from 50,690.48 tCO2e in year 1 to 193,891.69 in
  year 7. Anyone comparing "annual net ER" against a registered document's "average annual" figure
  will appear to be off by a factor of roughly three and will chase a non-existent bug.
- **`--review-output-dir` is the wrong tool for packaging here.** In `_run_export`, that branch
  calls `publish_docx_run_for_review(run_id=..., project_name=args.run_id, ...)`, so the package
  folder is named after the run id rather than the project, and it re-exports via
  `export_run_to_docx(run_id=run_id)` with no `project_input` and no `force`, meaning a
  hard-blocked export raises out of that branch. Publish by calling `publish_review_package` /
  `publish_demo_package` directly.
- **Windows console encoding.** The `calc` text output contains an em-dash-arrow glyph that the
  cp1252 console renders as a replacement character, and `pdd-agent --help` raises
  `UnicodeEncodeError` outright. Set `PYTHONIOENCODING=utf-8` before capturing text output and
  prefer `--output` / `--json` forms.
- **`PddCalcResult.raw_result` is not JSON-serializable.** For ACM0022 it holds a Pydantic model.
  Always serialize via `to_dict()`, which deliberately omits it.
- **Non-ASCII project data is load-bearing.** The Inegol input contains `Türkiye`, `İnegöl`,
  `BIOTREND Çevre ve Enerji Yatırımları Anonim Şirketi`, and `Doğu Star Elektrik Üretim A.Ş.`
  Every file read and write in the new scripts must pass `encoding="utf-8"` explicitly, and every
  `json.dump` must pass `ensure_ascii=False`. The dotted capital `İ` is a real character, not a typo.
- **Inegol has no assumption register.** There is no `configs/demo/inegol_project_input.assumptions.yaml`.
  The assumption-gating review path (`ASSUMPTION-BLOCK-*` and `ASSUMPTION-WARN-*` flags) will be
  inactive. Present that path on screen `09` from `rules/verra/wte_review_rules.yaml`, labelled as
  "rule exists, not exercised by this project".
- **Five subsections can never be auto-approved** under the WTE rules: `3.4` Baseline scenario,
  `3.5` Additionality, `1.13` Prior conditions, `4.1` Baseline emissions, `4.4` Net emission
  reductions. Screen `09` must name all five, because they define the irreducible human workload.
- **The two follow-up experiments to seed into the decision brief.** First: a full 36-section run
  using the `claude-code` provider, which is subscription-billed and therefore priced at zero
  marginal cost in `llm/budget.py`, to close the "no model-backed run has ever completed" gap.
  Second: cross-validating this repository's ACM0022 calculator against the five already-reconciled
  registered projects held in the portable workspace (VCS 4818 twice, 5040, 4940, 4921). Neither is
  performed by this plan.
- **Do not compare prose quality.** One lane produces placeholders, the other produces
  hand-written synthetic prose, and neither is model output. Any screen that invites a prose-quality
  judgement is a defect.
- **The scoring weights are pre-committed and biased.** The deliverable weighting in
  `## Specification` S2 was chosen before any evidence was seen and favours the provenance-heavy
  track. The page must display that caution beside the weighted result, not bury it.

## Verification Strategy

- **TEST-001:** `PYTHONPATH= uv run --no-sync python -m pytest -m "not corpus" -q` → at least `962 passed, 2 xfailed, 7 deselected`, zero failures.
- **TEST-002:** `PYTHONPATH= uv run --no-sync python -m pytest tests/test_walkthrough_evidence.py tests/test_walkthrough_render.py -q` → all pass.
- **TEST-003:** `PYTHONPATH= uv run --no-sync ruff check .` → `All checks passed!`.
- **TEST-004:** `PYTHONPATH= uv run --no-sync ruff format --check .` → no files listed for reformatting.
- **TEST-005:** `PYTHONPATH= uv run --no-sync uv lock --check` → succeeds with no lockfile change.
- **TEST-006:** `PYTHONPATH= uv run --no-sync python -c "import json;d=json.load(open('reports/walkthrough/inegol-evidence.json'));assert d['schema_version']=='1.0';assert len(d['repo_lane']['drafting']['noop']['sections'])==36;assert len(d['repo_lane']['drafting']['demo']['sections'])==36;assert abs(d['repo_lane']['calc']['crediting_period_total_tco2e']-893441.43)<0.01;print('ok')"` → prints `ok`.
- **TEST-007:** `PYTHONPATH= uv run --no-sync python -c "import json;d=json.load(open('reports/walkthrough/inegol-evidence.json'));rc=d['reality_checks'];assert len(rc)>=6;assert any(r['severity']=='material' for r in rc);print('ok')"` → prints `ok`.
- **TEST-008:** `PYTHONPATH= uv run --no-sync python -c "import re,pathlib;h=pathlib.Path('reports/walkthrough/pdd-walkthrough.html').read_text(encoding='utf-8');assert not re.search(r'(?:src|href)=\"https?://',h);assert '__EVIDENCE_JSON__' not in h;assert 'İnegöl' in h;print('ok')"` → prints `ok`.
- **TEST-009:** `PYTHONPATH= uv run --no-sync python -c "import pathlib;p=pathlib.Path('reports/walkthrough/pdd-walkthrough.html');print(p.stat().st_size < 5_000_000)"` → prints `True`.
- **TEST-010:** Idempotence — run `PYTHONPATH= uv run --no-sync python scripts/render_walkthrough.py` twice, then `git diff --stat reports/walkthrough/pdd-walkthrough.html` → no output, proving the renderer is deterministic.
- **MANUAL-001:** Open `reports/walkthrough/pdd-walkthrough.html` from disk. Confirm screen `00` renders, the "Next step" button is disabled until a prediction is locked or skipped, and the reveal panel stays hidden until then.
- **MANUAL-002:** On screen `04`, confirm the equation chain lists all ten components with the values in `## Specification` S1, the seven-year table runs 50,690.48 to 193,891.69, and the derived-climate-zone warning is visible.
- **MANUAL-003:** On screen `07`, confirm 36 grid cells render, all `noop` cells show `UNSUPPORTED`, and the four focus subsections open with both lanes shown and the `demo` lane labelled synthetic.
- **MANUAL-004:** Score two steps, reload the page, and confirm the scores are restored. Then use "Export my answers", clear site data, use "Import answers" with the exported JSON, and confirm the scores return.
- **MANUAL-005:** On screen `13`, confirm the brief renders with per-axis means, both overall means, the bias caution beside the weighted figure, and that the copy button places the brief on the clipboard.
- **MANUAL-006:** Resize the browser below 900 px wide and confirm the two lanes stack and the page body does not scroll horizontally.
- **OBS-001:** Confirm every structlog call added in the new scripts uses an event-name string as its first argument, e.g. `logger.info("walkthrough_bundle_written", path=str(out), bytes=size)` — never an interpolated sentence. Check with `grep -n "logger\.\(info\|warning\|error\)(" scripts/build_walkthrough_evidence.py scripts/render_walkthrough.py`.

## Risks and Alternatives

- **RISK-001:** The walkthrough shows placeholder and synthetic prose on the repository lane while
  the other lane rests on a real registered document, inviting an unfair conclusion. Mitigation:
  the fairness rule is structural, not advisory — the reality-check band is non-collapsible on
  every screen, the `demo` lane is labelled synthetic wherever it appears, and prose-quality
  comparison is explicitly excluded from all four scoring axes.
- **RISK-002:** The pre-committed deliverable weighting favours one track. Mitigation: both the
  unweighted and weighted results are shown, side by side, with the caution attached.
- **RISK-003:** The evidence bundle drifts out of date as the pipeline changes, reproducing exactly
  the staleness that motivated this work. Mitigation: the page is generated, never hand-edited;
  `reports/walkthrough/README.md` carries the two regeneration commands; TEST-010 proves the
  renderer is deterministic so regeneration produces a clean diff.
- **RISK-004:** Poppler may be unobtainable, leaving the second lane unexecuted. Mitigation:
  RISK-02-04 defines the documented-only fallback with a mandatory on-page banner and an
  `evidence_grade` field, so the page cannot quietly present documentation as measurement.
- **RISK-005:** The portable workspace is git-ignored, so a future reader may not be able to
  reproduce the second lane at all. Mitigation: the bundle embeds the SHA-256 of every 3908 input
  file, the resolved tool versions, and the process excerpt, so the lane is auditable from the
  committed artifact even without the workspace.
- **ALT-001:** Run the full 36 sections through the `claude-code` provider so the comparison covers
  real model output. Not chosen: it is slow, non-deterministic, and would turn a process comparison
  into a capability demonstration. It is recorded as the top follow-up experiment instead.
- **ALT-002:** Publish the walkthrough as a hosted page with server-side persistence. Not chosen:
  a repository-local file keeps the page beside its evidence bundle under version control and
  defers any distribution decision.
- **ALT-003:** Have the page `fetch()` `inegol-evidence.json` at view time instead of embedding it.
  Not chosen: browsers block `fetch` of sibling files over `file://`, which would break the primary
  viewing mode.
- **ALT-004:** Extend `scripts/compare_codex_vs_pipeline.py` rather than adding new scripts. Not
  chosen: that script targets whichever run JSON is newest and encodes an older notion of the
  second track; retrofitting it would couple the walkthrough to stale assumptions. It is left untouched.

## Suggested Next Step

Execute PHASE-01 and PHASE-02 — they are independent and can run in either order or in parallel.
Verify each phase's exit criteria before starting PHASE-03, which consumes both phases' outputs.
