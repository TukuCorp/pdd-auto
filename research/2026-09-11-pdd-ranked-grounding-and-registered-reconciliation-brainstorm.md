---
title: "Ranked Grounding and Registered Reconciliation: what pdd-auto needs after the walkthrough"
date: "2026-09-11"
author: "unattended analysis session"
inputs:
  - "plans/2026-08-28-defensible-numbers-and-document-assembly-plan.md (status: complete)"
  - "plans/2026-09-08-pdd-process-walkthrough-plan.md (status: complete)"
  - "research/2026-08-27-pdd-assembly-and-defensible-numbers-brainstorm.md"
  - "reports/bench/two-lane-bench.html, reports/2026-09-04-tinh-portable-workspace-test-report.html"
  - "reports/walkthrough/inegol-evidence.json and raw/ captures"
  - "live repository state at d968f75; registered Inegol ER workbook staged under data/runs/tinh-20260827/"
---

# Brainstorm: Ranked Grounding and Registered Reconciliation

## How this session differs from the last one

The 2026-08-27 brief found two things: the numbers were one parameter correction away from
defensible, and nobody owned the assembled document. The 2026-08-28 plan shipped both, all 66
tasks. The walkthrough and two-lane bench followed. The suite reproduces today at **974 passed,
7 deselected, 2 xfailed, 0 failed** (195 s, run this session).

This session did not re-audit those pushes. It looked at the two layers the last brief deferred:
**grounding** (Tracks C/D) and **the Inegol oracle**, the last two xfails. It checked every claim
below against code or a measurement taken this session, offline, with no money spent and no
source file changed.

The headline:

> **The retrieval layer does not rank. Every section is grounded on the first five documents in
> alphabetical order, including the project's own registered PDD. The ACM0022 methodology, "fixed"
> in the last push, is still absent from the index, for a different reason than the one fixed.
> Meanwhile the Inegol oracle's residual is mostly one climate-zone bit. The registered workbook
> that proves it has been sitting on this machine since Aug 27.**

---

## Finding 1 (headline): "retrieval" is an alphabetical sort

`retrieval/search.py:176`, `get_examples_for_section()`, is the entry point the orchestrator uses
for precedent. Its own docstring calls it "non-ranked". It hard-codes `score=0.0` and
`matched_terms=[]` on every result. Underneath, `retrieval/index.py:337` does:

```sql
ROW_NUMBER() OVER (PARTITION BY document_name ORDER BY chunk_index) AS doc_rank
...
ORDER BY doc_rank, document_name
LIMIT ?
```

So the top-k for any section is "the first chunk of each document that has a row for this
section, in alphabetical order of document name". No query terms, no BM25, no project similarity.
Neither the project's technology type nor its country or methodology plays any part beyond the
coarse `document_family` filter.

Measured in the captured Inegol evidence bundle
(`reports/walkthrough/inegol-evidence.json`):

```
retrieval hits (4 focus sections)      drafting [CORPUS: ...] citations
  VCS_Bergama           4                VCS_Bergama           12
  VCS_DRAFT_Yanjiang    4                VCS_DRAFT_Yanjiang    12
  VCS_Guangzhou         4                VCS_Guangzhou         12
  VCS_Guanxi_Zhuang     4                VCS_Guanxi_Zhuang     12
  VCS_Inegol            4                VCS_Inegol            12
```

These are exactly the first five of the 13 indexed documents, alphabetically, in perfect
uniformity. Three consequences, each worse than the last:

1. **The answer key is in the prompt.** Inegol is drafted with Inegol's own registered PDD as one
   of five precedents. The 2026-08-27 brief found the same thing for Soc Son (Finding 5) and
   diagnosed it as a missing `exclude_documents=` parameter. It is a symptom. Soc Son was only
   *less* contaminated because "S" sorts late.
2. **Damaged text is preferred.** Two of the five alphabetical winners are the most corrupted
   documents in the corpus: `VCS_DRAFT_Yanjiang` carries 1,629 U+FFFD characters; the whole
   corpus carries 8,046 (recounted this session). They win because "D" and "G" sort early.
3. **Relevance never enters.** Inegol is `combined_wte_ad` (anaerobic digestion + RDF + landfill),
   in Türkiye. Its precedents are chosen by the first letter of their filenames, not by being
   AD projects, Turkish projects, or projects with the same boundary.

Every grounding metric the repo reports (provenance counts, "grounded" confidence, the judge's
citation check) measures whether *something* was cited, never whether the right thing was.
The 889/891 "reachable rows" figure is true and beside the point: rows are reachable, but
retrieval never reaches for them.

