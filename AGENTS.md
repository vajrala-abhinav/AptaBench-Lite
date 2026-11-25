# AptaBench Lite
Standalone local Streamlit evaluator for research-team/PI review of extracted aptamer sequences.
Scientific authority: docs/AptaBench_Lite_Master_Design_Document.docx (frozen v1.0).
The extracted text and three figures in docs/ preserve its full 25 sections and 19 tables.

## Architecture and invariants
- readers/config: safe XLSX/structured-cell ingestion, exact provenance, explicit mappings.
- normalization/alignment: lossless canonicalization; unit-cost global and full-gold fitting traces.
- candidates/resolver/engine: significant-gold-only, same-paper graph; unique strict anchors,
  sequence-local names, one-to-one contextual resolution and conservative abstention (§§5–11).
- scoring: association establishes identity; correctness tests those fixed links (§12).
  Display toggles never rematch. Closed-world TP=T, FP=E-T, FN=G-T.
- review: immutable automatic result plus append-only validated events, explicit atomic reassignment,
  undo, fingerprinted durable replay (§§13–14). Human identity confirmation never overrides bases.
- exports/UI: one result and stored traces, identical numerical values/color operations (§§15–18).
- Excel presentation follows docs/excel-report-layout.md: six ordered sheets, compact overall
  summary, effective accepted pairs, full candidate audit and separate inventories. Reporting
  revisions must preserve numerical results, stored traces and on-demand cache invalidation.
- Strict canonical extractor duplicates only; preserve raw IDs and identical-gold multiplicity.
  No row-order identity tie-break, fuzzy deletion, cross-paper matching, T/U conversion or RC TP.
- Do not invent scientific heuristics, probabilities, margins or denominator definitions.
  Underspecified identity cases abstain with reasons (§24); policy changes need version/test/research review.

## Workflow and privacy
Work only in AptaBench-Lite; do not modify sibling repositories.
Use an implementation branch unless the user explicitly authorizes integration into main.
Do not import sibling packages at runtime. Reference implementations may be read for regression evidence.
Use this existing isolated checkout; no worktree unless requested. Do not deploy publicly.
Keep private inputs, .venv and generated outputs untracked; never overwrite source workbooks.
No research-data uploads, telemetry or external APIs during evaluation.
Deterministic decisions and run fingerprints must be invariant to caches and harmless row ordering.
Maintain IMPLEMENTATION_STATUS.md after each meaningful milestone using actual test evidence.
Run .venv/bin/python -m pytest; verify installed CLI, real Streamlit upload/review/export,
clean independent installation and report reconciliation before claiming completion.
Real-input performance checks require explicit private workbook paths; log only
counts, timings, status categories, lengths and truncated fingerprints. Live timing
traces are opt-in. Never change scientific policy to address a performance problem.
