# AptaBench Lite implementation status

Overall: **VERIFIED** for the standalone local sequence application on Python 3.12/Linux.
Current reviewed integration: PR #5, prepared on `integration/latest-pull-requests`.
The latest user request authorizes handling and merging the reviewed pull requests.
Historical task sections below retain their then-current approvals and blockers.
No main-branch merge or public deployment was performed by this repair task.
Current dashboard validation: **70 tests passed**, including sequence and optional Pool/Kd browser flows.
Sections 1–12 preserve historical implementation evidence; section 13 records the current repair.
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


## 13. Merged-dashboard regression repair — November 24, 2026

Status: **VERIFIED** locally. Branch: `fix/dashboard-merged-regressions`.
Inspected latest main `2c2415b`, including PR #1 (three-sheet dashboard/reports)
and PR #2 (practical review with optional Pool/Kd). The original 57 tests passed
on merged main but did not cover the reported Pool/Kd freeze.

### Confirmed failure and root cause

The Pool validator introduced in `3f9a69e` used the nested expression
`(?:[ACGTU]+|N\d+)+`. On a sufficiently long valid base prefix followed by an
unsupported character it performs catastrophic backtracking, blocking the Python
process and Streamlit's server. A pre-fix subprocess reproduction using 40 A bases
plus X exceeded the two-second timeout and was killed. A long real-workbook prefix
can therefore make Run appear endless and prevent the dashboard responding even
when the browser is closed/reopened. The user's exact uploaded files were not
available in this turn; the same failure was reproduced synthetically.

Fix: remove the ambiguous inner repetition: `(?:[ACGTU]|N\d+)+`. The accepted
Pool-template language is unchanged. Bounded subprocess regression checks reject
100,000-base invalid tails quickly; exhaustive short-string checks prove agreement
with the original validator's acceptance language. Unsupported templates are
retained for review, not silently repaired or awarded credit. No Kd tolerance,
unit conversions, sequence matching, normalization or scoring rules were relaxed.

### Other targeted corrections

- Unresolved-first sequence ordering keeps resolved golds inspectable and retains
  the selected record across review changes. Optional field selectors use stable
  record IDs instead of mutable list indices.
- Predictions from papers outside the declared attempted population remain in the
  audit but do not inflate optional-field closed-world E/FP. Source inventories
  and existing review backup fingerprints remain preserved.
- JSON audit downloads now include optional field inputs, automatic/effective
  results and review events, matching the three-sheet Excel report. Field exports
  validate replay history and reject data from a different sequence run.
- Malformed field-review records now raise readable ValueErrors (types, field IDs,
  timestamp/timezone and revisions) rather than crashing or silently ignoring actions.
- Run publishes sequence and optional state together only after all loading succeeds;
  a field input/review-load error cannot leave a half-initialized dashboard run.
- Field review actions display a saved-revision confirmation. Test stores are isolated.
- CI now triggers for main, fix/feature branches and pull requests, installs Chromium
  and includes browser tests instead of covering only one old feature branch.
  Remote CI has not been claimed as passed; the evidence below is local execution.

### Executed verification

- Baseline main: `.venv/bin/python -m pytest -q`: **57 passed in 15.90s**.
- New regression fixtures reproduced the untested selector, scope, audit and
  review-import failures before their fixes. The freeze reproduction used a
  timeout-isolated subprocess so it could not lock this work session.
- Final `.venv/bin/python -m pytest -q --basetemp .local/merged-tests`:
  **70 passed in 25.88s, no failures or skips**.
- Real Chromium tests cover both the original sequence flow and actual uploads
  with Pool/Kd enabled, a previously hanging malformed template, Run, field review,
  Excel/JSON download, undo, page reload and persisted review restoration.
  Optional browser Run: **1.254s** on the synthetic regression fixture; HTTP health
  remained 200. Evidence: `.local/merged-tests/test_optional_pool_kd_run_revi0/`.