**What good looks like:** rank candidates by project similarity. Start with deterministic features
(family, `technology_type`, country/region, methodology ids, and BM25 of project facts against the
chunk). Diversify across documents, exclude the project's own registered PDD by default when its
VCS id is known (Inegol declares 3908), and populate `score`/`matched_terms` honestly so the
provenance appendix can show *why* a precedent was chosen.

---

## Finding 2: the methodology is still not in the index, for a new reason

The 2026-08-28 PHASE-01 added a `text/plain` extraction branch. The four pre-extracted documents
now normalize properly: `EB111_repan07_ACM0022_v03.0` went from 1 text block to **308**. The
index was rebuilt 26 seconds after they were re-normalized (`corpus.fts.db` 04:18:17 vs
`.norm.json` 04:17:52, Aug 28). They are still absent. `index-report` lists 13 documents, not 17,
and all four under `missing_documents`.

Root cause, reproduced this session with `parse_document()`:

| document | headings | blocks | `section_spans` | mapped headings with text |
|---|---|---|---|---|
| EB111 (ACM0022) | 307 | 308 | **0** | 0 of 106 |
| DraftProjectDescription | — | 184 | **0** | 0 of 82 |
| Bergama monitoring v4.2 | — | 115 | **0** | 0 of 82 |
| HEREKO v4.1 | — | 104 | **0** | 0 of 71 |

The chain:

1. A text/plain record has **one "page"** holding the whole document (EB111: `pages=1`,
   172,737 chars), and **no heading carries a `page` key**.
2. Blocks and headings now *align*, so `parse_document` takes the strict branch, not the fallback
   written for these four documents (`section_parser.py:241-307`). That fallback's comment still
   describes the pre-08-28 shape ("1 text_block vs 50 headings").
3. The strict branch skips a heading when `_is_toc_page(page_texts[h.get("page", 1)])`. Every
   heading defaults to page 1, and page 1 is the whole document, which contains "CONTENTS".
   **Every heading is skipped as a table-of-contents entry.**
4. `_find_content_page()` hits the same trap, so every `sections_mapped` entry gets an empty
   `text_preview`. The indexer's second branch `continue`s on empty text, the document contributes
   zero rows, and **nothing logs a warning**. `skipping_doc` only fires on parse errors.

There is a second, smaller defect underneath. The text/plain heading pass picked up the TOC lines
themselves as headings (`'1. INTRODUCTION ........ 4'`), so even when fixed, spans would be keyed
on dotted-leader strings unless the heading pass strips them.

Fixing this is small (no page means no TOC-page test; strip dotted leaders; warn when an indexed
document yields zero rows). Its value is large: it gives the pipeline its first normative
grounding source. The orchestrator still never calls `search()` (the only ranked entry point), so
the fix only pays off alongside Finding 1's ranking work and a normative channel.

---

## Finding 3: the Inegol oracle residual is mostly a climate-zone bit

Two strict xfails remain, both Inegol (`tests/test_registered_pdd_oracle.py:159`). Their reason
says closing the gap "needs site-specific project-emission and composition inputs the Inegol
config lacks". That is partly wrong, and the correction is cheap.

`calc/constants.py:169`, `climate_zone_for()`:

```python
if abs(latitude) <= 23.5:
    return "tropical_wet"
return "boreal_temperate_wet"
```

The resolver **can never return a dry zone**. The IPCC wet/dry split depends on precipitation vs
potential evapotranspiration, not latitude, so latitude alone cannot decide it. The 08-28 plan's
ALT-003 argued latitude "resolves correctly for both oracle projects". That held for Soc Son. It
does not hold for Inegol.

The evidence: the registered Inegol ER workbook, `ER Calculation.v04_21.07.2025.xlsx`, sheet
*Waste Parameters*, staged in the Tinh workspace:

```
                      DOCj   kj        engine boreal_temperate_dry   engine boreal_temperate_wet
Wood                   43    0.02      0.02                          0.03
Paper/cardboard        40    0.04      0.04                          0.06
Food                   15    0.06      0.06                          0.185
Textiles               24    0.04      0.04                          0.06
Garden                 20    0.05      0.05                          0.10
```

The registered calculation uses **exactly** the engine's own `boreal_temperate_dry` column. The
engine derives `boreal_temperate_wet` (the phase-01 walkthrough capture records
`calc_climate_zone_resolved: zone=boreal_temperate_wet derived=True`), so it triples the food
decay rate.

