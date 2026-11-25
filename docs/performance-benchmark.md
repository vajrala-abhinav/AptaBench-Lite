# Full-input Pool/Kd performance verification

Branch: `fix/pool-kd-performance-privacy`. No merge is authorized or performed.
The preliminary safe regex and explicit Excel-preparation behavior are preserved.
No scientific metric, association, tolerance, or one-to-one rule changed in this work.

## Inputs and method

Only the two supplied workbooks were used for real-data reproduction and timing.
Their bytes remained unchanged. Private files, histories, signatures and evidence
are ignored under `.local/`; none are included in this PR. Source SHA256 prefixes:
**gold `a015e5b896c2…`**, **extractor `6986787019d5…`**.

The full preview was verified: **248 gold rows / 116 significant records /
6,309 significant bases / 44 linked attempted papers / 308 raw sequence items**.
Required gold and extractor sheet/column mappings were validated against those files.
The supplied gold has **243 nonblank Pool entries** (246 non-null cells, three
whitespace-only); the preliminary issue's count of 245 was not reproduced on this copy.
All 243 nonblank entries were included in the validation scan.

Python 3.12, this managed Linux machine. Two cold repetitions per mode, with the
alignment cache cleared before each CLI run. Browser measurements separately use
normal warmed Streamlit caches. Measurements are observations, not runtime promises.

## Before/after: the actual freeze

| Check on the supplied gold | Before | After |
|---|---:|---:|
| Pool-validation scan | Did not finish within **0.250 s**; child killed safely | **0.00170 s** for all 243 nonblank entries |
| Completed scan | No | Yes: 178 accepted / 65 retained as unsupported |
| Quantified improvement | Completion time unavailable | **>147×** versus the canceled 250 ms lower bound |
| Excel on ordinary score/review reruns | Built eagerly before the preliminary fix | **Zero builds**; explicit preparation required |

A second bounded probe ran the legacy validator inside actual `load_fields` after
sequence evaluation had finished. It also timed out at 250 ms, before Excel began;
this verifies the eligible-record pipeline rather than only a standalone raw scan.

The old-regex child loads inputs before signaling readiness; Python startup and
XLSX parsing do not consume the timed 250 ms window. No raw entry is printed.
We did not wait minutes to obtain a complete pre-fix time or fabricate one.

The original spinner enclosed **sequence evaluation, `load_fields`, and review
restoration together**. The reproduced stall is inside Pool normalization during
`load_fields`, after sequence evaluation. Excel generation was outside that spinner:
it was a separate rerun-latency problem, not the cause of this observed spinner.
The UI now labels the sequence, optional-field and review-restore phases separately.

## Post-fix cold-run phase timings

Seconds, mean of two runs on identical full inputs:

| Mode | XLSX parsing | Sequence compute* | Pool normalize | Kd normalize | Review restore | Selected scoring | Excel export |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sequence | 0.0967 | 3.8181 | — | — | 0.00136 | 0.00137 | 0.5217 |
| Sequence + Pool | 0.1253 | 3.8607 | 0.00079 | — | 0.00289 | 0.00139 | 0.5191 |
| Sequence + Kd | 0.1315 | 3.9513 | — | 0.00200 | 0.00507 | 0.00347 | 0.5561 |
| Sequence + Pool + Kd | 0.1368 | 3.8288 | 0.00077 | 0.00186 | 0.00849 | 0.00574 | 0.5101 |

\* Sequence compute is the measured evaluation stage minus its measured XLSX parsing.
Parsing includes workbook construction and streamed row reads; initial file-byte reads
are outside these timings. Normalization and review phases can contain nested scoring;
columns are not an additive total. Restore uses local verification-only histories
created from real record IDs and immediately undone, not an unprovided PI history.
The scoring column is one selected population; Excel additionally aggregates all eight
views. Repeatability/count/trace reconciliation and opening the resulting report add
verification overhead not represented as a normal user Run phase.

## Browser rendering and cache proof

Actual Chromium upload of the two supplied files; timing-only server tracing enabled:

| Mode/action | Browser Run wall time | Backend rendering excluding Run/export | New alignment computations |
|---|---:|---:|---:|
| Sequence, cold | 5.629 s | 0.327 s | 1,281 |
| Add Pool, cached sequence | 1.105 s | 0.212 s | 0 |
| Add Kd, cached sequence | 0.693 s | 0.216 s | 0 |
| Pool + Kd, cached sequence | 0.648 s | 0.225 s | 0 |
| Repeat identical Run | — | 0.197 s | 0 |
| Change scoring view | — | 0.248 s | 0 |
| Prepare Excel explicitly | — | 0.237 s excluding export | 0 |
| Reload and restore saved field history | — | 0.341 s | 0 |

Repeat Run, score toggle, explicit export and restored-history reruns also had
**zero XLSX parsing calls**. Optional fields cache by source bytes, run identity and
field mappings. Review restoration remains outside that cache, so fresh histories
are loaded without rereading inputs. Input/mapping changes still require a new run.

Prepared Excel is unavailable after a scoring change or review action until prepared
again. The downloaded workbook has exactly **Simple Summary / Debug Log / Logistics**.
Field review save, undo, reload/resume and backup import were exercised successfully;
sequence review roundtrip/undo was checked through the library and regression suite.

## Verification and reproduction

- Starting branch suite: **59 passed**.
- Full Python 3.12 suite with the real-input environment variables: **63 passed in
  44.87 s**, including standard UI/browser regressions and both opt-in real-input checks.
- Subsequent focused checks for default-off tracing/privacy assertions: **3 UI/timing
  tests passed**, and the supplied-file cache check passed separately.
- Internal scientific signatures match starting commit `65c801a` for all four modes,
  all eight sequence scoring views, records, traces, associations and field results.
- Two cold repetitions per mode matched exactly; input SHA256s stayed unchanged.
- `pip check`: no broken requirements. No new dependencies.

From the repository root, supplying private local paths explicitly:

```bash
.venv/bin/python scripts/benchmark_real_inputs.py \
  --gold inputs/gold.xlsx --extractor inputs/extractor.xlsx \
  --output-dir .local/benchmark --repeats 2 --legacy-timeout 0.25

APTABENCH_TEST_GOLD="$PWD/inputs/gold.xlsx" \
APTABENCH_TEST_EXTRACTOR="$PWD/inputs/extractor.xlsx" \
  .venv/bin/python -m pytest -q
```

Unit/regression fixtures are synthetic; all reported full-input timings and browser
checks use the supplied pair. CI receives no private workbooks and skips opt-in tests
when those explicit paths are absent. Do not paste full result objects or private
artifacts into GitHub. The benchmark emits only aggregate counts, durations, status
categories, lengths and truncated source fingerprints.

Developer-only live timing trace (disabled by default):

```bash
APTABENCH_PERFORMANCE_LOG=.local/runtime-timings.jsonl \
  .venv/bin/python -m streamlit run app.py
```

The trace stores only stage call counts/durations, completion flags and review revision
counts. It captures no widget values, names, sequences, raw diagnostics or credentials.
Nested stage durations are inclusive; do not sum them as independent wall time.