- Representative existing workbooks with both optional fields enabled: sequence
  **2.696s**, optional input loading **0.028s**, export **0.562s**. Source hashes
  unchanged. Sequence counts remain G97/E278/M49/T49. Pool G42/E44/M40/T20,
  Kd G91/E156/M8/T4; pending identities remain explicit. Private evidence and
  outputs: `.local/merged-representative/verification.json`, `evaluation.xlsx`,
  `audit.json`. These measurements are observations, not promised runtimes.
- `.venv/bin/python -m pip check`: no broken requirements.
- Reference repository working trees remain unchanged; no private workbooks or
  representative outputs are staged. The original master DOCX is unchanged.

### Remaining scope and next action

The code repairs are verified on Linux/Python 3.12. Native Windows/macOS and
remote hosting remain unverified. Optional Pool/Kd policies were inherited from
the merged feature branch; their scientific authorization/calibration is not
established by these runtime tests. The repair does not change the inherited 5%
Kd comparison rule. No public deployment or merge to main is authorized/performed.

Review/merge the repair branch, or run it directly, then stop/restart the Streamlit
server. Closing only its browser tab does not stop an already-stuck Python process.
The repaired loopback dashboard is started and health-checked in this workspace;
this does not restart a server on the user's separate machine.

## 14. PR #5 integration with explicitly supplied workbooks — November 25, 2026

Status: **IMPLEMENTED_UNVERIFIED** for the final GitHub issue/PR review; local
integration and supplied-file verification are **VERIFIED**. Main publication is
pending access to the repository issue instructions requested by the user.

User explicitly authorized merging branches to main, superseding the previous
no-main-merge task restriction. Work was prepared on `integration/all-branches`
from main `ea45628` and PR #5 head `65c801a` (`fix/pool-kd-performance-privacy`).
Other published feature/fix/implementation heads were already included in main.

Resolved actual conflicts in the workflow, README, Pool regex, UI and Pool tests:
- Preserve main's finite-time validator and existing accepted token language.
- Integrate PR #5's explicit **Prepare Excel report** action and state fingerprint
  invalidation; do not build Excel on every ordinary UI rerun.
- Retain the earlier review, attempted-population, field-audit and transactional
  Run fixes. In particular, the new branch must not regress Pool/Kd JSON audit data.
- Keep broad main/PR/fix CI coverage and add integration branches; preserve both
  sets of regression tests. Existing synthetic fixtures were NOT used for this task.
- Update the optional browser test for the newly explicit report-preparation step.

### Supplied-file-only verification executed

Only the user's uploaded `gold.xlsx` and `extractor.xlsx` were used. Exact private
copies and their hashes remain under ignored `.local/user-inputs/`. No examples,
sibling-repository workbooks or modified/manufactured workbooks were substituted.
No private inputs or full evaluation outputs are staged.

- A timeout-isolated reproduction of the old regex stalled on the uploaded gold
  at source row 243; the subprocess was stopped after two seconds. This establishes
  the freeze on the actual supplied input rather than only a synthetic pattern.
- `scripts/verify_supplied_workbooks.py --gold ... --extractor ... --output-dir ...`
  verified sequence-only, +Pool, +Kd and combined variants; fixed association
  invariance; exact count reconciliation; source-hash preservation; sequence/field
  review save/import/undo; readable Excel and matching JSON audit.
- `APTABENCH_TEST_GOLD=<uploaded gold> APTABENCH_TEST_EXTRACTOR=<uploaded extractor>
  .venv/bin/python -m pytest -q tests/test_uploaded_workbooks.py --basetemp .local/uploaded-tests`:
  **2 passed in 36.75s**. The second test used actual Chromium uploads and live
  Streamlit, all four field configurations, on-demand preparation/download,
  invalidation after scoring/review changes, field action/undo, and page reload.
- Browser observed Run times: sequence 5.229s cold; Pool 0.823s; Kd 0.767s; combined
  0.778s (warm sequence cache reused). Explicit report prepare/download: 1.461s.
  These are measurements on this environment, not promised runtimes.
- Both uploaded source hashes remained unchanged. Detailed private evidence:
  `.local/supplied-verification/` and `.local/uploaded-tests/`.