Measured this session with `compute_for()`, overriding in memory only:

| Inegol configuration | year-1 net | 7-yr total | vs registered 730,000 |
|---|---|---|---|
| as committed (derived `boreal_temperate_wet`) | 50,690 | 893,441 | **+22.4%** (xfail) |
| `climate_zone: boreal_temperate_dry` | 36,684 | 594,306 | **−18.6%** (inside 0.20) |
| dry + registered 59,455.872 MWh/yr | 41,835 | 630,360 | **−13.6%** |

Declaring one sourced field flips the crediting-total test from outside to inside tolerance.
Because the xfail is `strict=True`, doing that turns the suite red until the xfail is removed.
That is the intended signal.

**This is sourced, not fitted.** The last brief warned against pasting parameters that make tests
pass. This case is different: the value comes from the registered project's own calculation
workbook, the exact kind of source the repo's provenance policy asks for. The remaining −13.6% is
structural and visible in the same workbook:

- **Waste is not constant.** *Waste Projection* grows from 214,255 t (2020) to 547,500 t (2026).
  The config holds one scalar, `annual_waste_throughput: 262970.37`.
- **The baseline is back-loaded.** Registered ERs run 4,358 → 35,163 → 62,889 → … → 232,574 over
  2021-2027, because the FOD pile starts empty in 2020. The engine's year-1 is already 50,690.
- **Project emissions grow** from 5,809 to 14,739 tCO2e/yr (*Project Emissions*, dominated by
  `PE_CH4` from anaerobic digestion). The engine holds 8,645 constant.
- **Electricity is 59,455.872 MWh/yr** from 2023 in the workbook vs `49,935.315` in the config.

---

## Finding 4: the second year-by-year oracle is a spreadsheet already on disk

Soc Son has a year-by-year oracle because someone typed Table 9 into test constants. Inegol can
have a better one, read mechanically: the registered workbook's *SUMMARY (ER)* sheet holds the
full schedule.

```
year   BE (tCO2e)  PE      ER
2021   10,167      5,809   4,358
2022   43,251      8,088   35,163
2023   72,738      9,849   62,889
2024  102,035     11,316   90,719
2025  140,719     12,294   128,425
2026  189,144     13,272   175,872
2027  247,313     14,739   232,574
TOTAL 805,367     75,367   730,000   (AVERAGE 104,285, matching INEGOL_ANNUAL_ERS)
```

`openpyxl` is already a core dependency, and `phase06/spreadsheet_mapper.py` already maps a
Vietnam workbook into `ProjectInput`. An Inegol ER-workbook mapper is the same shape of work. It
reads composition by treatment path, k/DOC by waste type, waste projection by year, electricity
and project emissions. It yields a `ProjectInput` delta plus a year-by-year oracle, each value
carrying sheet/cell lineage.

This is also **the joint experiment both recent cross-track reports recommended and nobody ran**.
The 09-04 Tinh report: "run the repo's calculator against Tinh's bundled inputs and diff. That
cross-check is the highest-value joint experiment available". The two-lane bench: "the useful
question … is whether Lane A's arithmetic agrees with the document Lane B is preserving." The
inputs are a 2.6 MB file in a git-ignored folder.

---

## Finding 5: a duplicate YAML key silently overrides a documented assumption

`configs/demo/inegol_project_input.yaml` sets `technology.biomethanization_suitable_fraction`
twice: once to `0.35` at line ~69, with a two-line comment explaining the assumption, and again
to `0.45` at line ~93, with no comment. PyYAML keeps the last value without complaint, so the
documented assumption is dead and an undocumented one is live. Measured: switching to the
commented `0.35` moves the 7-year total from +22.4% to +24.2%.

A duplicate-key check across the other three project configs found none. The fix is a
duplicate-rejecting loader wherever `ProjectInput` YAML is read. That is one small class, and it
turns this class of silent error into a load failure.

---

## Finding 6: carried forward, still open

Re-verified this session; unchanged since the 08-27 brief unless noted.

- **Citations are still unresolved.** All four real providers still score confidence by substring
  (`"[CORPUS:" in text`, e.g. `openai_provider.py:215`), and the judge's citation check is still a
  substring test (`review/judge.py:309`). A fabricated document name scores HIGH. With Finding 1
  fixed, a resolver can also check that a cited document was *in the retrieved set*, a far
  stronger test than "exists in the corpus".
