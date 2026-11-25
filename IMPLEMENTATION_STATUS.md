# AptaBench Lite implementation status

Overall: **VERIFIED** for the standalone local sequence application on Python 3.12/Linux.
Branch: `implementation/lite-standalone`. No main-branch merge or public deployment.
Scientific correctness is bounded by the frozen contract and tested fixtures; no claim of
universal biological identity is made. See docs/acceptance.md for requirement-to-test mapping.

## 1. Milestones

| Milestone | Status | Executed evidence |
|---|---|---|
| A Discovery/specification | VERIFIED | Attached DOCX preserved unchanged; all 25 sections, 19 tables, 3 diagrams extracted/inspected; references read without modification |
| B Standalone engine | VERIFIED | Normalization, safe readers/mappings, linking/scope, dedup/capacity, global/fitting DP, strict/name/exhaustive stages, one-to-one resolution, tie/runner-up abstention and metrics tests |
| C Streamlit dashboard | VERIFIED | AppTest and real Chromium upload→configure→run→navigate→score→alignment workflow; selected-pair persistence regression |
| D Manual review | VERIFIED | Confirmation, rejection, missing, unresolved note, atomic reassign, targeted undo, immutable automatic state, checksummed fingerprint/revision replay; real browser review/download/reload/import |
| E Reporting/installation | VERIFIED | Excel/JSON reconciliation, rich-text + operation-colored cells, safe formula handling, examples, installed CLI, pinned independent environment, setup/user documentation |
| F End-to-end verification | VERIFIED | 52-test combined suite including browser; independent installation's 51 non-browser tests; representative private XLSX batch; source hashes unchanged |

## 2. Specification and implementation decisions

Authoritative DOCX SHA256:
`1ffb40cc6ea0c3b6c5627d2be2b86646b8e0c3f39aec562748dea2d754732896`.
The newly attached file was byte-identical to the repository original. Extracted 1,094
paragraphs, 19 tables, all 25 numbered sections and three media figures; there were no
OMML equations to omit. Formulas are preserved as text. `docs/master-design.txt` and
`docs/figure-*.png` make the source searchable/inspectable.

- Standalone immutable dataclasses and callable library; Streamlit and exporters contain
  no alternate matching algorithm. No runtime sibling imports, paths or virtual environments.
- Scientific policy `lite-seq-v1.0-conservative`; exact integer edit budget and literal
  forward bases. Only significant golds in linked attempted papers enter G.
- Unique uncontested strict-whole anchors execute first; remaining named comparisons use
  the shared provider before the exhaustive remaining graph. Locked endpoints never enter
  subsequent assignment. Preempted comparisons remain available for inspection only.
- Remaining one-to-one objective is exact lexicographic local-name support, cardinality,
  total full-gold core completion, then conditional global completion for actual competition.
  One forbid-edge counterfactual per proposed edge identifies equivalent alternatives.
  No confidence percentages, numerical margins or row-order biological decisions.
- Exact repeated motifs without adequate name evidence, multiple equal fits, ambiguous
  alphabets, identical gold identities and contradictory names abstain conservatively (§24).
  No arbitrary minimum length. Identical-gold duplicate groups preserve raw item capacity.
- Review is a durable identity overlay. It never edits source bases, reruns alignment or
  converts an incorrect value into TP. Scoring/export uses fixed stored evidence.
- Local single-user autosave with lock, revision validation, checksum, atomic replace and
  backup. Shared authenticated multiuser service is not claimed.

## 3. Completed functionality

All sequence-module requirements described in milestones B–E are implemented and verified.
Configurable worksheets/headers, historic preset suggestions, structured/simple input modes,
explicit significant/present labels, manifest attempts, safe paper aliases, validation inventory,
lossless normalization and source/list-index provenance are available. Raw, parseable, invalid,
unique/logical and suppressed prediction counts plus multiplicity exceptions reconcile.
Dashboard offers three primary scientific scoring controls, per-paper counts/progress,
selectable gold/extractor panels, availability and competitor evidence, cached alignments,
all six review actions, durable save/resume and Excel/JSON/configuration downloads.