- Existing synthetic-workbook test suite was deliberately not executed, per the
  user's instruction to use only the two supplied files for testing/reproduction.
  Historical suite results elsewhere in this file do not describe this integration.

### External blocker / required next action

Native authenticated Git fetch/push works, but the environment rejects CONNECT
requests to `api.github.com` with HTTP 403. GitHub CLI issue/PR reads therefore fail.
Private github.com issue/PR HTML returns 404 without the API's authentication route.
The issue instructions themselves have not been read; no claim that issues are
resolved or required GitHub review/checks were inspected is made.

The user was asked to paste the issue instructions or allow `api.github.com` in
running environment settings. Once available, read those instructions and PR #5,
complete any required work, recheck current branch tips, then promote the verified
integration to main and confirm all remote branch heads are ancestors. No force
push, branch deletion or public app deployment is intended.


## 15. Full real-input Pool/Kd profiling (historical branch verification) — November 25, 2026

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

Published: performance code commit `cc4e1c8` is pushed to
`fix/pool-kd-performance-privacy`; working tree is clean. Main remains `ea45628`.
`gh pr create --base feature/practical-review-pool-kd --head fix/pool-kd-performance-privacy`
failed because `https://api.github.com/graphql` returns Forbidden in this environment.
No new PR was created. The complete focused description is in ignored
`.local/performance-pr.md`; the review/creation URL is:
https://github.com/vajrala-abhinav/AptaBench-Lite/compare/feature/practical-review-pool-kd...fix/pool-kd-performance-privacy?expand=1

Remaining external blocker: permit GitHub API access or create that focused PR from
the compare page. Implementation and local verification are complete. Remote CI and
native Windows/macOS are not claimed verified. No merge was performed; do not auto-merge.


## 16. Final reviewed PR integration — November 25, 2026

Local integration: **VERIFIED**. Target: PR #5 into main.
Starting main `242cfa1` already includes PR #7 (`integration/all-branches`).
Feature tip `6fe2255` includes PR #6 and performance tip `5b6f5a0`; these are the
remaining changes not yet represented in starting main. Prior no-auto-merge task
instructions are superseded by the user's explicit request to handle all PRs/merges.

Resolved the real conflicts between main and the updated feature tip:
- Keep earlier dashboard, attempted-population, review integrity and complete field
  JSON/Excel audit fixes from main.
- Integrate cached optional ingestion, opt-in privacy-safe timing instrumentation,
  distinct Run phases and explicit/stale-safe Excel preparation.
- Preserve both branches' documentation and verification history. No scientific
  normalization/association/tolerance changes introduced by conflict resolution.

Executed combined validation:
`APTABENCH_TEST_GOLD=<supplied gold> APTABENCH_TEST_EXTRACTOR=<supplied extractor>
.venv/bin/python -m pytest -q --basetemp .local/final-integration-tests`:
**78 passed in 97.80s**, including both original browser flows and both supplied-file
integration/browser suites. Private evidence remains ignored under `.local/`.
Independent signatures against starting main match for all four modes and eight
scoring views, including source records, traces, decisions and field outcomes.
`git diff --check`: clean. No private XLSX, raw biology or JSON evidence staged.

GitHub API access was restored after the network allowlist update. Inspected all
PRs and open issue #4. PR #5 was the sole open PR, with no review comments or
outstanding formal review decision; PRs #6/#7 were already merged and checks green.
Issue #4's real-data, schema, bounded freeze reproduction, privacy, cache, review,
Excel and benchmark requirements were checked against the completed evidence.
Branch-protection administration details are not readable by the connector; standard
GitHub PR merging and its check/review policies remain authoritative.

Workflow: push this resolved candidate to PR #5's existing head branch, wait for its
current-head GitHub checks to pass, and merge via GitHub without admin overrides,
force pushes or source-branch deletion. Final check results and merge SHA are recorded
on https://github.com/vajrala-abhinav/AptaBench-Lite/pull/5 . All published branch and
PR head SHAs are checked for ancestry in the resulting main, and no unrelated
reference repository or source workbook is modified.


