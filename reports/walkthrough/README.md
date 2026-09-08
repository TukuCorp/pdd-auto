# Inegol PDD Walkthrough

Interactive, step-by-step HTML walkthrough of the full Verra VCS Project Design
Document process for **Inegol Integrated Solid Waste Storage and Disposal
Facility (VCS 3908)**, comparing this repository's pipeline against the portable
Codex workspace track on practicality. Plan:
`plans/2026-09-08-pdd-process-walkthrough-plan.md`.

## Files

- `pdd-walkthrough.html` — the page. Open from disk (`file://`); no server, no
  external resources. Generated, never hand-edited.
- `template.html` — hand-authored page with one `__EVIDENCE_JSON__` token.
- `inegol-evidence.json` — machine-generated evidence bundle (schema `1.0`) the
  page renders from. Every fact on the page comes from here.
- `raw/` — PHASE-01/02 captures: repo-lane runs (`noop` + `demo`), corpus index
  health, calc output, and portable-workspace packaging evidence.
- `phase-0N-report.html` — per-phase completion reports (not part of the plan's
  minimal file list; kept by the convention phases 01–02 established).

## Regenerate

```bash
# 1. Re-capture the evidence bundle (needs data/runs/ run JSONs + raw/ captures)
PYTHONPATH= uv run --no-sync python scripts/build_walkthrough_evidence.py

# 2. Re-render the page (sole author of pdd-walkthrough.html)
PYTHONPATH= uv run --no-sync python scripts/render_walkthrough.py
```

Re-rendering is deterministic: same inputs produce byte-identical output.

## The four scoring axes

Each judgeable step (01–12) scores both tracks on one relative scale
(−2 repo clearly better … +2 workspace clearly better):

1. `human_minutes` — which track needs less skilled human time at this step?
2. `cost` — which track costs less in money or tokens at this step?
3. `defensibility` — which track's output is easier to defend to a validation body?
4. `failure_mode` — when this step goes wrong, which track fails more safely and visibly?

Step 13 aggregates per-axis means, an unweighted overall mean, and a
deliverable-weighted mean (defensibility 0.4 / human_minutes 0.3 / failure_mode
0.2 / cost 0.1 — pre-chosen, structurally favours the provenance-heavy track).

## Honest-state notes

- Both lanes ran **without any model-backed provider** (`noop` + `demo` only).
  The `noop` lane shows placeholders; the `demo` lane shows hand-written
  synthetic prose explicitly labelled as such. Prose quality is never compared.
- Portable-workspace stages: **executed** — 00_INPUT manifest, mechanical
  packaging (560-page merged PDF, 224s). **Documented only** — the Codex
  authoring stage (36-slot prose, citations, attestations) and calculation
  transfer, both read from `PDD_CREATION_PROCESS.md`, never run here.