## 4. In-progress functionality

None for the agreed local sequence-module acceptance scope.

## 5. Blocked or unimplemented requirements

No essential local sequence requirement is blocked. Contract-deferred modules remain
unimplemented: pool/Kd scoring, modified-base interpretation, IUPAC wildcards, reverse-
complement equivalence, authenticated shared hosting and research-data retention services.
No public deployment was performed. Native Windows/macOS execution is unverified; their
installation commands and Windows launcher are supplied, but only Linux was available.

## 6. Actual test commands/results

- `.venv/bin/python -m pytest -q --basetemp .local/acceptance-tests`:
  **52 passed in 16.84s**, including system Chromium browser test, with no skips.
- After adding the per-paper resolved-outcome progress display:
  `.venv/bin/python -m pytest -q tests/test_ui.py`: **1 passed in 1.63s**.
- Independent copied source/environment:
  `.local/clean-venv/bin/python -I -m pytest -q .local/clean-source/tests --ignore=.local/clean-source/tests/test_browser_e2e.py --basetemp .local/clean-verified-tests`:
  **51 passed in 3.05s**. This separate environment was installed from `requirements.lock`
  and its own copied Lite source. `find_spec('aptabench') is None` was asserted; isolated
  evaluation and updated Excel exports reproduced the synthetic counts.
- `.venv/bin/python -m pip check`: **No broken requirements found**.
- `git diff --check`: passed. Both reference repositories' `git status --short`: empty.
- Alignment oracle enumerates all substrings of all binary strings of lengths 1–4;
  global/fitting distances and all optimal-interval counts agree independently.
- Adaptive integer budget checked for lengths 1–10,000; assignment solver checked against
  brute-force enumeration of 60 seeded matrices with arbitrary-size integer weights.
- Fourteen synthetic global/core cases frozen from the reference pure alignment function
  agree in distance/interval count. Corpus includes reference source SHA256 and deliberate
  Lite policy differences. No old package is imported by these regression tests.

Earlier failures were investigated and corrected: an equally optimal display traceback,
review-import schema checks, Streamlit asynchronous test selection and dynamic-option
labels resetting selected pairs. The final passing checks cover those paths; no failures
were disabled or assertions weakened. Playwright's CDN browser download was policy-denied;
the existing system Chromium was used successfully instead. No network-policy changes
or verification bypasses were required.

## 7. End-to-end evidence

Installed CLI:
`.venv/bin/aptabench-lite --gold examples/gold.xlsx --extractor examples/extractor.xlsx --output-dir .local/handoff-sample`

Synthetic automatic adaptive/core/all: **G5 E5 M3 T3 TP3 FP2 FN2**.
Artifacts: `.local/handoff-sample/evaluation.xlsx`, `audit.json`, `review.json`.
Excel opens successfully and reconciles to the JSON/UI counts.

Real browser: actual XLSX uploads, evaluation, paper/record navigation, incorrect identity
confirmation, score toggle, Excel and JSON download, undo, reload/re-upload, automatic
local resume and review-state JSON restore all executed. The downloaded reviewed audit
has original automatic M3 preserved and effective M4/T3: **75% matched-pair correctness**,
**60% significant recovery**. Undo restores original links. Selected pair remains selected.
Browser artifacts/screenshots are under `.local/acceptance-tests/test_browser_upload_review_exp0/`.
Measured score-toggle rerun in that synthetic browser test: **0.512s** (one local observation).

Representative private workbooks (explicit developer profile, not normal user Run):
248 gold rows, 308 raw extractor items, 49 gold papers, 44 linked attempted papers,
606 same-paper candidates. Automatic adaptive/core/all: **G97 E278 M49 TP49 FP229 FN48**;
48 identities remain pending conservatively, five gold papers are unattempted. Counts
reconcile to original IDs; both workbook SHA256s remain unchanged. No research inputs
or reports are staged/committed. Private outputs: `.local/representative-verified/`.