## 17. Excel report redesign — IN_PROGRESS

Branch: `feature/excel-report-redesign`, based on main `d535472`. Verified remote
`fix/pool-kd-performance-privacy` tip `9a053a9` is already an ancestor of main.
Scope: Excel projection and report selection labels/tests/docs only; scientific
algorithms, fixed associations, field evaluation and review behavior remain unchanged.
Plan: six ordered sheets, compact interpretation/metrics, dedicated paper and pair
tables, complete candidate audit, operational/review log and separated inventory.
Existing on-demand report identity/invalidation is retained. Verification pending.
Private supplied workbooks exist under ignored `.local/user-inputs`; use only those
for optional real-data validation and synthetic fixtures for committed examples.

Report implementation: **IMPLEMENTED_UNVERIFIED** (comprehensive verification ongoing).
Focused original export/field tests: **22 passed in 1.25s**. New report tests: **7 passed
in 2.41s**, including frozen pre-refactor numerical dictionaries, all candidate IDs,
effective incorrect human confirmation, Pool/Kd provenance, sheet subsets and AppTest
report invalidation after scoring/sheet/field review/sequence review changes.
Synthetic six-sheet sample generated successfully with the committed generator under
`.local/report-redesign/synthetic-six-sheet.xlsx`; migration map in
`docs/excel-report-layout.md`. Full browser/real-input suite and privacy checks pending.

Real-input report comparison: **VERIFIED** for sequence, Pool, Kd and Pool+Kd on the
supplied full pair. Baseline `d535472` exporter/audit loaded privately for comparison;
all eight calculated views and complete scientific audits match. All 50 accepted
associations and 606 candidates exported, no new alignment calls, source hashes
unchanged (prefixes `a015e5b896c2` / `6986787019d5`). Final export observations
0.918–1.033 s versus old 0.555–0.630 s; details in docs/excel-report-layout.md.
Sample readback: six exact sheets, 51-row summary, populated-section table filters,
frozen headers, percentage formats and rich-text alignments. Native Excel rendering
is unavailable; structural/style metadata readback and browser downloads are verified.

An intermediate comprehensive run had **84 passed / 1 failed**: the supplied-input
verification script retained its old three-sheet assertion. Updated that script and
the benchmark assertion to the explicit six-sheet contract; affected real-input check
rerun: **1 passed in 5.62s**. Final focused export/field/UI tests: **29 passed in 3.37s**.
`pip check`: no broken requirements. Comprehensive final rerun in progress.

### Final report-redesign acceptance — VERIFIED

- Python 3.12 full suite, with the actual supplied paths explicitly enabled:
  `APTABENCH_TEST_GOLD=<private gold> APTABENCH_TEST_EXTRACTOR=<private extractor>
  .venv/bin/python -m pytest -q --basetemp .local/report-redesign/final-tests`
  → **85 passed in 99.03s**, no skips/failures. Includes Chromium upload/download,
  real-file four-mode evaluation, review resume/import/undo and cache checks.
- Seven new report-focused tests verify exact six-sheet order and independent subsets,
  all eight overall views/definitions, no summary inventories, exact effective pairs,
  all candidates/outcomes, Pool/Kd review/provenance, raw/logical/duplicate inventories,
  frozen pre-refactor metrics and report invalidation after relevant state changes.
- Only `exports.py` and the UI report options/import/caption changed under the engine
  package; matching, normalization, resolution, scoring and review modules are untouched.
- Source workbook hashes unchanged; no private inputs or generated evidence committed.
- Synthetic deliverable: `.local/report-redesign/sample-six-sheet.xlsx`; reproduce
  with `scripts/make_report_example.py --output <new-path.xlsx>`.
- Excel desktop rendering remains unverified on this Linux machine; workbook structure,
  style metadata, rich text, metric values and browser downloads have been verified.
- Implementation is on `feature/excel-report-redesign`; open PR for review. **Do not
  auto-merge.** No scientific owner decision or implementation blocker is outstanding.

Next action: human review of the focused PR and sample workbook; merge only on request.
