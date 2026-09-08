# Codex-authored Verra PDD process

## Canonical flow

`MIXED INPUTS -> ACTIVE CODEX TASK -> SOURCE-PRESERVING VERRA PDD PACKAGE`

The active Codex task is the sole document authoring stage. It reads the
project evidence in place, applies the official Verra template, and performs
the render/review loop. It must not launch a nested `codex exec` process or
hand the final document to a second content-blind renderer.

For a repeatable source-preserving package, use:

```powershell
python scripts\run_pdd_in_place.py `
  --input-dir <project-file-or-folder> `
  --template library\templates\vcs\VCS-Project-Description-Template-v4.4-FINAL2.docx `
  --output-dir outputs\<run-name>
```

Project inputs may be YAML, JSON, PDF, Word, Excel, CSV, text, KML/KMZ or a
folder containing a mixture of those formats. The runner does not create an
intermediate facts YAML, deterministic narrative draft or replacement
calculation workbook.

## Stage 00_INPUT - evidence manifest

The runner inventories and hashes the supplied source files without changing
them. `00_INPUT/input_manifest.json` assigns each file one authority role:

- `project_input`: may support project facts and reported calculations;
- `example`: may support writing style and section organization only;
- `methodology` or `tool`: may support rules, applicability and calculation
  justification only; and
- `template`: controls the final Word structure and formatting.

Approved comparable-project PDDs belong in `inputs/pdd_examples/` by default,
or in the folder supplied with `--examples-dir`. An example must never supply a
current-project name, date, owner, location, parameter, assumption, formula or
number.

Active methodology and tool references are read from
`library/methodologies/active/`. Codex selects and reads the documents matching
the methodologies and tools identified in the project inputs. A methodology
document establishes the rule; project evidence must separately establish that
the current project satisfies it.

## In-place Codex authoring stage - sole authoring stage

The active task reads the run-local input manifest, source files, approved
examples, methodology/tool library, and the official template. It must:

1. read the relevant mixed project inputs directly;
2. produce finished prose for all 36 VCS Project Description template slots;
3. cite every claim with a PDF page, Word section, YAML path or Excel
   worksheet/cell/range;
4. transfer calculations only when they are already reported or formula-backed
   in an input workbook;
5. explain the calculation components, formula, units, periods and source-cell
   lineage and check them against the applicable methodology/tools;
6. preserve broken formulas, external links, stale cached values, conflicts and
   missing evidence as review items; and
7. attest that it created no new calculation or invented numeric value; and
8. render the Word/PDF output and inspect every page before release.

The in-place runner creates a traceability cover, preserves the authoritative
source PDD page-for-page, and appends read-only PDF renditions of the supplied
calculation workbooks. It does not create a normalized-facts YAML, a PREOUTPUT
prose stage, a nested Codex contract, or a replacement calculation model.

The final Verra deliverable is the PDF package; the Word file is a faithful
working copy for review. Supporting approvals, deeds, validation material and
exemption requests remain unchanged in the input evidence folder.

## Calculation requirements

- Do not build a new calculation model.
- Do not repair, overwrite or resave source workbooks.
- Use only workbook inputs, formulas, displayed/cached outputs and assumptions
  that can be traced to exact cells/ranges.
- State the source workbook, worksheet, cell/range, formula status, unit and
  period for every reported PDD calculation.
- Explain why the reported calculation follows the applicable Verra/CDM
  methodology and tools, with exact methodology/tool locators.
- A zero, not-applicable component or total is permitted only when directly
  supported by project evidence.
- If a value is ambiguous, stale, externally linked, formula-broken or missing,
  leave a data gap or review-required statement. Never recompute a substitute.

## Release gates

Before release:

1. confirm every source input is inventoried and hashed;
2. confirm the source PDD and calculation evidence are present;
3. verify no new calculation model or unsupported value was introduced;
4. render the DOCX and inspect every page when LibreOffice is available; and
5. record source, template and final artifact hashes in the run manifest.

The output remains review-ready, not automatically approved, validated,
registered or submission-ready.

## Legacy process

The historical `INPUT -> YAML -> PREOUTPUT -> CODEX_FINISHED` pipeline and its
scripts are retained under `_archive/cleanup_20260827/` for recovery only. They
are not the canonical PDD creation route and must not be used as project
evidence.
