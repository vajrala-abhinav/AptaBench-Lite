# Acceptance evidence map

The complete master is preserved unchanged in DOCX; extracted text includes all 25
sections and 19 tables, and figures 0–2 preserve the three diagrams. SHA256 is recorded
in IMPLEMENTATION_STATUS.md. Tests below are executable evidence, not biological validation.

| Requirement | Evidence |
|---|---|
| S01 unique exact whole | test_engine::test_S01_strict |
| S02/S04 exact flanked core | test_S02_S04_unique_core |
| S03 40/84 context | test_S03_40_84 |
| S05/S06 one edit in 8 nt | test_S05_S06_one_edit_eight |
| S07/S08 indels | test_alignment::test_edits; exhaustive fitting oracle |
| S09 outside budget | test_S09_outside; test_budget_exact (lengths 1–10,000) |
| S10/S29 repeated motif/placements | test_S10_S29_repeated; exhaustive interval-count oracle |
| S11/S13/S14/S18 multiplicity/dedup | test_S11_S13_S14_multiplicity; one-to-one review checks |
| S12/S20 near-identical ambiguity | test_S12_S20_ambiguous_near_gold |
| S15 contradictory duplicate names | test_S15_duplicate_names |
| S16/S18 local names/conflicts | test_S16_S18_names |
| S17 separate name inventory | test_readers::test_independent_name_inventory_ignored |
| S19 conditional scope tie-break | test_S19_conditional_global |
| S21 runner-ups/whole-paper assignment | test_S21_context_runnerup; test_solver brute-force oracle |
| S22/S23 out-of-tolerance/no forced match | test_S09_outside; test_significant_only_no_forcing |
| S24/S25 empty/unattempted | test_S24_S25_empty_unattempted |
| S26 ambiguous alias | test_S26_alias_collision |
| S27 forward literal T/U/RC | test_S27_literal_TU_RC |
| S28 unsupported chemistry/Unicode/gaps | test_alignment::test_normalization |
| S30 row/cache invariance | test_S30_permutation_and_cache |
| M01/M02 exact worked metrics | test_M01_M02_numerical_contract |
| M03 pending never TP | test_S12_S20_ambiguous_near_gold; worked counts |
| M04 confirmed within tolerance | test_M04_confirm_within_tolerance_changes_only_overlay |
| M05 confirmed incorrect sequence | test_M05_bad_sequence_confirmation |
| M06/M07/M08/M09 reject/missing/reassign/undo | test_M06_M07_M08_M09 |
| M10 replay integrity | test_M10_checksum_fingerprint_concurrency; invalid schema tests |
| M11/M12/M13/M14 zero/invalid denominators | empty/unattempted, empty significant, no matches, invalid inventory tests |
| M15 shared traces/colors | test_M15_exports_trace_injection; test_html_excel_exact_colors_and_trace |
| M16 scoring toggles never rematch | test_M16_toggle_invariance (alignment patched to fail if called) |
| M17 original/effective separation | incorrect confirmation test; browser audit download assertion |
| M18 duplicate physical capacity | multiplicity fixture; review one-to-one validation |
| Safe configurable ingestion | test_readers (custom names/sheets/simple tables, literal parser, malformed inventory, header/ID errors) |
| Installed CLI roundtrip | test_entrypoints::test_actual_cli_independent_entrypoint |
| Reference parity | test_frozen_reference_alignment_parity: 14 synthetic global/core cases, source hash recorded |
| Streamlit functional actions | test_ui actual AppTest, including conflict and undo |
| Actual browser upload/review/export/resume | test_browser_e2e, system Chromium + real Streamlit HTTP/WebSocket |
| Clean install independence | isolated .local/clean-source and .local/clean-venv, original aptabench absent |
| Representative run | .local/representative/profile.json; 248 gold rows, 308 raw extractor items; source hashes unchanged |

## Design-deferred items

Pool/Kd scoring, modification/IUPAC wildcard/RC equivalence and authenticated shared
hosting are outside the sequence-module scope. Public deployment is prohibited.
No arbitrary minimum sequence length, confidence percentage or completion margin was added.
Research-owner review is needed before relaxing the conservative §24 identity fallback.
Windows/macOS commands are documented but require those hosts for native verification.