- **No normative channel.** The orchestrator never calls `search()`.
- **The prompt header misnumbers every subsection.** `section_orchestrator.py:616` formats
  `f"({section_id}.{sub_section_id})"`, but `sub_section_id` is already `"4.1"`, so the model is
  told it is writing **"4.4.1"**. This is very likely the origin of the `4.4.1` heading the 08-27
  brief found in the real `smoke-4-1` output (its Finding 6). The assembly pass now strips the
  echoed heading, but the model is still primed with the wrong number, and the number can leak
  into prose cross-references.
- **A blocked export exits 0** (walkthrough finding F-2): `_run_export` prints
  `Export blocked: …` and bare-`return`s (`cli.py:919`). Automation cannot detect the block
  without parsing text.
- **`pdd-agent --help` still crashes on Windows.** Reproduced today: `UnicodeEncodeError`
  `'→'` at position 1034, rc=1. Windows is the primary development and demo machine.
- **Tests still write into the production run store.** This session's suite run added **57** run
  JSONs to `data/runs/` (now 2,162 files). No retention policy.
- **29 `Path(__file__).parent.parent.parent…` asset lookups** remain in `src/`, and the wheel
  still packages only `src/pdd_agent` + `schemas`. Nothing works outside the checkout.
- **No `run_id` validation** in the service before formatting into `data/runs/{run_id}.json`.
- **No prompt caching.** Zero `cache_control` in `src/`, and the section-specific header is still
  first in the prompt.
- **Corpus encoding damage** (8,046 U+FFFD) and the mojibake stem `VCS_Ã_demis`, which now also
  appears as a document name in the index and therefore in `[CORPUS: …]` provenance.
- **README drift.** It says live runs are "pending API keys" (the keyless `claude-code` provider
  has run), that `registry_download.py` "is a stub" (it is a real best-effort implementation with
  a manual-download fallback), and that `cli.py` has "6 commands" (it has 25).

---

## Finding 7: survivability is done, so the real run is now gated only on grounding

The 08-28 PHASE-06 delivered what the last brief's Track E asked for: `--estimate-only`,
`--max-cost-usd`, `--workers`, `--resume`, `--force-budget`, per-section `checkpoint()`, and
`estimate_run()`. The mechanical blockers to a real 36-section run are gone. What is left is an
API key or explicit authorization for `claude-code` spend.

The open question is therefore **what the money would buy**. Run today, a real model would get
five alphabetical precedents per section, including Inegol's own PDD, and no methodology text.
The output would look grounded, score HIGH on substring confidence, and teach nothing about
whether the pipeline works. Five months in, no model-written 36-section document exists. The
first one should be run against grounding that means something, with the project's own PDD
excluded so it can serve as the grading key.

---

## Finding 8: structural drift in the orchestrator

`agent/section_orchestrator.py` is now **1,528 lines**, up from 1,192 → 1,280 → 1,528 across the
last three pushes, none of which was about it. It owns prompt assembly, grounding, calc injection,
fact substitution, the judge/redraft loop, budgeting, concurrency, checkpointing and review.
`cli.py` (1,188), `export/docx_export.py` (1,197) and `service/main.py` (937) follow. Two packages
are named after plan phases (`phase05/`, `phase06/`), not after what they do.

This is not yet a problem, because tests cover the behaviour. It will become one when ranking
(Finding 1), a normative channel and a citation resolver all land in the same file. The natural
seam is a `grounding/` module: retrieval selection, exclusion, the normative channel and citation
resolution behind one interface the orchestrator calls once per section. Finding 1 forces that
seam anyway.

---

## Finding 9: the product the bench points at

The two-lane bench reached a conclusion the repo has not acted on. The lanes do different jobs:
Lane A authors a new PDD, Lane B preserves an existing one. For a registered project migrating
templates (Inegol), Lane B fits the job and Lane A's value is as a **checker**. Lane B "has no
content check at all and would package a wrong number silently". Lane A blocked its own export
over an arithmetic contradiction.

Findings 3 and 4 make that concrete. A `reconcile` mode would:

1. read a registered PDD's calculation workbook (and later its extracted tables),
2. recompute with the engine,
3. emit a per-year, per-component diff with sheet/cell lineage, flagging every disagreement
   above tolerance.

That needs no LLM and no API key, and it is testable offline against two real projects today. It
is also the convergence point with Tinh's track: his workspace packages the evidence, and the
repo checks the arithmetic inside it. It is the first thing the repo could hand a VVB-facing
reviewer that neither track currently offers.

---

## Proposed tracks

### Track A: grounding that means something (F1, F2, F6 partial). **Build first.**

