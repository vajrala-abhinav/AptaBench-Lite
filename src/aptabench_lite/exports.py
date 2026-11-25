"""Excel and JSON projections of canonical results; no scientific computation."""
from dataclasses import asdict
from io import BytesIO
import json
import xlsxwriter
from .performance import timed
from .models import base_run,associations,ReviewedRun
from .scoring import compute_metrics,paper_status,CAVEAT
from .presentation import COLORS


def audit_dict(value,metrics=None,field_data=None,field_events=()):
    run=base_run(value)
    if metrics is not None:
        expected=compute_metrics(value,metrics['population'],metrics['tolerance'],metrics['sequence_scope'])
        if metrics!=expected:raise ValueError('Metrics do not match canonical result/view')
    result = {'schema_version':'lite-audit-1','run':asdict(run),'metadata':json.loads(run.metadata_json),
            'configuration':json.loads(run.config_json),'selected_metrics':metrics or compute_metrics(value),
            'automatic_metrics':{f'{pop}/{tol}/{scope}':compute_metrics(run,pop,tol,scope) for pop in ('all','matched') for tol in ('strict','adaptive') for scope in ('whole','core')},
            'effective_metrics':{f'{pop}/{tol}/{scope}':compute_metrics(value,pop,tol,scope) for pop in ('all','matched') for tol in ('strict','adaptive') for scope in ('whole','core')},
            'effective_associations':[asdict(a) for a in associations(value)],
            'review_events':[asdict(e) for e in value.events] if isinstance(value,ReviewedRun) else [],
            'marked_missing':list(value.missing) if isinstance(value,ReviewedRun) else [],
            'rejected_pairs':list(value.rejected) if isinstance(value,ReviewedRun) else [],'methodology':CAVEAT}
    if field_data is not None:
        from .field_eval import field_results
        from .field_review import replay, fingerprint
        if field_data["run_id"]!=run.run_id:raise ValueError("Field data belongs to a different evaluation run")
        result["optional_fields"]={"fingerprint":fingerprint(field_data),"inputs":field_data,
            "automatic_results":field_results(field_data),"effective_results":replay(field_data,field_events),
            "review_events":list(field_events)}
    return result


def export_audit(value,metrics=None,field_data=None,field_events=()):
    return json.dumps(audit_dict(value,metrics,field_data,field_events),ensure_ascii=False,indent=2,default=str,allow_nan=False).encode()



REPORT_SHEETS = (
    "Simple Summary", "Per-Paper Results", "Matched Pairs", "Debug Log",
    "Logistics & Review", "Record Inventory",
)

COUNT_DEFINITIONS = (
    ("G", "Eligible, scoreable significant gold sequence records in attempted papers"),
    ("E", "Logical extractor sequence predictions after the existing duplicate-handling policy"),
    ("M", "Accepted one-to-one gold–extractor associations, including effective manual-review decisions"),
    ("T", "Accepted associations passing the selected strict/adaptive and core/whole sequence criterion"),
    ("TP", "Correctly recovered significant gold records under the chosen criterion"),
    ("FP", "Extractor predictions not credited as correct significant-gold recoveries under closed-world scoring"),
    ("FN", "Significant gold records not correctly recovered under closed-world scoring"),
)

CLOSED_WORLD_EXPLANATION = (
    "AptaBench Lite evaluates extracted sequences against a reference containing eligible significant gold sequences only. "
    "Extractor predictions that do not correctly recover a sequence in this reference are counted as false positives under the closed-world scoring convention.",
    "A closed-world false positive is not necessarily a biologically incorrect or hallucinated sequence. "
    "It may represent a legitimate non-significant aptamer sequence excluded from the gold reference.",
    "Therefore, closed-world precision and F1 measure agreement with the significant-reference set, not the extractor’s overall biological accuracy.",
    "Results remain provisional while manual-review decisions are pending. True negatives are not defined for this sequence-retrieval evaluation.",
)


