# AptaBench Lite

A standalone local Streamlit application for a research team and PI to evaluate
aptamer sequence extraction against **significant gold sequences only**. No Codex,
LLM, API key, sibling repository, GPU or online service is needed for evaluation.
The scientific contract is [the master design](docs/AptaBench_Lite_Master_Design_Document.docx).
See [implementation evidence](IMPLEMENTATION_STATUS.md) and [scientific policy](docs/science_policy.md).

## Install and launch

Tested on Linux with **Python 3.12**. Windows/macOS instructions use the same Python
application and dependencies; those operating systems have not been exercised here.
Clone the Lite repository/implementation branch into its own directory. Research
workbooks are not included; `examples/` contains synthetic inputs only.

Windows PowerShell, from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Or double-click `launch.bat` after Python 3.12 is installed. It installs the pinned
dependencies if the local environment does not exist and starts the dashboard.
The terminal must remain open; Ctrl+C stops the server. Activation is unnecessary.

macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m streamlit run app.py
```

Open the local address printed by Streamlit (normally `http://localhost:8501`).
The server binds to loopback. This address works on the same computer only.
Installation requires package-download access; computation then runs offline.
`requirements.lock` pins the tested environment, including developer tools. Normal
operation does **not** execute tests or download a browser.

## Evaluate workbooks

1. Upload a gold `.xlsx` and extractor `.xlsx`, or select **Use synthetic example workbooks**.
2. Choose worksheets independently. Recognized historic column names are suggested;
   choose your actual headers for paper IDs, filenames, stable record IDs, significance,
   sequence and optional name. The preview shows the chosen data before evaluation.
3. For historic gold, use `aptamer_type` as significance (`significant_sequence` versus
   `non_significant_sequence`) and `sequence_status` as presence (`present`). For a
   single combined status column choose that column and configure its explicit labels.
   Blank/unknown labels are reported, never assumed significant.
4. Select **Structured list** for JSON/Python-literal lists of sequence dictionaries,
   with the configured sequence key (normally `sequence`). Select **One sequence per
   row** for ordinary tables, with optional same-row name and notes mappings.
   Independent `aptamer_name` lists are never paired by index.
5. Review source diagnostics, significant counts and attempted-paper item counts;
   click **Run evaluation**. Empty lists still declare an attempted paper. Absent papers
   are unattempted unless explicitly entered in the advanced processed-paper manifest.
6. Choose **All sequences / Matched only**, **Strict / Adaptive tolerant**, and
   **Whole string / Core matching**. These controls score the **same fixed associations**;
   they do not rematch. Core matching consumes the entire gold with only extractor
   terminal flanks free. Inspect any paper and any candidate, not only the top suggestion.

Only sequence evaluation is enabled. Pool and Kd need separate scientific specifications.
Paper linking uses exact paper ID/filename, then unique aliases stripping peripheral
whitespace and terminal `.pdf`. Configured artifact suffixes may be removed. There is
no title fuzziness, nucleotide-based linking or filename case folding.

## Interpret scores

An **association** establishes record correspondence. A **value pass** tests its bases.
A human-confirmed association can still fail every correctness criterion.
Adaptive edits use `max(1, min(4, isqrt(L // 9)))` for positive gold length `L`.
Only forward literal bases are scored: no T/U conversion, reverse complement or IUPAC wildcard.

For attempted, linked, scoreable significant golds, let G be gold records, E logical
predictions after strict canonical deduplication, M accepted links and T passing links.
All-sequences: TP=T, FP=E−T, FN=G−T; precision=T/E, recall=T/G, F1=2T/(E+G).
Extras may be real sequences outside the significant reference; FP is a **closed-world
reference convention**, not verified biological falsity. Pending identities have no TP.
Matched-only correctness is T/M, including human-confirmed bad sequences; recovery T/G
and accepted count remain visible. Empty denominators show N/A, never fabricated 100%.
Invalid significant references and unlinked/unattempted papers remain disclosed separately.

Unique canonical extractor duplicates are suppressed without deleting raw provenance.
Identical golds retain available raw extractor capacity and trigger identity review.
No physical extractor can be used twice. Green bases do not resolve ambiguous identity.

## Review, save and resume

Select a paper; **Resolve manual review** or enable correction actions. Golds are on
the left, extractor items on the right. Pick any eligible pair. The panel shows
source cells/list indexes, raw/canonical values, local names, alternatives and stored
alignment operations: green match, yellow indel/gap, red substitution, gray free flank.
Color is supplemented by operation labels and edit counts.

Enter reviewer identity and use:

- **Confirm association:** establish identity; never override sequence correctness.
- **Reject candidate:** reject only the selected edge; other candidates remain available.
- **Mark gold missing:** retain FN, resolve review outcome. Removing an existing link
  requires the explicit confirmation checkbox.
- **Leave unresolved:** record a note without creating a match.
- **Reassign explicitly:** review affected current links, check explicit confirmation,
  and enter a reason. One atomic transaction frees old endpoints and links the new pair.