1. **Parser fix.** A heading without a page never triggers the TOC-page test. Strip dotted
   leaders and trailing page numbers from text/plain headings. The indexer logs
   `document_zero_rows` for every parsed document that contributes nothing. Rebuild, then assert
   17/17 documents are reachable and EB111 has > 0 rows.
2. **Ranked selection.** Replace the alphabetical `ORDER BY` with a scored ranking: a family
   match, then `technology_type` / methodology / country similarity from `ProjectInput`, then BM25
   of project facts against the chunk. Keep per-document diversity. Populate `score` and
   `matched_terms`. Add a penalty or exclusion for chunks with a high U+FFFD ratio.
3. **Self-exclusion.** `exclude_documents=` threaded through selection; default-exclude the
   project's own registered PDD when `project.vcs_id` (or equivalent) matches a corpus document.
   Record the exclusion in provenance.
4. **Normative channel.** Methodology chunks (`document_family` = methodology, `section_id=""`)
   are retrieved by `search()` and injected under their own heading, distinct from precedent.
5. **Fix the prompt header** numbering (`section_orchestrator.py:616`).

**Why first:** it decides what every future run (real or demo) reads. It is offline, and it is
the precondition for the real run being informative. **Effort:** medium. **Risk:** changes
retrieval for every run, so outputs are not byte-comparable with earlier runs (accept, as
08-28 RISK-003 did).

### Track B: reconcile Inegol against its registered workbook (F3, F4, F5)

1. **Climate zone.** `climate_zone_for()` stops guessing wet/dry outside the tropics. It returns
   the derived zone with an explicit `ambiguous` warning, and the Inegol config declares
   `location.climate_zone: boreal_temperate_dry`, sourced to *Waste Parameters* in the registered
   workbook.
2. **Workbook mapper.** Following `spreadsheet_mapper`'s pattern, map composition by treatment
   path, k/DOC, the per-year waste projection, electricity and PE into `ProjectInput` with
   cell lineage. Add a per-year throughput input (or reuse `capacity_ramp`) so a growing deposit
   is modelled.
3. **Year-by-year oracle.** Add `TestInegolAnnualSchedule` read from *SUMMARY (ER)* (committed as
   constants with the workbook path and sheet in comments, because the workbook itself is
   git-ignored). Remove the strict xfails only when the tests genuinely pass. Record every
   residual as a dated measurement. `TOLERANCE` stays 0.20.
4. **Duplicate-key-rejecting YAML loader** for project inputs. Resolve Inegol's `0.35` vs `0.45`
   to one sourced value.

**Why:** "the engine reproduces two registered PDDs year by year, from their own sourced
parameters" is a stronger claim than anything the repo can make now, and the evidence is on
disk. **Effort:** medium. **Dependencies:** none. **Risk:** the growing-deposit model may expose
further structural gaps (the AD pathway, `PE_CH4`). That is a finding, not a failure.

### Track C: `pdd-agent reconcile` (F9)

A CLI/service mode that takes a `ProjectInput` plus a registered calculation workbook (Inegol) or
extracted PDD tables (Soc Son), recomputes, and writes a per-year, per-component diff report plus
a DOCX appendix. It reuses Track B's mapper and the existing export appendix machinery.

**Why:** it is the checker role the bench identified, the convergence point with the portable
workspace, and a deliverable that needs no model. **Effort:** small-medium once Track B exists.
**Dependencies:** Track B.

### Track D: the real run, as an experiment with a grading key (F7)

After Track A, draft Inegol section **4.1** (then 3.5, 1.13, 1.1: the walkthrough's focus
sections) with a real model under `--max-cost-usd 5`. Inegol's own PDD is excluded from
retrieval, and each section is scored against the registered PDD's corresponding section
(required-element coverage, number agreement with the calc result, citation resolution rate).
Only then the full 36 sections. This is the bench's Q5 "run that would settle it", executed
against grounding worth grading.

**Effort:** small. **Dependencies:** Track A (mandatory) and Track B (preferred, so the numbers in
4.1 are the reconciled ones). **Gate:** a key and explicit human authorization. No spend in
unattended mode.

### Track E: hygiene batch (F6 remainder)

UTF-8-safe CLI help (reconfigure stdout, or ASCII in help strings), a non-zero exit on a blocked
export, a `tmp_path` runs-dir fixture so tests stop writing to `data/runs`, a run-store retention
command, `run_id` validation (`^[A-Za-z0-9_.-]{1,80}$`), a single repo-root/asset resolver
replacing the 29 parent-chains, and a README resync. Prompt-cache reordering (static content
first, `cache_control` on the Anthropic provider) fits here because it becomes worth money the
moment Track D runs.