Measured final instrumented run with Python tracemalloc enabled: total engine **53.588s**;
parsing/linking **0.610s**, normalization **0.036s**, alignment comparisons **52.865s**,
assignment **0.039s**, exports **1.750s**, peak Python allocations **42.448 MiB**;
**1,281** uncached DP comparisons. These are environment-specific traced measurements,
not a promised runtime or total process memory benchmark.

## 8. Known limitations/deviations

- Conservative §24 identity rules can leave genuine matches unresolved. Research-owner
  review is needed before relaxing these rules or changing the documented objective.
- No calibrated biological confidence model or universal identity guarantee is asserted.
- Native Windows/macOS and authenticated shared deployment were not available/tested.
- Safety resource limits are documented in README; violations stop with diagnostics and
  never silently skip sequences. Excel's cell limit may truncate explicitly labeled long
  provenance text; the full original remains in JSON. Counts/traces are unchanged.
- Review checksums detect corruption, not forgery/authentication. Single-user local scope.
- Historical policy parity is intentionally limited to unchanged pure-alignment behavior;
  Lite's significant-only scope, one-edit minimum, assignment and metrics supersede older rules.

## 9. Repository and privacy status

Implementation is isolated on `implementation/lite-standalone`, with meaningful tested
milestone commits. Original repositories/workbooks and authoritative DOCX are unchanged.
Only synthetic example XLSX files are included; `.local`, private inputs, outputs and
virtual environments are ignored. No cloud-environment draft was reapplied or published.
Branch publication status is recorded in the final handoff after the push attempt.

## 10. Next action

Research-owner acceptance review of the implementation branch and conservative scientific
policy. No implementation blocker remains for local sequence evaluation. To run, follow
README.md or use `.venv/bin/python -m streamlit run app.py` from this repository.

## 11. Feature branch: report/dashboard simplification (unverified changes)

Branch: feature/three-sheet-dashboard-review, based on the previously verified sequence baseline.
The sequence alignment, candidate matching, resolver and metric denominator definitions have not changed.

- Excel was consolidated from nine fixed worksheets to three available tabs: Simple Summary, Debug Log and Logistics.
- UI offers an inclusion checkbox and selectable tabs, with all three selected by default.
- Browser controls the file save destination; Streamlit has no client-side folder picker.
- Simple Summary includes eight metric combinations, per-paper rows, per-record completion and significant status.
- Debug Log preserves effective and automatic association IDs, all candidate comparisons, aligned traces, reasons and source provenance.
- Logistics preserves hashes, configurations, input diagnostics, review history, inventories and deduplication.
- The full machine audit remains exportable as JSON.
- A read-only unresolved-gold reason breakdown assists future safeguard ablation; it does not alter a match or score.
- Tests were updated and expanded, but HAVE NOT BEEN EXECUTED on this feature branch. The prior 52-pass evidence only describes the original baseline.
- Pool and Kd remain deferred; one-Kd-per-aptamer scoring requires agreed field mappings and rounding tolerance.
- Do not merge until running Python 3.12 tests, inspecting exported workbook, and exercising Windows launch.

## 12. Practical workflow feature branch (new, targeted validation)

Branch: feature/practical-review-pool-kd. This extends the three-sheet report
branch without merging to main. It adds optional Pool/Kd workbook field mapping,
exact library-template comparison, one-Kd-per-aptamer numerical evaluation with
unit conversion and a 5% rounding tolerance, an independent append-only reviewed
field overlay, recalculated field results, backup export/restore, and an
unresolved-first sequence-review selector. Sequence matching and denominators
remain unchanged; this is a deliberate constraint until manual adjudication
provides evidence for relaxing conservative matching safeguards.

