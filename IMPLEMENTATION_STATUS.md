# Implementation status
Overall: IN_PROGRESS. Branch: implementation/lite-standalone.

## Milestones
- A Discovery: VERIFIED — attached DOCX identical to repository original; SHA256
  1ffb40cc6ea0c3b6c5627d2be2b86646b8e0c3f39aec562748dea2d754732896.
  Extracted 1,094 paragraphs, 19 tables, all 25 sections, three figures; no OMML equations.
  Inspected all three figures, frozen formula and scientific/engineering acceptance matrices.
  Read reference global/fitting DP, assignment and normalization; no runtime reuse/import planned.
- B Standalone engine: IN_PROGRESS.
- C Dashboard: NOT_STARTED.
- D Manual review: NOT_STARTED.
- E Reporting/install: NOT_STARTED.
- F Final verification: NOT_STARTED.

## Decisions
Use immutable dataclasses, explicit JSON schemas, exact integer tolerance, cached traces,
and exact lexicographic one-to-one optimization. Underspecified biological identity abstains.
Local single-user persistence only; public deployment forbidden.

## Completed / in progress
Discovery, package scaffolding, isolated Lite virtual environment; engine implementation next.

## Blocked/unimplemented
B–F not implemented yet. No external blocker identified.

## Commands and evidence
DOCX ZIP/XML extraction and image inspection succeeded. Dedicated implementation branch created.
No application acceptance tests executed yet. No completion claims.

## Limitations/deviations
Pool/Kd scoring and shared multiuser hosting are deferred by the contract, not part of sequence MVP.
Windows installation will be documented; actual Windows execution requires a Windows host.

## Next action
Implement and verify standalone engine and its scientific fixtures.

## Milestone B–E update
B engine: VERIFIED (focused and integration suite). C dashboard: IMPLEMENTED_UNVERIFIED
for real browser uploads; Streamlit AppTest interactions VERIFIED. D review: VERIFIED
by backend and actual Streamlit interaction tests. E reports: VERIFIED for synthetic CLI,
JSON and readable rich-text XLSX; installation documentation still IN_PROGRESS.

Executed `.venv/bin/python -m pytest -q`: **40 passed in 1.88s**.
Executed `.venv/bin/python -m pip check`: no broken requirements.
Executed installed package CLI on examples: G5 E5 M3 TP3 FP2 FN2 (adaptive/core/all).
Outputs: `.local/cli-first/{evaluation.xlsx,audit.json,review.json}`.
Streamlit AppTest exercised sample load, run, score controls, paper/candidate selection,
incorrect association confirmation, conflict warning and undo; local review file verified.
Automated browser install encountered a download failure; diagnosis in progress.

Policy detail: unique strict anchors first. Remaining exact one-to-one optimization uses
lexicographic name support, cardinality, total core completion, conditional global completion;
each selected edge is forbidden once to detect equivalent optima. No arbitrary numeric margin.
Exact repeated motifs without name evidence, ambiguous fit placement, ambiguous alphabet,
identical golds and contradictory duplicate names abstain. Identical-gold duplicate capacity
retains raw physical items. These conservative §24 choices require research-owner review
before any expansion of automatic identity acceptance.

## Final verification in progress
Executed focused suite after hardening: **50 passed in 2.85s** (browser test excluded).
Read-only historical pure-alignment regression: 14 synthetic comparisons frozen with
source SHA256; distances and optimal-interval counts agree. Exact assignment also
checked against brute-force enumeration on 60 seeded integer matrices.
Clean-source/clean-venv installation succeeded with requirements.lock; isolated `-I`
imports confirm `aptabench` absent and Lite imported from clean-source. Independent
sample evaluation reproduced G5 E5 TP3. No original repository changes detected.

Representative inputs: 248 gold rows, 308 raw extractor items, 49 gold papers,
44 linked attempted papers, 606 candidate comparisons. Adaptive/core/all automatic
G97 E278 M49 TP49 FP229 FN48; 48 pending identities. This is a provisional conservative
result, not a scientific identity guarantee. Source workbook hashes unchanged.
Profile with Python tracemalloc enabled: engine 55.024s, export 1.402s, peak Python
allocations 40.608 MiB, 1,281 uncached DP calls. Files remain private in
`.local/representative/`; no historical workbooks/outputs added to Git.

Browser verification: system Chromium starts and real uploads/evaluation execute.
Test harness synchronization of Streamlit's asynchronous dropdown/rerun remains under
investigation; full browser acceptance NOT yet verified. Browser binary CDN download
was policy-denied; system Chromium avoids that external prerequisite.
README, pinned dependencies, local Windows launcher, science policy, review workflow
and acceptance matrix added. Native Windows/macOS execution has not been tested.