- **Undo selected action:** append an undo event targeting a prior active action. An undo
  that makes dependent later actions invalid is rejected; undo dependent actions first.

Each successful action autosaves atomically in `.local/reviews/<run-id>.json`, with a
checksum, revision check, lock and prior-file `.bak`. The UI changes only after durable
save succeeds. Download **review state** for a portable backup. Reopen, upload identical
workbooks and mapping, and Run; the local state resumes automatically. On another machine,
use **Restore review-state JSON**. Hash/config/policy mismatches and conflicting histories
are rejected. To resume a different scientific input version, create a new evaluation;
there is no implicit migration. A checksum detects accidental corruption, not forgery or
researcher authentication. This is a **single-user** local app, not a shared review service.

If a process crashes leaving a `.lock`, stop all app instances, preserve the review JSON
and `.bak`, verify the store is idle, then remove the stale lock. Never remove an active
writer's lock. Keep backups before machine cleanup; clearing Streamlit session state alone
is not equivalent to deleting persisted review.

## Export and CLI/library use

Download a selectable three-tab Excel report, JSON audit, review state and mapping configuration from the app.
Excel offers Simple Summary (all eight score views, per-paper metrics and per-gold completion), Debug Log (accepted/missing records, all candidates and alignment traces), and Logistics (inputs, validation, review history, inventory and run provenance).
A browser controls the downloaded file's save location, not the Streamlit application. The full underlying audit is available in JSON. JSON includes all candidates, both automatic and
reviewed results, source hashes, mappings and policy versions. Alignment colors and counts
read the same stored trace as the dashboard; exporters do not run alignment. Excel's
32,767-character cell limit is explicitly marked if exceeded; full provenance is in JSON.
Reports are outputs, not editable statistical authorities or review-input spreadsheets.

```bash
.venv/bin/aptabench-lite --gold examples/gold.xlsx --extractor examples/extractor.xlsx --output-dir .local/my-run
# Optional: --config config.json --review review.json --population matched --tolerance strict --scope whole
```

The output directory must not contain existing `evaluation.xlsx`, `audit.json`, or
`review.json`; CLI refuses to overwrite them. Configuration JSON maps the fields in
`aptabench_lite.config.RunConfig`; download a configured example from the dashboard.

```python
from aptabench_lite.engine import evaluate
from aptabench_lite.scoring import compute_metrics
from aptabench_lite.exports import export_workbook
run = evaluate(gold_file="examples/gold.xlsx", extractor_file="examples/extractor.xlsx")
metrics = compute_metrics(run, population="all", tolerance="adaptive", sequence_scope="core")
excel_bytes = export_workbook(run, metrics)
```

## Verification and development

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

