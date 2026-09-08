---
title: "Interactive PDD Process Walkthrough & Two-Track Practicality Comparison"
date: "2026-09-08"
type: "brainstorm"
depth: "standard"
source_request: "Design an interactive, step-by-step HTML walkthrough of the full PDD creation process (start to finish), with user input required at each step, so I can re-onboard after being out of touch and compare the repo pipeline vs the Tinh Ta Drive/Codex track on practicality."
slug: "pdd-process-walkthrough"
---

# Brainstorm: Interactive PDD Process Walkthrough & Two-Track Practicality Comparison

## Problem & Why Now

Tung has been out of direct contact with the `pdd-auto` pipeline because the work was
delegated to agents, and simultaneously out of contact with the parallel staff track
(Tinh Ta's Google Drive / Codex "portable workspace"). Both tracks have shipped
substantially since he last held the whole picture:

- The repo closed a 66-task plan (`plans/2026-08-28-defensible-numbers-and-document-assembly-plan.md`),
  reaching 960 passing tests, four wired calc engines, native Markdown/table/math DOCX
  rendering, a split export gate, and run survivability (pre-flight estimate, atomic
  checkpoint, `--resume`, `--workers`).
- Tinh's track went through **three generations** and explicitly retired generation 2
  (`INPUT -> YAML -> PREOUTPUT -> CODEX_FINISHED` was moved to `_archive/cleanup_20260827/`
  and marked "must not be used"). The current generation is a 672 MB portable Codex
  workspace with a source-preserving, hash-manifested packaging pipeline.

The consequence is that **nobody currently holds a first-hand, evidence-grounded view of
how a PDD actually gets made on either track**, which makes the near-term commercial
decision — what finished document can credibly be handed to a client — unmakeable.
Reading code or docs does not fix this; the gap is experiential, not informational.

There is also a live risk of judging the tracks on the wrong evidence. The repo's
prettiest artifacts are `demo`-provider synthetic prose, while Tinh's side has a real
139-page source PDD and a 560-page merged evidence package. A naive side-by-side would
compare a synthetic draft to a real document and reach a false conclusion.

## Current vs Desired State

- **Current state:**
  - The end-to-end process exists only as code plus scattered, partly stale docs.
    `activeContext.md` still describes the 2026-08-21 plan (two plans out of date);
    `lessons.md` is empty; `README.md:397` still calls `registry_download.py` a stub
    (false); `README.md` and `activeContext.md` disagree on test counts.
  - Repo pipeline: 25 CLI subcommands in `src/pdd_agent/cli.py`, a FastAPI service at
    `src/pdd_agent/service/main.py` with a `/dashboard`, four calc engines
    (`ACM0022`, `VM0051`, `VM0044`, `AMS-II.G`) in `src/pdd_agent/calc/`, BM25 retrieval
    over a SQLite FTS5 index, 36-section orchestration, rule-based review, DOCX export
    against the real Verra v4.4 template.
  - **No full real-model run has ever happened.** The only real-model artifact is
    `data/runs/smoke-4-1.json` — one section, `claude-code` provider, 47,523 tokens,
    $0.198, confidence LOW. Everything else is `noop` or `demo`.
  - Tinh track: `MIXED INPUTS -> ACTIVE CODEX TASK -> SOURCE-PRESERVING VERRA PDD PACKAGE`,
    staged locally at `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/`.
    The 2026-09-04 hands-on test verified 335/335 present files by hash, produced a
    560-page 9.07 MB merged PDF at a short path, and stalled on a missing Poppler
    (`pdftoppm`). No Codex session was ever launched here.
  - Comparison artifacts exist as prose (`docs/2026-06-15-tinh-track-vs-repo-comparison.md`,
    `docs/2026-08-28-tinh-track-vs-repo-comparison.md`,
    `reports/2026-09-04-tinh-portable-workspace-test-report.html`) but nothing walks the
    process interactively or forces a per-step judgment.

- **Desired state:**
  A single, self-contained, gated HTML walkthrough in the repo that takes Tung through
  **Inegol / VCS 3908** from zero to a finished package in ~14 screens. At each step he
  predicts, then sees the *real* artifact from both tracks, then scores both on four
  practicality axes. It ends by rendering a copyable decision brief that is saved back
  into `research/`. Every fact on the page comes from a captured evidence bundle produced
  by an actual run, so the page can be regenerated rather than left to rot.

- **Key repo surfaces:**
  - Entry/orchestration: `src/pdd_agent/cli.py` (`_build_parser:36`, dispatch `:458`),
    `src/pdd_agent/agent/section_orchestrator.py` (`run:1373`, `draft_all_sections:1251`,
    `_build_prompt:597`, `run_review:1396`)
  - Inputs: `schemas/project_input.py` (`ProjectInput:663`),
    `configs/demo/inegol_project_input.yaml`
  - Calc: `src/pdd_agent/calc/dispatch.py` (`compute_for:387`, `ENGINE_BY_METHODOLOGY:25`),
    `calc/acm0022.py:32`, `calc/incineration.py`, `calc/cdm_tool_04.py`, `calc/constants.py`
  - Retrieval: `src/pdd_agent/retrieval/index.py:96`, `retrieval/search.py:176`
  - Review: `review/checks.py:75`, `review/states.py:33`, `review/consistency.py:88`,
    `review/tbd_tracker.py:18`, `review/document_coherence.py:31`,
    `phase06/assumptions.py:240`, `rules/verra/wte_review_rules.yaml`
  - Export/package: `export/docx_export.py` (`check_export_gate:57`, `export_run_to_docx:169`),
    `export/markdown_docx.py`, `export/assembly.py`, `export/review_package.py:32` and `:126`,
    `export/pdf_export.py:36`
  - Providers/cost: `llm/provider.py:209`, `llm/budget.py:104`, `llm/judge_selection.py:74`
  - Tinh track: `data/runs/tinh-20260827/ws/PDD_Portable_Workspace_20260827/process/PDD_CREATION_PROCESS.md`,
    `scripts/run_pdd_in_place.py` (inside that workspace),
    `reports/2026-09-04-tinh-portable-workspace-test-report.html`
  - New surfaces to create: `reports/walkthrough/pdd-walkthrough.html`,
    `reports/walkthrough/inegol-evidence.json`, `scripts/build_walkthrough_evidence.py`

## Resolved Decisions

- **DEC-001:** The walkthrough's primary purpose is Tung's re-onboarding, ending in a
  defensible judgment on which track is more practical and where each is weak — not a
  teaching asset, not team documentation.
- **DEC-002:** Follow **one concrete real project end-to-end** with real inputs, real
  intermediate files, real numbers and a real output package at every step. No abstract
  stage descriptions.
- **DEC-003:** The subject project is **Inegol / VCS 3908** — the only project that exists
  on both sides (`configs/demo/inegol_project_input.yaml` plus `examples/example-inegol-demo.docx`
  plus a 7-year calc of 893,441.43 tCO2e on the repo side; the Aug-24 Verra pull for 3908 and
  the 560-page merged package on Tinh's side). Enables true apples-to-apples.
- **DEC-004:** Interaction model is **predict -> reveal -> judge**. Each step asks what Tung
  thinks happens / costs / breaks, then reveals the real artifact, then takes a scored
  verdict plus a note. Forces active recall; verdicts accumulate into the decision.
- **DEC-005:** Evidence comes from **a real Inegol execution performed before the page is
  built** — real calc, real review flags, real export-gate behaviour, real DOCX excerpts,
  real wall-clock timings. Not harvested-only, not hand-written from the code map.
- **DEC-006:** The output is a **decision brief written back to the repo**. Verdicts persist
  in the page across sittings, and a final step renders a copyable brief (per-step verdicts,
  notes, recommended track per step, joint experiments worth running) that is saved as a
  dated markdown in `research/`.
- **DEC-007:** For the Tinh lane, **install Poppler and complete the mechanical 3908
  packaging run** at a short path so timings, page counts and artifact sizes are *measured*.
  Only the Codex authoring stage stays doc-reviewed — and is labelled as such, loudly.
- **DEC-008:** Step spine is **~12 steps following the real pipeline**, with both tracks
  shown at every step (see Walkthrough Spine below). Not decision-grouped, not two
  separate lanes, not a 20-step deep dive.
- **DEC-009:** Every step scores both tracks on four axes: **human minutes, $ / token cost,
  defensibility to a VVB or Verra reviewer, and failure mode when it breaks.** Covers
  effort and trust — the two adoption drivers. Scalability and skill-dependency deliberately
  excluded to keep the per-step load at four.
- **DEC-010:** Credibility gaps get an **inline reality-check band on every step** plus one
  consolidated view. You cannot judge practicality if the demo hides where it is hollow.
- **DEC-011:** **No real-model run.** `demo` and `noop` providers only. The `claude-code`
  provider is subscription-billed at $0 marginal and could have closed the gap, but the run
  stays cheap, fast and deterministic; the reality-check band states plainly that all prose
  shown is synthetic or placeholder.
- **DEC-012:** Build an **evidence bundle plus a regenerable page**: every step's real
  artifacts captured into a versioned JSON in the repo, with the page rendering from it.
  Re-run later, re-capture, and the walkthrough stays true instead of rotting the way
  `activeContext.md` did.
- **DEC-013:** The final step is framed around **what to show a client in 8 weeks**, and
  specifically around **a finished document handed over** — one excellent Inegol package
  (DOCX plus evidence, gap analysis, assumption register), machine behind the curtain.
  Steps are therefore scored on their contribution to *that* deliverable, not on product-demo
  polish. Note this framing materially favours provenance and packaging over automation
  throughput, and the walkthrough should say so.
- **DEC-014:** Domain content lives in **expandable "why Verra cares" asides per step** —
  collapsed by default. Main flow stays machine-focused; the aside carries what additionality
  must prove, why the FOD decay model drives the whole baseline, why DC-01..DC-04
  double-counting guards exist, and what a VVB actually challenges.
- **DEC-015:** The calc step shows the **full equation chain with Inegol's real values**:
  `BE_CH4` (SWDS FOD) -> `BE_EC` -> `PE_EC` / `PE_FC` / `PE_COM_CO2` (Eq.22) /
  `PE_COM_CH4_N2O` (Eq.27) / `PE_WW` (Eq.28) -> `LE_RDF` / `LE_AD` -> net, plus the
  year-by-year `annual_schedule`. This is where the two tracks most sharply disagree, so it
  earns disproportionate depth.
- **DEC-016:** Cover **Inegol/ACM0022 throughout, with one breadth step near the end**
  showing exactly what changes for VM0051 rice, VM0044 biochar and AMS-II.G cookstoves —
  and what is absent for them: no corpus documents, no registered oracle, no review rules
  beyond the WTE set.
- **DEC-017:** Navigation is **gated but skippable** — the reveal is hidden until a
  prediction is logged and the next step until a verdict is logged, with a visible skip
  escape on every gate.
- **DEC-018:** The walkthrough is a **local HTML file in the repo** (`reports/walkthrough/`),
  committed to git, opened from disk, with verdicts persisted in that browser's
  `localStorage`. No published artifact, no hosting, no sharing decision to make yet.
- **DEC-019:** To keep the comparison fair, **lead with the `noop` run as the repo's honest
  state** — placeholders, `REVIEW REQUIRED` flags, the Required Inputs appendix — and show
  the `demo` output beside it explicitly labelled synthetic. Compare structure, gates and
  evidence handling; never compare prose quality, because one side has no real prose.
- **DEC-020:** The drafting step shows a **compact map of all 36 subsections** with their
  real state, confidence and flags from the run, then opens four in depth: **4.1 Baseline
  Emissions** (calc-injected), **3.5 Additionality** (never auto-approvable), **1.13 Prior
  Conditions** (assumption-blocked), and one clean low-stakes section for contrast.

## Walkthrough Spine

Fourteen screens. Steps 1-11 are the pipeline proper (DEC-008); 0, 12 and 13 frame it.

| # | Screen | Repo lane shows | Tinh lane shows |
|---|---|---|---|
| 0 | Orientation | What actually runs today; the two tracks in one diagram; how the gates work | Same diagram, other half |
| 1 | Corpus and index | `ingest -> normalize -> bucket -> build-index`; real index stats | 206-doc methodology library read directly, no index |
| 2 | Intake | `configs/demo/inegol_project_input.yaml`; required vs gating fields | Mixed evidence folder, unmodified, hashed at `00_INPUT` |
| 3 | Methodology screening | `domain/methodology_screen.py` ranked suggestions | Authority roles assigned per file |
| 4 | Quantification | Full ACM0022 equation chain, real Inegol values, annual schedule (DEC-015) | **Never recompute** — transfer reported values with worksheet/cell lineage |
| 5 | Retrieval | BM25 hits per section, `[CORPUS: ...]` provenance, family fallback | Model reads approved example PDDs directly; examples supply style only |
| 6 | Prompt assembly | Schema guidance + overlay + retrieval + calc block + facts + evidence registry + assumption register + length budget | Single in-place Codex task brief |
| 7 | Drafting x36 | 36-section map with real states/flags; 4 opened in depth (DEC-020) | One Codex pass writes all 36 template slots |
| 8 | Judge and redraft | Rubric scoring, capped 3 redrafts, `NEEDS_DOMAIN_REVIEW` parking | Human page-by-page inspection |
| 9 | Review / QA | 6 checks: rules (DC-01..04), consistency, evidence, assumption gating, TBD, coherence; 5-state machine | `audit_portable_pdd.py` / `check_portable_pdd.py`; release gates |
| 10 | Export gate and DOCX | Hard blocks vs Required Inputs appendix; DRAFT watermark; Verra v4.4 template | Reportlab traceability cover; `soffice` workbook-to-PDF; `pdftoppm` rasterize |
| 11 | Package and deliver | `reports/review-packages/` and `reports/demo-packages/` contents, manifest | Merged page-for-page PDF plus hashed run manifest |
| 12 | Breadth | VM0051 / VM0044 / AMS-II.G engines and what is missing for them (DEC-016) | Not implemented on that side either; VCS 4019 CarbonCure in neither |
| 13 | Verdict | Rendered decision brief scored against "a finished document handed over" (DEC-013) | — |

Per-step layout: title -> collapsed **why Verra cares** aside (DEC-014) -> **predict** gate ->
**reveal** (two lanes side by side) -> persistent **reality-check band** (DEC-010) -> **judge**
(4 axes x 2 tracks plus free note) -> next gate.

## Assumptions & Constraints

- **ASM-001:** `configs/demo/inegol_project_input.yaml` is complete enough to pass
  `ProjectInput` validation and to satisfy the ACM0022 calc gate
  (`quantification.grid_emission_factor` plus `grid_emission_factor_source` must both be
  present, or `compute_for()` returns `None` and there is no calc block at all).
- **ASM-002:** The Tinh workspace staged at `data/runs/tinh-20260827/ws/` is intact enough
  to complete the mechanical packaging run once Poppler is present; the 2026-09-04 report's
  partial PASS at `C:/t3908/job` is reproducible.
- **ASM-003:** Wall-clock timings measured on this machine are representative enough to
  score "human minutes" and "$ cost" honestly, given both runs are deterministic and local.
- **CON-001:** No API keys exist in this environment and none will be used
  (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` absent). Per DEC-011 the run is `demo`/`noop` only.
- **CON-002:** Tests must never require API keys, network access, or a running Ollama
  instance; all HTTP mocked (`CLAUDE.md`).
- **CON-003:** LibreOffice and `gws` must degrade gracefully and never become hard
  requirements. Poppler (DEC-007) is a *walkthrough-evidence* dependency on the Tinh lane
  only — it must not leak into the repo's own runtime requirements.
- **CON-004:** LibreOffice's `-env:UserInstallation` is path-length sensitive on this
  machine — identical calls fail silently (exit 1) at deep staging paths and succeed at
  `C:/t3908/job`. Any Tinh-lane execution must use a short staging root.
- **CON-005:** `reports/demo-packages/` run folders are committed to git;
  `reports/review-packages/` is the internal reviewer area where placeholder bodies and
  assumption-gated content are expected. New evidence must land in the right area.
- **CON-006:** The page is a single local HTML file with `localStorage` persistence
  (DEC-018) — no server, no build step required to open it, and no external CDN dependency
  that would break it offline.
- **CON-007:** Ruff, line length 100, structlog event-style logging, for any Python added
  (`scripts/build_walkthrough_evidence.py`).
- **CON-008:** `pdd-agent --help` currently raises `UnicodeEncodeError` on cp1252 due to an
  arrow glyph — any capture script driving the CLI must not depend on `--help` output and
  should set a UTF-8 capable encoding.

## Approaches Considered

- **Chosen:** A gated, predict-reveal-judge HTML walkthrough over **one project (Inegol)**,
  rendered from a **captured evidence bundle** produced by a real `demo`/`noop` run plus a
  completed Tinh mechanical run, scoring both tracks on four axes per step and ending in a
  decision brief. — It is the only shape that simultaneously re-onboards through active
  recall, grounds every claim in an artifact that actually exists, keeps the comparison
  honest about where each side is hollow, and survives future re-runs.
- **ALT-001:** *Two real projects side by side, each track running its own.* — Rejected:
  Inegol already exists on both sides, so a second project adds work without adding
  comparability.
- **ALT-002:** *Live working intake form driving a real pipeline run from the page.* —
  Rejected: teaches the data model rather than the process, and couples a documentation
  artifact to a running service.
- **ALT-003:** *Full 36-section `claude-code` real-model run to close the "never done a real
  run" gap.* — Rejected for this artifact (DEC-011): slow, non-deterministic, and it would
  make the walkthrough a proof-of-capability exercise rather than a process comparison. It
  remains the single highest-value follow-up experiment and should be named as such in the
  decision brief.
- **ALT-004:** *Published private Artifact with server-side verdict persistence.* —
  Rejected (DEC-018): a repo-local file keeps the walkthrough next to its evidence bundle
  and inside version control, and defers the "does Tinh see this" question.
- **ALT-005:** *Show the polished `demo` package as the repo's face.* — Rejected (DEC-019):
  it would compare synthetic prose against Tinh's real 139-page source PDD and invite a
  conclusion a real run could invert.
- **ALT-006:** *Decision-grouped 7-step spine.* — Rejected (DEC-008): sharper for deciding,
  but blurs the mechanics Tung specifically needs to rebuild.

## Out of Scope

- Any real-model (`openai` / `anthropic` / `claude-code`) drafting run.
- Launching or executing a Codex authoring session on the Tinh workspace.
- Fixing the repo defects the walkthrough surfaces: index reachability at 889 of 3,026 rows
  with ACM0022 itself unretrievable; the 2 oracle `xfail`s; the 3 unwired Verra table
  renderers (`risk_assessment`, `sustainable_development`, `data_gaps`); the uncalibrated
  LLM judge prompt; the stale `docs/vietnam-pdd-*.md`. The walkthrough *surfaces* these;
  repairing them is separate work.
- Refreshing the `activeContext.md` / `README.md` inconsistencies.
- Adding auth to the FastAPI service, or any service work.
- Cross-validating the repo calculator against Tinh's five reconciled registered projects
  (VCS 4818 x2, 5040, 4940, 4921) — this is the top joint experiment and should be
  *recommended* by the decision brief, not executed inside it.
- The VCS 4019 CarbonCure methodology area, which neither track implements.
- Sharing the walkthrough or the brief with Tinh.

## Open Questions

1. **Q-001:** Is the 3908 source PDD inside Tinh's Aug-27 workspace the same vintage as
   `configs/demo/inegol_project_input.yaml`, or has the registered document been revised
   since the repo's input was authored?
   - **Recommended default:** Treat them as potentially divergent. Capture both vintages'
     identifying metadata into the evidence bundle and show a provenance note on the intake
     step rather than asserting they match.
   - **Why this matters:** If the inputs differ, any number-level comparison at step 4 is
     comparing two different projects, and the calc-vs-transfer contrast loses its force.

2. **Q-002:** How should Poppler be installed — `winget`, `scoop`, or a manual binary drop —
   and is a permanent `PATH` change acceptable on this machine?
   - **Recommended default:** Install to a short fixed path and add it to `PATH` for the
     capture session only, recording the exact method in the evidence bundle so the run is
     reproducible without a permanent system change.
   - **Why this matters:** DEC-007 makes Poppler the gating dependency for the Tinh lane's
     measured evidence; how it is installed determines whether anyone else can reproduce it.

3. **Q-003:** Should the decision brief be written to `research/` automatically at the end of
   the session, or only after Tung has walked all 14 screens and reviewed it?
   - **Recommended default:** The page renders the brief for copy/download; a human step
     saves it to `research/YYYY-MM-DD-pdd-track-decision-brief.md`. No automatic write.
   - **Why this matters:** An auto-written brief with half-filled verdicts would become
     another stale document of exactly the kind this exercise exists to correct.

4. **Q-004:** Does "a finished document handed over" (DEC-013) mean the *repo's* Verra-template
   DOCX, or the Tinh-style merged source-preserving PDF package, as the thing a client
   receives?
   - **Recommended default:** Leave it genuinely open and let the verdict screen force the
     choice from the accumulated per-step scores — that is the exercise's payload.
   - **Why this matters:** Pre-deciding it would prejudge the comparison the walkthrough is
     built to run.

## Suggested Next Step

Run `/plan pdd-process-walkthrough` to turn this into a multi-phase implementation plan.