Pool/Kd comparison has its own closed-world denominator caveat and never
interprets numerical proximity as identity. Manual confirmation changes record
identity only, not the stored value. Unknown/ambiguous field identities are left
for review instead of forced matches.

Synthetic tests were added for units, one-to-one field associations, review
action and undo, optional field export, and unchanged sequence metrics.
A branch-specific Python 3.12 CI workflow executes non-browser tests.
**Check the current CI run before merging**; prior milestone evidence does not
automatically validate this new feature.

## 13. Full real-input Pool/Kd profiling — November 25, 2026

Current work: `fix/pool-kd-performance-privacy`, based on `65c801a`.
Status: **VERIFIED** locally for performance, repeatability and UI behavior. No merge
was performed; latest user instruction explicitly requires approval before merging.
The earlier integration branch is separate and has not been promoted by this task.

Full input availability was confirmed from the existing user uploads: preview exactly
248 gold rows, 116 significant records, 6,309 significant bases, 44 attempted linked
papers and 308 raw sequence items. No replacement extractor was requested or needed.
Only this pair was used for real-data reproduction/benchmarks. Normal unit fixtures
remain synthetic as requested by the complete regression-suite requirement.

Completed:
- Preserved the preliminary safe validator and on-demand Excel implementation.
- Bounded legacy-regex probe reproduced the freeze on the supplied gold after imports
  and reading completed; killed after 250ms. Safe scan of all 243 nonblank Pool values:
  1.70ms, >147x below the canceled lower bound. Preliminary count 245 was not reproduced;
  this supplied workbook has 243 nonblank and three whitespace-only non-null Pool cells.
- A second bounded old-validator probe inside actual load_fields timed out after
  sequence finished and before Excel started, confirming spinner-stage attribution.
- Two cold runs of each of four modes profiled XML parsing, sequence computation,
  Pool/Kd normalization, real-file review restoration, scoring and Excel export.
- Opt-in context-local instrumentation records only call counts and durations. New
  alignment counts measure cache misses, not calls that reuse an existing trace.
- Optional field ingestion cached by input bytes, run ID and mappings; review restoration
  stays live. Repeated Run, score toggles, exports and resume had zero input parse/alignment.
- Separate sequence / optional field / review-restore spinners make the original stall
  attributable to Pool normalization in load_fields, not to Excel outside that spinner.
- UI publishes state only after all Run stages succeed; prepared reports invalidate on
  scoring/review changes. All three sheets, review backup import/resume/undo checked.
- Scientific-output hashes match starting commit 65c801a for all four modes and eight
  sequence views. No metric/association/tolerance/one-to-one change was introduced.

Actual checks:
- Initial full suite: 59 passed in 15.52s.
- Focused engine/reader/normalization/field/UI suite during implementation: 39 passed.
- Full Python 3.12 suite with supplied-input variables: **63 passed in 44.87s**, no skips.
- Latest default-off tracing/privacy focused checks: 3 passed in 1.35s; real cache check
  1 passed in 4.16s. Browser synchronization was corrected to wait for a completed
  post-action render/revision, avoiding downloading stale pre-undo widget data.
- Scientific baseline comparison: all four modes / all eight sequence views equal.
- Cold benchmark: two repetitions per mode, scientific repeatability verified; source
  hashes unchanged. Detailed anonymized table: docs/performance-benchmark.md.
- `pip check`: no broken requirements; no new dependencies. `git diff --check`: clean.

Private evidence (ignored; never commit): `.local/performance-final-benchmark/`,
`.local/performance-final-suite/`, scientific comparison and local review snapshots.
The committed benchmark document contains only aggregate timings/counts and truncated
fingerprints. No workbooks, raw biological strings, JSON evidence or credentials staged.

Remaining: publish the fix branch and create a focused PR to
`feature/practical-review-pool-kd`. GitHub API access currently returns Forbidden;
if PR creation remains blocked, provide the exact compare link and local PR body.
Remote CI and native Windows/macOS are not claimed verified. Do not auto-merge.