Browser tests use system Chromium or `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. Without a browser,
that test is explicitly skipped; use `python -m playwright install chromium` where network
policy permits. Core tests and Streamlit AppTest do not require a browser. Tests use only
synthetic inputs; an explicit developer profiling command can evaluate approved local files:

```bash
.venv/bin/python scripts/profile_run.py --gold /path/to/gold.xlsx --extractor /path/to/extractor.xlsx --output-dir .local/profile
```

`docs/acceptance.md` maps acceptance cases to executed evidence. No tests claim biological
identity guarantees. Unresolved repeated motifs, equivalent assignments, name contradictions,
ambiguous alphabets and identical-gold multiplicity intentionally abstain. The qualitative
identity boundaries deferred by the design need research-owner review before relaxation.

## Privacy and internal sharing

Share the approved source and installation instructions through the team's authorized
repository, not raw research workbooks or `.local` outputs. `.gitignore` excludes private
inputs, reports, environments and review state; only synthetic examples are included.
Uploaded data stays on the machine running this app. There are no LLM/analytics calls;
Streamlit telemetry is disabled. A remote host would receive uploaded bytes: do not expose
this unauthenticated local app on a public IP. Institutional hosting needs separately
approved authentication, access control, HTTPS, concurrency and retention design. No
public deployment is included or authorized. Clear private local files and caches when
required by the team's retention policy. Source workbooks are read-only and never rewritten.

Safety limits: 20 MiB upload, 100 MiB expanded XLSX, 10,000 rows per selected sheet,
500 headers, 100,000 characters/structured cell, depth 12, 1,000 items/cell, 2,000 nt/sequence,
4 million DP cells/comparison. Limit violations stop with a message; they never silently
skip hard comparisons. Missing/unsupported reference bases are unscoreable, not repaired.

## Practical review and optional Pool/Kd fields (feature branch)

Optional **Evaluate pool** and **Evaluate Kd** controls appear in the upload/mapping section.
Choose gold columns and matching extractor worksheets before **Run evaluation**.
The existing sequence alignment and scoring policy are unchanged. The sequence
review panel now starts with unresolved golds; optional Pool/Kd records have a separate
one-record-at-a-time **Review Pool / Kd** panel.

Pool is scored once per distinct annotated selection-library template per paper,
not once for each aptamer using it. Canonical pool-template equality is strict;
the pool type is displayed as an independent exact-match diagnostic. A single
unambiguous gold/extractor pool for a paper can be associated even when their
templates differ; the association then fails the value comparison.

Kd uses **one annotated Kd value per gold aptamer**, not a separate measurement table.
The extractor's `kd` worksheet is expected to contain structured entries with
`amount`, `unit` and optional aptamer `name` or `notes` with `Aptamer: <name>`.
Only named unique same-paper associations or a sole noncontradictory same-paper
gold/prediction pair are automatically linked. **Numerical closeness never
establishes identity**. Supported units: fM, pM, nM, uM, mM, M.
Comparison is exact after conversion to nM, then within a fixed **5% relative
error**. Ranges, inequalities, unknown units and nonpositive values cannot pass.
A manual identity confirmation never edits a measurement, so an incorrect number
remains incorrect.

For optional fields, the dashboard saves reviewer events under `.local/reviews/`,
recalculates the results after each action, allows undo, and supports review
backup export/import. An association or explicit missing outcome resolves its
review queue entry. Field totals use a closed-world reference convention; unmatched
predictions are **not verified biological false positives**. Pending means no
final identity/missing decision has been recorded.

The same **three-sheet Excel workbook** includes optional Pool/Kd metrics in
Simple Summary, field outcomes in Debug Log, and field mappings/review history
in Logistics. The JSON audit includes both sequence and optional-field automatic/effective results;
sequence review backup remains a separate download. To move field review between machines, use the Pool/Kd
review backup, with identical workbooks and mappings.

This feature branch needs verification on actual gold and extractor workbook schemas.
It remains a local, single-user review app; not a shared authenticated service.


## Recovery from a Pool/Kd Run that never finishes

A merged Pool-template validator could hang the entire server on an unsupported
character following a long DNA prefix. The repair preserves the accepted template
rules while eliminating that backtracking. Closing the browser alone does not stop
an already-running Streamlit process.

Stop the terminal running this app with Ctrl+C, update to the repaired code (or
`fix/dashboard-merged-regressions` while its merge is pending), and restart with
the platform-specific Streamlit command above. If Ctrl+C cannot stop the process,
terminate only the Python process running this Streamlit app using your operating
system's process manager. Do not delete `.local/reviews`: existing review backups
are preserved. An existing process must restart to load the fix.


## Private-data performance troubleshooting

The full research workbooks are **never** stored in Git. Keep all locally supplied
`gold.xlsx` and `extractor.xlsx` files under the ignored `inputs/` directory,
outside `examples/` and `tests/fixtures/` (which intentionally contain tracked
synthetic fixtures). The repository ignores `*.xlsx` except its two synthetic
fixture directories. Do not force-add private spreadsheets or paste their raw
contents into issues, CI logs, or pull requests.

The Pool/Kd performance fix replaces a potentially exponential-time regular
expression in pool-template validation with a linear-time tokenization pattern.
This is a performance/security hardening change, not a relaxation of the
scientific matching rules.

Excel reports are now prepared **only** when **Prepare Excel report** is clicked.
After a manual review action or scoring option change, prepare again before
downloading. This avoids reconstructing large alignment-rich workbooks during
every Streamlit interaction.

To validate a hang on real inputs, compare sequence-only / +Pool / +Kd /
+Pool+Kd wall times and isolate workbook reading, sequence evaluation, field
normalization, review restoration, dashboard rendering, and report generation.
Record only aggregate counts and durations. Do not upload the underlying
research datasets to GitHub.


To verify a reported hang using only explicitly supplied private workbooks:

```bash
.venv/bin/python scripts/verify_supplied_workbooks.py --gold inputs/gold.xlsx --extractor inputs/extractor.xlsx --output-dir .local/supplied-verification
APTABENCH_TEST_GOLD=/absolute/path/gold.xlsx APTABENCH_TEST_EXTRACTOR=/absolute/path/extractor.xlsx .venv/bin/python -m pytest -q tests/test_uploaded_workbooks.py
```

These integration checks have no example-workbook fallback. They exercise all
four field configurations, private report exports, review roundtrips and actual
browser reloads without rewriting source files. Input paths must be supplied;
outputs remain local. Prepare Excel explicitly after a scoring/review change.


### Full-input performance verification

See [the anonymized benchmark](docs/performance-benchmark.md) for phased timings,
cache verification and the bounded pre-fix reproduction on the supplied full inputs.
The optional Pool/Kd parse cache reuses source bytes and mapping/run identities;
review decisions are restored separately. The Run spinner now identifies sequence
computation, optional-field loading and review restoration as separate phases.
Normal score/review reruns do not read workbooks or run sequence alignment, and
Excel remains an explicit **Prepare Excel report** action.

`benchmark_real_inputs.py` requires explicit private paths and never falls back to
examples. Optional live tracing is disabled unless `APTABENCH_PERFORMANCE_LOG` is
set; trace files contain timing/count metadata only and belong under `.local/`.