**Effort:** small, parallelizable. It should not gate Tracks A-B.

### Track F: carve out `grounding/` (F8)

Move selection, exclusion, the normative channel and citation resolution out of the orchestrator
behind one `ground_section(project, section) -> Grounding` interface, as part of Track A rather
than as a separate refactor. Rename `phase05/` → `benchmark/` and `phase06/` → `intake/`
opportunistically.

---

## What I would do next, if it were my call

**Track A + Track B as one push, with Track E's exit-code, `--help` and test-isolation items as
the opening phase.**

Track A because every downstream claim (grounding scores, judge verdicts, the value of a real run)
currently rests on an alphabetical sort. Track B because the evidence is already measured: one
sourced field moves Inegol from +22.4% to −18.6%, and the workbook that sources it holds a full
year-by-year oracle. The three hygiene items go first because they are an hour's work, and the
test-isolation fix stops every later phase from polluting the run store it measures.

Track C follows immediately; it is small once B lands. Track D follows A. The repo's first real
model document should be graded against a key it was not allowed to read.

The trap this time is **declaring grounding fixed because rows are reachable**. The last two
pushes improved reachability (889 → 891 rows, text/plain normalization) while the selection
query ignored all of it. The acceptance test for Track A is not "EB111 has rows". It is: for
Inegol section 4.1, the retrieved set contains the ACM0022 methodology, does not contain
`VCS_Inegol`, and is ordered by a score that is not zero.

---

## Assumptions adopted where I would otherwise have asked

Per the unattended-session rule, these were decided rather than raised:

- **ASM-A:** Deterministic similarity ranking (features + BM25) comes before any embedding or LLM
  reranker. The repo's house style is offline and testable, and it has no embedding dependency.
- **ASM-B:** Self-exclusion defaults **on** when the project's registered id matches a corpus
  document. This reverses the 08-27 brief's ASM-E ("default off"). Justification: that brief
  assumed contamination was occasional; this session found it structural (Inegol is always in its
  own top five). Comparability with earlier runs is already broken by the ranking change.
- **ASM-C:** The Inegol climate zone is **declared** in config, sourced to the registered workbook.
  No climate dataset is bundled (keeping 08-28 ALT-003's rejection), but the resolver stops
  pretending latitude decides wet vs dry.
- **ASM-D:** Registered-workbook values are committed as test constants with sheet/cell lineage
  comments. The workbook stays git-ignored (it is 2.6 MB, client-adjacent, and lives in the Tinh
  staging folder). A test that needs the file is `corpus`-marked and skipped when it is absent.
- **ASM-E:** `TOLERANCE` stays 0.20. The strict Inegol xfails are removed only when the tests
  genuinely pass, never by widening tolerance.
- **ASM-F:** For the duplicate `biomethanization_suitable_fraction`, neither value is picked here.
  The plan must source it from the workbook's *Waste Projection* composition (the biomethanization
  column) or record it as an explicit assumption.
- **ASM-G:** No money is spent. Track D stays gated on explicit authorization, and every
  measurement above was taken offline.
- **ASM-H:** The committed `reports/demo-packages/` artifacts are not regenerated as a ride-along,
  even though Track A changes what they would contain (same call as the last three briefs).

---

## Considered and rejected

- **Run the full 36-section real model now, since survivability shipped.** Rejected. It would
  spend money grounding on alphabetical precedent that includes the answer key, and produce a
  document that cannot be graded (Finding 7).
- **Set Inegol to `boreal_temperate_dry` and flip the xfail as a one-liner.** Rejected as the
  *whole* fix. It is a legitimate sourced change and belongs in Track B, but alone it leaves the
  −13.6% structural residual unexplained and the year-by-year shape wrong (back-loaded registered
  vs front-loaded engine). Land it with the year-by-year oracle so the shape is measured, not
  just the total.
- **Add `exclude_documents=` and stop there** (the 08-27 brief's Track D). Rejected. Exclusion on
  top of an alphabetical sort just promotes the sixth letter of the alphabet.
- **An embedding index for retrieval.** Deferred, not rejected. It needs a model dependency and
  offline test fixtures, and deterministic features have not been tried. Revisit if Track A's
  ranking measurably underperforms on leave-one-out.
- **A big-bang orchestrator refactor.** Rejected in favour of carving `grounding/` out as part of
  Track A, where the seam is forced by real work.