@timed("excel_export")
def export_workbook(value, metrics=None, sheets=None, field_data=None, field_events=()):
    """Six-sheet projection of fixed results. Reuses stored traces; never aligns.

    Optional subsets always follow REPORT_SHEETS order. The JSON audit is unchanged.
    """
    run = base_run(value)
    metrics = metrics or compute_metrics(value)
    view = tuple(metrics[k] for k in ("population", "tolerance", "sequence_scope"))
    if metrics != compute_metrics(value, *view):
        raise ValueError("Metrics do not match canonical result/view")
    requested = tuple(REPORT_SHEETS if sheets is None else sheets)
    if not requested or len(set(requested)) != len(requested) or any(s not in REPORT_SHEETS for s in requested):
        raise ValueError("Choose one or more distinct supported report sheets")
    selected = tuple(s for s in REPORT_SHEETS if s in requested)
    field_scores = None
    if field_data is not None:
        from .field_review import replay
        if field_data["run_id"] != run.run_id:
            raise ValueError("Field data belongs to a different evaluation run")
        field_scores = replay(field_data, field_events)

    out = BytesIO()
    wb = xlsxwriter.Workbook(out, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    wb.formats[0].set_font_name("Calibri")
    wb.formats[0].set_font_size(11)
    body = wb.add_format({"text_wrap": True, "valign": "top"})
    header = wb.add_format({"bold": True, "bg_color": "#DDE9F4", "text_wrap": True, "valign": "top"})
    section = wb.add_format({"bold": True, "bg_color": "#B8CEDF", "font_size": 12})
    note = wb.add_format({"font_color": "#475569", "text_wrap": True, "valign": "top"})
    warning = wb.add_format({"bold": True, "bg_color": "#FFF2CC", "text_wrap": True})
    percentage = wb.add_format({"num_format": "0.0%", "valign": "top"})
    # Completion() has always returned a 0–100 value; retain its exact stored number.
    completion = wb.add_format({"num_format": '0.0"%"', "valign": "top"})
    pass_style = wb.add_format({"bg_color": "#DCFCE7", "font_color": "#166534"})
    fail_style = wb.add_format({"bg_color": "#FEE2E2", "font_color": "#991B1B"})
    review_style = wb.add_format({"bg_color": "#FEF3C7", "font_color": "#854D0E"})
    mono = wb.add_format({"font_name": "Consolas", "font_size": 10})
    color_formats = {op: wb.add_format({"font_color": color, "font_name": "Consolas"})
                     for op, color in {"MATCH": "#166534", "INSERTION": "#854D0E",
                     "DELETION": "#854D0E", "SUBSTITUTION": "#991B1B",
                     "FREE_EXTRACTOR_FLANK": "#64748B"}.items()}
    worksheets = {}
    for name in selected:
        ws = wb.add_worksheet(name)
        worksheets[name] = ws
        ws.hide_gridlines(2)
        ws.set_default_row(30)
        ws.set_column(0, 59, 19, body)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.set_footer('&LAptaBench Lite | private research report&RPage &P of &N')
    table_index = 0
    frozen = set()

    def safe(v):
        if isinstance(v, (dict, list, tuple)):
            v = json.dumps(v, default=str, ensure_ascii=False, allow_nan=False)
        if v is None:
            return ""
        if isinstance(v, str) and len(v) > 32767:
            return v[:32670] + " [TRUNCATED: full value in audit.json]"
        return v

    def table(ws, row, title, headers, rows):
        """Independent filterable tables; header-only empty sections stay readable."""
        nonlocal table_index
        ws.merge_range(row, 0, row, max(1, len(headers)-1), title, section)
        rows = list(rows)
        columns = []
        for col, name in enumerate(headers):
            fmt = percentage if name in {"precision", "recall", "F1", "matched_correctness", "significant_recovery",
                                       "closed_world_precision", "closed_world_recall", "closed_world_F1", "matched_pair_correctness"} else completion if name.endswith("_%") else body
            columns.append({"header": name, "header_format": header, "format": fmt})
            ws.write(row+1, col, name, header)
            if name.endswith("_%") or name in {"precision", "recall", "F1", "matched_correctness", "significant_recovery"}:
                ws.set_column(col, col, 18, fmt)
            if any(key in name for key in ("source", "raw", "canonical", "aligned", "reasons", "definition", "interpretation")):
                ws.set_column(col, col, 36)
        ws.set_row(row+1, 44)
        if rows:
            table_index += 1
            ws.add_table(row+1, 0, row+1+len(rows), len(headers)-1,
                         {"name": f"ReportTable{table_index}", "columns": columns,
                          "data": [[safe(v) for v in record] for record in rows], "style": "Table Style Medium 2"})
            for col, name in enumerate(headers):
                if name in {"strict_core", "tolerant_core", "strict_whole", "tolerant_whole", "exact", "tolerant"}:
                    for val, style in ((True, pass_style), (False, fail_style)):
                        ws.conditional_format(row+2, col, row+1+len(rows), col,
                                              {"type": "cell", "criteria": "==", "value": val, "format": style})
                if "status" in name or name == "pending":
                    ws.conditional_format(row+2, col, row+1+len(rows), col,
                        {"type": "text", "criteria": "containing", "value": "REVIEW", "format": review_style})
        if ws.name not in frozen:
            ws.freeze_panes(row+2, 1)
            ws.repeat_rows(row+1)
            frozen.add(ws.name)
        return row+len(rows)+3

    def paragraph(ws, row, text, style=note, height=32):
        ws.merge_range(row, 0, row, 12, text, style)
        ws.set_row(row, height)
        return row+1

    def rich(ws, row, col, trace, text):
        if not text:
            return
        if len(text) > 3000:
            ws.write(row, col, safe(text), mono)
            return
        pieces = []
        for ch, op in zip(text, trace.operations):
            pieces.extend((color_formats[op], ch))
        if len(text) > 1:
            ws.write_rich_string(row, col, *pieces, mono)
        else:
            ws.write(row, col, text, color_formats[trace.operations[0]])

    views = [(p, t, s) for p in ("all", "matched") for t in ("strict", "adaptive") for s in ("core", "whole")]
    overall = {v: compute_metrics(value, *v) for v in views}
    metric_headers = ["population", "tolerance", "scope", "precision", "recall", "F1",
                      "significant_recovery", "matched_correctness", "selected_view", "interpretation"]

    def metric_row(v, m):
        return [*v, m["precision"], m["recall"], m["f1"], m["significant_recovery"],
                m["matched_correctness"], v == view,
                "Closed-world significant-reference agreement" if v[0] == "all" else "Conditional matched-pair correctness: P/R/F1 = T/M"]

    if "Simple Summary" in selected:
        ws = worksheets["Simple Summary"]
        ws.set_column(0, 12, 17)
        row = paragraph(ws, 0, "AptaBench Lite | overall significant-reference evaluation", section)
        row = paragraph(ws, row, f"Selected configuration: {('All sequences' if view[0] == 'all' else 'Matched only')} / {view[1].title()} / {view[2].title()} | {'PROVISIONAL — review pending' if metrics['provisional'] else 'No pending scoreable gold review'}", warning)
        row = table(ws, row, "A | ALL EIGHT SCORING VIEWS — OVERALL", metric_headers,
                    [metric_row(v, overall[v]) for v in views])
        row = paragraph(ws, row, "B | Understanding closed-world scoring", section)
        row = paragraph(ws, row, "Closed-world FP does not mean verified hallucination.", warning)
        for text in CLOSED_WORLD_EXPLANATION:
            row = paragraph(ws, row, text, height=38)
        row = paragraph(ws, row, "C | COUNT DEFINITIONS", section)
        ws.write(row, 0, "symbol", section)
        ws.merge_range(row, 1, row, 12, "definition", section)
        row += 1
        for symbol, definition in COUNT_DEFINITIONS:
            ws.write(row, 0, symbol, body)
            ws.merge_range(row, 1, row, 12, definition, body)
            row += 1
        row = paragraph(ws, row, "T is not shorthand for tolerant matching: T counts passing accepted associations.")
        row = table(ws, row, "D | SUPPORTING COUNTS — FP/FN ARE POPULATION-SPECIFIC",
                    ["population", "tolerance", "scope", "G", "E", "M", "T", "TP", "FP", "FN", "pending", "count_basis"],
                    [[*v, *[overall[v][k] for k in ("G", "E", "M", "T", "TP", "FP", "FN", "pending_gold")],
                      "Closed-world: E−T / G−T" if v[0] == "all" else "Conditional pair errors: M−T / M−T"] for v in views])
        for text in (
            "All sequences / Closed-world: TP = T; FP = E − T; FN = G − T; Precision = T/E; Recall = T/G; F1 = 2T/(E + G).",
            "An accepted association failing the selected nucleotide criterion contributes one FP and one FN. An unmatched extractor contributes one closed-world FP; an unrecovered gold contributes one FN.",
            "Unresolved gold receives no TP credit. Human confirmation establishes association identity, not sequence correctness. Accepted associations remain one-to-one.",
            "Matched only uses M: existing precision, recall and F1 each equal T/M (conditional matched-pair correctness). Its FP/FN columns are conditional pair errors, not closed-world confusion counts. Recovery remains T/G.",
            "TN: undefined / not enumerated. Empty denominators are blank; no biological true-negative classification is implied.",
        ):
            row = paragraph(ws, row, text, height=38)
        if field_scores is not None:
            row = table(ws, row, "POOL AND KD | EFFECTIVE FIELD SCORES",
                        ["field", "gold", "predictions", "associations", "passing", "pending_review",
                         "closed_world_precision", "closed_world_recall", "closed_world_F1", "matched_pair_correctness"],
                        [[kind, *[field_scores[kind][k] for k in ("G", "E", "M", "T", "pending", "precision", "recall", "f1", "matched_correctness")]]
                         for kind in ("pool", "kd") if field_scores[kind]["gold"] or field_scores[kind]["predictions"]])
            paragraph(ws, row, "Pool is a library-level attribute; Kd is an independent field evaluation. These counts do not enter sequence metrics.")
        ws.print_area(0, 0, ws.dim_rowmax, 12)

    if "Per-Paper Results" in selected:
        ws = worksheets["Per-Paper Results"]
        row = table(ws, 0, "SELECTED SCORING VIEW | ONE ROW PER PAPER",
                    ["paper_id", "attempted", "review_status", *metric_headers, "G", "E", "M", "T", "TP", "FP", "FN", "pending"],
                    [[p.id, p.attempted, paper_status(value, p), *metric_row(view, (m := compute_metrics(value, *view, paper_id=p.id))),
                      *[m[k] for k in ("G", "E", "M", "T", "TP", "FP", "FN", "pending_gold")]] for p in run.papers])
        table(ws, row, "ALL EIGHT SCORING VIEWS | PER-PAPER COMPARISON",
              ["paper_id", "status", *metric_headers, "G", "E", "M", "T", "TP", "FP", "FN", "pending"],
              [[p.id, paper_status(value, p), *metric_row(v, (m := compute_metrics(value, *v, paper_id=p.id))),
                *[m[k] for k in ("G", "E", "M", "T", "TP", "FP", "FN", "pending_gold")]] for p in run.papers for v in views])

    cm = {c.id: c for c in run.candidates}
    em = {e.id: e for e in run.extractors}
    gm = {g.id: g for g in run.gold}
    associated = {a.gold_id: a for a in associations(value)}
    original = {a.gold_id: a for a in run.automatic}
    decisions = {d.gold_id: d for d in run.decisions}
    missing = set(value.missing) if isinstance(value, ReviewedRun) else set()
    rejected = set(value.rejected) if isinstance(value, ReviewedRun) else set()
    pair_headers = ["row_type", "paper_id", "gold_id", "extractor_id", "selected", "auto_selected",
                    "association_status", "gold_name", "extractor_name", "gold_raw", "extractor_raw",
                    "gold_canonical", "extractor_canonical", "core_edits", "whole_edits", "budget",
                    "core_completion_%", "whole_completion_%", "strict_core", "tolerant_core", "strict_whole", "tolerant_whole",
                    "name_support", "name_conflict", "viable", "candidate_stage", "candidate_reasons", "gold_source", "extractor_source",
                    "core_aligned_gold", "core_aligned_extractor", "core_operations", "whole_aligned_gold", "whole_aligned_extractor", "whole_operations",
                    "core_optimal_intervals", "whole_optimal_intervals", "candidate_id", "association_reasons", "automatic_decision",
                    "automatic_reasons", "review_status", "rejected_pair", "gold_length", "extractor_length", "core_counts", "whole_counts",
                    "core_trace_metadata", "whole_trace_metadata"]

    def candidate_row(c, row_type):
        g, e = gm[c.gold_id], em[c.extractor_id]
        a, auto = associated.get(g.id), original.get(g.id)
        chosen = bool(a and a.candidate_id == c.id)
        decision = decisions.get(g.id)
        return [row_type, g.paper_id, g.id, e.id, chosen, bool(auto and auto.candidate_id == c.id),
                a.origin if chosen else "CANDIDATE_ONLY", g.name, e.name, g.sequence.raw, e.sequence.raw,
                g.sequence.canonical, e.sequence.canonical, c.core.distance, c.whole.distance, c.budget,
                c.core.completion(), c.whole.completion(), c.strict_core_pass, c.adaptive_core_pass,
                c.strict_whole_pass, c.adaptive_whole_pass, c.name_support, c.name_conflict, c.viable, c.stage,
                c.reasons, asdict(g.source), asdict(e.source), c.core.aligned_gold, c.core.aligned_extractor, c.core.operations,
                c.whole.aligned_gold, c.whole.aligned_extractor, c.whole.operations,
                c.core.optimal_interval_count, c.whole.optimal_interval_count, c.id,
                a.reasons if chosen else (), decision.status if decision else "", decision.reasons if decision else (),
                "HUMAN_CONFIRMED" if chosen and a.origin == "MATCHED_HUMAN" else "EFFECTIVE_ACCEPTED" if chosen else "REJECTED_PAIR" if (g.id, e.id) in rejected else "NOT_SELECTED",
                (g.id, e.id) in rejected, len(g.sequence.canonical or ""), len(e.sequence.canonical or ""),
                c.core.counts, c.whole.counts,
                {k: v for k, v in asdict(c.core).items() if k not in {"aligned_gold", "aligned_extractor", "operations"}},
                {k: v for k, v in asdict(c.whole).items() if k not in {"aligned_gold", "aligned_extractor", "operations"}}]

    def color_rows(ws, start, candidates, accepted_only=False):
        for row, c in enumerate(candidates, start):
            if accepted_only and not (associated.get(c.gold_id) and associated[c.gold_id].candidate_id == c.id):
                continue
            for col, trace, text in ((29, c.core, c.core.aligned_gold), (30, c.core, c.core.aligned_extractor),
                                     (32, c.whole, c.whole.aligned_gold), (33, c.whole, c.whole.aligned_extractor)):
                rich(ws, row, col, trace, text)

    if "Matched Pairs" in selected:
        ws = worksheets["Matched Pairs"]
        candidates = [cm[a.candidate_id] for a in associations(value)]
        table(ws, 0, "EFFECTIVE ACCEPTED ASSOCIATIONS | IDENTITY DOES NOT IMPLY NUCLEOTIDE CORRECTNESS",
              pair_headers, [candidate_row(c, "ACCEPTED_PAIR") for c in candidates])
        color_rows(ws, 2, candidates)

    if "Debug Log" in selected:
        ws = worksheets["Debug Log"]
        outcomes = []
        for g in run.gold:
            if not g.significant or not g.sequence.canonical or g.id in associated:
                continue
            decision = decisions[g.id]
            data = {"row_type": "GOLD_OUTCOME", "paper_id": g.paper_id, "gold_id": g.id,
                    "selected": False, "auto_selected": g.id in original,
                    "association_status": "MARKED_MISSING" if g.id in missing else decision.status,
                    "gold_name": g.name, "gold_raw": g.sequence.raw, "gold_canonical": g.sequence.canonical,
                    "candidate_reasons": decision.reasons, "gold_source": asdict(g.source),
                    "automatic_decision": decision.status, "automatic_reasons": decision.reasons}
            outcomes.append([data.get(k) for k in pair_headers])
        row = table(ws, 0, "UNMATCHED AND UNRESOLVED GOLD OUTCOMES", pair_headers, outcomes)
        start = row+2
        table(ws, row, "ALL CANDIDATE PAIRS | FULL AUDIT INCLUDING SELECTED, UNSELECTED AND PREEMPTED",
              pair_headers, [candidate_row(c, "CANDIDATE") for c in run.candidates])
        color_rows(ws, start, run.candidates, accepted_only=True)
        if field_scores is not None:
            rows = []
            for kind in ("pool", "kd"):
                for item in field_scores[kind]["rows"]:
                    g, e, cmp = item["gold"], item["extractor"], item["comparison"]
                    rows.append([kind, g["paper_id"], g["id"], e["id"] if e else "", item["status"],
                                 g.get("raw"), e.get("raw") if e else "", str(g["nm"]) if g.get("nm") is not None else "",
                                 str(e["nm"]) if e and e.get("nm") is not None else "", g.get("pool_type"), e.get("pool_type") if e else "",
                                 cmp.get("exact"), cmp.get("tolerant"), cmp.get("relative_error_pct"), g.get("source"),
                                 e.get("source") if e else "", item.get("auto_extractor_id"), item])
            table(ws, ws.dim_rowmax+2, "POOL AND KD | REVIEWED FIELD COMPARISONS",
                  ["field", "paper_id", "gold_id", "extractor_id", "status", "gold_raw", "extracted_raw", "gold_nM", "extracted_nM",
                   "gold_type", "extracted_type", "exact", "tolerant", "relative_error_pct", "gold_source", "prediction_source",
                   "automatic_extractor", "complete_field_result"], rows)

    if "Logistics & Review" in selected:
        ws = worksheets["Logistics & Review"]
        data = {"run_id": run.run_id, "policy_version": run.policy_version, "schema_version": run.schema_version,
                "gold_sha256": run.gold_sha256, "extractor_sha256": run.extractor_sha256,
                "configuration": json.loads(run.config_json), "runtime_metadata": json.loads(run.metadata_json),
                "timings": json.loads(run.timings_json), "selected_scoring_view": dict(zip(("population", "tolerance", "sequence_scope"), view)),
                "selected_scoring_counts": {k: metrics[k] for k in ("G", "E", "M", "T", "TP", "FP", "FN", "pending_gold")},
                "source_scope": "Only scoreable significant golds in linked attempted papers", "closed_world_warning": CAVEAT,
                "report_sheet_selection": selected, "marked_missing": sorted(missing), "rejected_pairs": sorted(rejected)}
        row = table(ws, 0, "RUN, INPUTS AND REPRODUCIBILITY", ["key", "value"], data.items())
        row = table(ws, row, "PAPER LOGISTICS", ["paper_id", "attempted", "G", "raw_extractor", "logical_extractor", "status", "reasons", "aliases"],
                    [[p.id, p.attempted, len(p.gold_ids), len(p.extractor_ids), len(p.logical_extractor_ids), paper_status(value, p), p.reasons, p.aliases] for p in run.papers])
        row = table(ws, row, "VALIDATION AND INPUT WARNINGS", ["code", "message", "source", "record_id", "severity", "suggested_fix"],
                    [[d.code, d.message, d.source, d.record_id, d.severity, d.fix] for d in run.diagnostics])
        row = table(ws, row, "REVIEW HISTORY | APPEND-ONLY", ["revision", "action", "reviewer", "timestamp", "gold_id", "extractor_id", "note", "undo_target", "confirmed"],
                    [[ev.revision, ev.action, ev.reviewer, ev.timestamp, ev.gold_id, ev.extractor_id, ev.note, ev.target_revision, ev.confirmed]
                     for ev in (value.events if isinstance(value, ReviewedRun) else ())])
        row = table(ws, row, "ORIGINAL AUTOMATIC ASSOCIATIONS | IMMUTABLE", ["gold_id", "extractor_id", "candidate_id", "origin", "reasons"],
                    [[a.gold_id, a.extractor_id, a.candidate_id, a.origin, a.reasons] for a in run.automatic])
        if field_data is not None:
            table(ws, row, "POOL/KD INPUT MAPPINGS AND WARNINGS", ["key", "value"],
                  [("field_configuration", json.loads(field_data["config"])), ("field_input_warnings", field_data["warnings"]),
                   ("field_review_event_count", len(field_events)), ("field_review_actions", list(field_events))])
        ws.set_column(1, 1, 80)

    if "Record Inventory" in selected:
        ws = worksheets["Record Inventory"]
        logical = {eid for p in run.papers for eid in p.logical_extractor_ids}
        owner = {a.extractor_id: a.gold_id for a in associations(value)}
        counts = [(k, metrics[k]) for k in ("E_raw", "E_parseable_raw", "E_unique", "E_logical", "E_invalid", "duplicate_suppressed", "multiplicity_exception_count", "significant_all", "significant_unscoreable")]
        row = table(ws, 0, "ATTEMPTED-POPULATION INVENTORY COUNTS", ["count", "value"], counts)
        row = table(ws, row, "EXTRACTOR INVENTORY | RAW, UNLINKED AND SUPPRESSED",
                    ["extractor_id", "paper_id", "name", "canonical", "raw", "logical", "assigned_gold", "source", "normalization_status",
                     "parseable", "normalization_provenance", "paper_key", "name_source", "notes"],
                    [[e.id, e.paper_id, e.name, e.sequence.canonical, e.sequence.raw, e.id in logical, owner.get(e.id, ""), asdict(e.source),
                      e.sequence.status, bool(e.sequence.canonical), asdict(e.sequence), e.paper_key, e.name_source, e.notes] for e in run.extractors])
        row = table(ws, row, "LOGICAL EXTRACTOR PREDICTIONS | EXISTING MULTIPLICITY POLICY", ["paper_id", "extractor_id", "assigned_gold"],
                    [[p.id, eid, owner.get(eid, "")] for p in run.papers for eid in p.logical_extractor_ids])
        row = table(ws, row, "EXTRACTOR DEDUPLICATION", ["duplicate_group_id", "paper_id", "canonical", "raw_members", "logical_representatives", "name_conflict", "multiplicity_exception"],
                    [[d.id, d.paper_id, d.canonical, d.members, d.representatives, d.name_conflict, d.multiplicity] for d in run.duplicates])
        row = table(ws, row, "GOLD REFERENCE INVENTORY | ALL SCOPES",
                    ["gold_id", "paper_id", "significant", "scope_status", "canonical", "sequence_status", "source", "raw", "name", "name_source", "paper_key", "normalization_provenance", "notes"],
                    [[g.id, g.paper_id, g.significant, g.scope_status, g.sequence.canonical, g.sequence.status, asdict(g.source), g.sequence.raw,
                      g.name, g.name_source, g.paper_key, asdict(g.sequence), g.notes] for g in run.gold])
        if field_data is not None:
            table(ws, row, "POOL/KD RAW RECORD INVENTORY", ["field", "role", "record"],
                  [[kind, role, record] for kind in ("pool", "kd") for role in ("gold", "predictions") for record in field_data[role][kind]])
    wb.close()
    return out.getvalue()
