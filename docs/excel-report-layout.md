# Six-sheet Excel report

This report-only revision supersedes the original three-tab presentation. Scientific
results, Pool/Kd rules, sequence association, scoring and review replay are unchanged.
The worksheet selector defaults to all six sheets; any nonempty subset is supported
and always appears in the canonical order below.

| Previous section | New location |
|---|---|
| Simple Summary: eight overall views | Simple Summary: A, overall metrics; D, supporting counts |
| Simple Summary: per-paper eight-view table | Per-Paper Results: selected view first (one row per paper), full comparison below |
| Simple Summary: per-gold completion / Significant_Status | Matched Pairs for accepted pairs; Debug Log for unmatched outcomes; Record Inventory `significant` and `scope_status` for all golds |
| Debug Log: accepted gold outcome summaries | Matched Pairs: effective accepted associations, including incorrect human-confirmed sequences |
| Debug Log: unmatched gold outcomes and all candidate comparisons | Debug Log: unresolved/missing outcomes then full candidate audit, including selected candidates |
| Debug Log: Pool/Kd field comparisons | Debug Log: reviewed field comparisons, with automatic extractor IDs and full field result |
| Logistics: run IDs, hashes, configuration, timing, paper linkage, validation | Logistics & Review |
| Logistics: sequence review history | Logistics & Review: append-only history, missing/rejected state, original automatic associations |
| Logistics: Pool/Kd mappings, warnings and event history | Logistics & Review: Pool/Kd input mappings and warnings |
| Logistics: gold, raw extractor and duplicate inventories | Record Inventory: all gold/raw records, separate logical predictions, duplicate groups and normalization provenance |
| Simple Summary: optional field scores | Simple Summary: concise independent Pool/Kd table (Pool remains library-level) |

Existing diagnostic column names are retained where practical (`tolerant_core` and
`tolerant_whole` mean adaptive pass; `budget` is the adaptive edit budget).
`core_completion_%` and `whole_completion_%` remain the original 0–100 values, shown
with a percentage sign. Metric fractions retain their original 0–1 values with Excel
percentage formatting. No Excel formulas redefine metrics. `TP/FP/FN` are explicitly
population-specific; matched-only errors remain `M−T`, while closed-world errors use
`E−T` and `G−T`. Matched-only P/R/F1 are conditional pair correctness. TN is undefined.

The summary has no paper or record inventories. Its definitions and warnings explain
why a closed-world FP is not a verified hallucination. Pending scoreable golds are
provisional non-successes, and identity confirmation never overrides nucleotide
correctness. Blank ratios indicate undefined denominators, not zero measurements.

Accepted-pair alignments retain colored core traces and add colored whole traces.
The full candidate audit retains all plain alignment strings and colors selected traces;
this avoids per-nucleotide rich-text overhead for every unselected competitor.
Excel tables provide filters on each populated record section; headers freeze and
repeat for printing. Green/red show sequence pass/fail and yellow flags review status.
Both core and whole nucleotide traces use the same stored operations as the engine:
green matches, yellow indels, red substitutions and gray ignored flanks. For long
strings (>3,000 characters), plain trace text replaces rich formatting. Excel's
32,767-character limit is marked explicitly, with the full value in JSON audit.

Report generation stays on demand. The existing prepared-report identity includes
sequence review events, field review events, scoring controls, field fingerprints and
worksheet selection. Changing these hides the stale download until a fresh report is
requested. Export does not evaluate, rematch or align sequences. JSON schema and its
scientific audit remain unchanged.

Generate a safe example without any research inputs:

```bash
.venv/bin/python scripts/make_report_example.py
```

Windows: `.venv\Scripts\python.exe scripts\make_report_example.py`.
The output is `.local/report-redesign/synthetic-six-sheet.xlsx` (ignored, not committed).
Use `--output <new-path.xlsx>` to choose another location. The script refuses to
overwrite an existing file. It includes exact/core matches, an incorrect human-confirmed
association, an unresolved gold, duplicates, excluded gold, independent Pool/Kd metrics
and a field-review event. Only the generator and synthetic regression expectations are
committed; private workbooks and evaluation evidence stay ignored.

## Verification observations (November 25, 2026)

Pre-refactor baseline: main `d535472` (already contains the Pool/Kd performance fixes).
The regression fixture freezes all eight calculated metric dictionaries from that
baseline, rather than comparing only display strings. New tests also verify effective
incorrect confirmations, unresolved outcomes, full candidate IDs, raw/logical/duplicate
inventories, optional-field review history and on-demand report invalidation.

The supplied private inputs were available for this task. Four reporting modes were
checked on the same full inputs; all audits and eight-view numerical results matched
the baseline. All 50 accepted associations and 606 stored candidates remained present.
The 248-row gold input's significant-only preview is unchanged. Scientific evaluation
modules were not edited. Both source workbook hashes stayed unchanged.

One local export observation per mode, Python 3.12 (seconds; not runtime promises):

| Optional fields | Previous report | Six-sheet report | New alignment calls | Summary rows |
|---|---:|---:|---:|---:|
| None | 0.630 | 0.965 | 0 | 45 |
| Pool | 0.555 | 1.033 | 0 | 50 |
| Kd | 0.556 | 0.926 | 0 | 50 |
| Pool + Kd | 0.602 | 0.918 | 0 | 51 |

The small increase is report formatting/table/audit projection cost, paid only on
explicit preparation. Normal score/review reruns retain their existing caches.
Private report files and evidence remain ignored. Excel XML, table filters, frozen
panes, number formats and rich text were read back with openpyxl. Native Microsoft
Excel desktop rendering was not available in the Linux cloud environment.
