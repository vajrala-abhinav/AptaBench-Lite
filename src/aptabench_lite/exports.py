"""Excel and JSON projections of canonical results; no scientific computation."""
from dataclasses import asdict
from io import BytesIO
import json
import xlsxwriter
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



REPORT_SHEETS = ("Simple Summary", "Debug Log", "Logistics")


def export_workbook(value, metrics=None, sheets=None, field_data=None, field_events=()):
    """Three-tab human-readable report. The JSON audit retains the complete machine record.

    Sheet selection only changes presentation; no matching or alignment is performed.
    """
    run = base_run(value)
    metrics = metrics or compute_metrics(value)
    expected = compute_metrics(value, metrics["population"], metrics["tolerance"], metrics["sequence_scope"])
    if metrics != expected:
        raise ValueError("Metrics do not match canonical result/view")
    selected = tuple(REPORT_SHEETS if sheets is None else sheets)
    if not selected or len(set(selected)) != len(selected) or any(s not in REPORT_SHEETS for s in selected):
        raise ValueError("Choose one or more distinct supported report sheets")

    out = BytesIO()
    wb = xlsxwriter.Workbook(out, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False})
    h = wb.add_format({"bold": True, "bg_color": "#DDE9F4", "text_wrap": True, "valign": "top"})
    section = wb.add_format({"bold": True, "bg_color": "#B8CEDF", "font_size": 12})
    note = wb.add_format({"italic": True, "font_color": "#475569", "text_wrap": True})
    color_formats = {
        op: wb.add_format({"font_color": color, "font_name": "Consolas"})
        for op, color in {
            "MATCH": "#166534", "INSERTION": "#854D0E", "DELETION": "#854D0E",
            "SUBSTITUTION": "#991B1B", "FREE_EXTRACTOR_FLANK": "#64748B",
        }.items()
    }
    mono = wb.add_format({"font_name": "Consolas", "font_size": 10})

    def sheet(name, width=20):
        ws = wb.add_worksheet(name)
        ws.set_column(0, 42, width)
        ws.freeze_panes(0, 0)
        return ws

    def safe(v):
        if isinstance(v, (dict, list, tuple)):
            v = json.dumps(v, default=str, ensure_ascii=False, allow_nan=False)
        if v is None:
            return ""
        if isinstance(v, str) and len(v) > 32767:
            return v[:32670] + " [TRUNCATED: full value in audit.json]"
        return v

    def put(ws, row, values):
        for col, v in enumerate(values):
            ws.write(row, col, safe(v))

    def begin(ws, row, title, headers):
        ws.write(row, 0, title, section)
        for col, name in enumerate(headers):
            ws.write(row + 1, col, name, h)
        return row + 2

    def rich(ws, row, col, trace, text):
        # The trace is canonical: the report never invents a second alignment.
        if not text:
            return
        if len(text) > 3000:
            ws.write(row, col, safe(text))
            return
        pieces = []
        for ch, op in zip(text, trace.operations):
            pieces.extend((color_formats[op], ch))
        if len(text) > 1:
            ws.write_rich_string(row, col, *pieces, mono)
        else:
            ws.write(row, col, text, color_formats[trace.operations[0]])

    cm = {c.id: c for c in run.candidates}
    em = {e.id: e for e in run.extractors}
    gm = {g.id: g for g in run.gold}
    associated = {a.gold_id: a for a in associations(value)}
    original = {a.gold_id: a for a in run.automatic}
    decisions = {d.gold_id: d for d in run.decisions}
    marked_missing = set(value.missing) if isinstance(value, ReviewedRun) else set()
    paper_lookup = {p.id: p for p in run.papers}

    if "Simple Summary" in selected:
        ws = sheet("Simple Summary", 18)
        ws.set_column(0, 0, 24)
        ws.set_column(11, 17, 22)
        ws.write(0, 0, "AptaBench Lite | significant-reference sequence evaluation", section)
        ws.write(1, 0, "The reported closed-world FP is relative to significant gold, not proof of a hallucinated aptamer.", note)
        ws.write(2, 0, "Matched-only F1/precision/recall are conditional pair correctness, not population-wide extraction F1.", note)
        metric_cols = ["population", "tolerance", "scope", "G", "E", "M", "T",
                       "TP", "FP", "FN", "precision", "recall", "F1",
                       "matched_correctness", "significant_recovery", "pending", "selected_view"]
        row = begin(ws, 4, "ALL EIGHT SCORING VIEWS | OVERALL", metric_cols)
        for pop in ("all", "matched"):
            for tol in ("strict", "adaptive"):
                for scope in ("core", "whole"):
                    m = compute_metrics(value, pop, tol, scope)
                    put(ws, row, [pop, tol, scope, m["G"], m["E"], m["M"], m["T"],
                                  m["TP"], m["FP"], m["FN"], m["precision"], m["recall"], m["f1"],
                                  m["matched_correctness"], m["significant_recovery"], m["pending_gold"],
                                  pop == metrics["population"] and tol == metrics["tolerance"] and scope == metrics["sequence_scope"]])
                    row += 1
        row += 2
        row = begin(ws, row, "PER-PAPER SCORING VIEWS", ["paper_id", "status"] + metric_cols)
        for p in run.papers:
            for pop in ("all", "matched"):
                for tol in ("strict", "adaptive"):
                    for scope in ("core", "whole"):
                        m = compute_metrics(value, pop, tol, scope, p.id)
                        put(ws, row, [p.id, paper_status(value, p), pop, tol, scope,
                                      m["G"], m["E"], m["M"], m["T"], m["TP"], m["FP"], m["FN"],
                                      m["precision"], m["recall"], m["f1"], m["matched_correctness"],
                                      m["significant_recovery"], m["pending_gold"],
                                      pop == metrics["population"] and tol == metrics["tolerance"] and scope == metrics["sequence_scope"]])
                        row += 1
        row += 2
        row = begin(ws, row, "PER-RECORD COMPLETION | SCOREABLE SIGNIFICANT GOLDS",
                    ["paper_id", "gold_id", "Significant_Status", "extractor_id",
                     "association_status", "core_completion_%", "whole_completion_%",
                     "strict_core", "tolerant_core", "strict_whole", "tolerant_whole"])
        for g in run.gold:
            if not g.significant or not g.sequence.canonical:
                continue
            a = associated.get(g.id)
            c = cm[a.candidate_id] if a else None
            put(ws, row, [g.paper_id, g.id, "Y", a.extractor_id if a else "",
                          a.origin if a else "MARKED_MISSING" if g.id in marked_missing else decisions[g.id].status,
                          c.core.completion() if c else None, c.whole.completion() if c else None,
                          c.strict_core_pass if c else None, c.adaptive_core_pass if c else None,
                          c.strict_whole_pass if c else None, c.adaptive_whole_pass if c else None])
            row += 1
        ws.autofilter(5, 0, 5 + 8, len(metric_cols) - 1)

    if "Debug Log" in selected:
        ws = sheet("Debug Log", 22)
        ws.set_column(0, 0, 16)
        ws.set_column(9, 12, 40)
        ws.set_column(28, 35, 60)
        ws.write(0, 0, "Every stored gold–extractor candidate; SELECTED marks the effective association.", section)
        ws.write(1, 0, "Identity confirmation does not turn an incorrect nucleotide sequence into a passing value.", note)
        cols = ["row_type", "paper_id", "gold_id", "extractor_id", "selected", "auto_selected",
                "association_status", "gold_name", "extractor_name", "gold_raw", "extractor_raw",
                "gold_canonical", "extractor_canonical", "core_edits", "whole_edits",
                "budget", "core_completion_%", "whole_completion_%",
                "strict_core", "tolerant_core", "strict_whole", "tolerant_whole",
                "name_support", "name_conflict", "viable", "candidate_stage",
                "candidate_reasons", "gold_source", "extractor_source",
                "core_aligned_gold", "core_aligned_extractor", "core_operations",
                "whole_aligned_gold", "whole_aligned_extractor", "whole_operations",
                "core_optimal_intervals", "whole_optimal_intervals"]
        row = begin(ws, 3, "MATCHED AND UNMATCHED GOLD OUTCOMES", cols)
        for g in run.gold:
            if not g.significant or not g.sequence.canonical:
                continue
            a = associated.get(g.id)
            c = cm[a.candidate_id] if a else None
            e = em[a.extractor_id] if a else None
            status = a.origin if a else "MARKED_MISSING" if g.id in marked_missing else decisions[g.id].status
            if c is None:
                put(ws, row, ["GOLD_OUTCOME", g.paper_id, g.id, "", False,
                              g.id in original, status, g.name, "", g.sequence.raw, "",
                              g.sequence.canonical, "", "", "", "", "", "", "", "", "", "",
                              "", "", "", "", decisions[g.id].reasons, asdict(g.source)])
            else:
                put(ws, row, ["GOLD_OUTCOME", g.paper_id, g.id, e.id, True,
                              g.id in original and original[g.id].candidate_id == c.id, status,
                              g.name, e.name, g.sequence.raw, e.sequence.raw,
                              g.sequence.canonical, e.sequence.canonical, c.core.distance,
                              c.whole.distance, c.budget, c.core.completion(), c.whole.completion(),
                              c.strict_core_pass, c.adaptive_core_pass, c.strict_whole_pass,
                              c.adaptive_whole_pass, c.name_support, c.name_conflict, c.viable,
                              c.stage, c.reasons, asdict(g.source), asdict(e.source),
                              c.core.aligned_gold, c.core.aligned_extractor, c.core.operations,
                              c.whole.aligned_gold, c.whole.aligned_extractor, c.whole.operations,
                              c.core.optimal_interval_count, c.whole.optimal_interval_count])
                rich(ws, row, 29, c.core, c.core.aligned_gold)
                rich(ws, row, 30, c.core, c.core.aligned_extractor)
            row += 1
        row += 2
        row = begin(ws, row, "ALL CANDIDATE PAIRS | INCLUDING UNSELECTED AND PREEMPTED", cols)
        for c in run.candidates:
            g, e = gm[c.gold_id], em[c.extractor_id]
            a = associated.get(g.id)
            auto = original.get(g.id)
            chosen = bool(a and a.candidate_id == c.id)
            status = a.origin if chosen else "CANDIDATE_ONLY"
            put(ws, row, ["CANDIDATE", g.paper_id, g.id, e.id, chosen,
                          bool(auto and auto.candidate_id == c.id), status,
                          g.name, e.name, g.sequence.raw, e.sequence.raw, g.sequence.canonical,
                          e.sequence.canonical, c.core.distance, c.whole.distance, c.budget,
                          c.core.completion(), c.whole.completion(),
                          c.strict_core_pass, c.adaptive_core_pass, c.strict_whole_pass, c.adaptive_whole_pass,
                          c.name_support, c.name_conflict, c.viable, c.stage, c.reasons,
                          asdict(g.source), asdict(e.source),
                          c.core.aligned_gold, c.core.aligned_extractor, c.core.operations,
                          c.whole.aligned_gold, c.whole.aligned_extractor, c.whole.operations,
                          c.core.optimal_interval_count, c.whole.optimal_interval_count])
            if chosen:
                rich(ws, row, 29, c.core, c.core.aligned_gold)
                rich(ws, row, 30, c.core, c.core.aligned_extractor)
            row += 1

    if "Logistics" in selected:
        ws = sheet("Logistics", 26)
        ws.set_column(0, 0, 35)
        ws.set_column(1, 7, 40)
        row = begin(ws, 0, "RUN, INPUTS AND REPRODUCIBILITY", ["key", "value"])
        data = {
            "run_id": run.run_id, "policy_version": run.policy_version,
            "schema_version": run.schema_version,
            "gold_sha256": run.gold_sha256, "extractor_sha256": run.extractor_sha256,
            "configuration": json.loads(run.config_json),
            "runtime_metadata": json.loads(run.metadata_json),
            "timings": json.loads(run.timings_json),
            "selected_scoring_view": {k: metrics[k] for k in ("population", "tolerance", "sequence_scope")},
            "selected_scoring_counts": {k: metrics[k] for k in ("G", "E", "M", "T", "TP", "FP", "FN", "pending_gold")},
            "source_scope": "Only scoreable significant golds in linked attempted papers",
            "closed_world_warning": CAVEAT,
            "report_sheet_selection": selected,
        }
        for key, val in data.items():
            put(ws, row, [key, val])
            row += 1
        row += 2
        row = begin(ws, row, "PAPER LOGISTICS", ["paper_id", "attempted", "G",
                                                 "raw_extractor", "logical_extractor", "status", "reasons"])
        for p in run.papers:
            put(ws, row, [p.id, p.attempted, len(p.gold_ids), len(p.extractor_ids),
                          len(p.logical_extractor_ids), paper_status(value, p), p.reasons])
            row += 1
        row += 2
        row = begin(ws, row, "VALIDATION AND INPUT WARNINGS",
                    ["code", "message", "source", "record_id", "severity", "suggested_fix"])
        for d in run.diagnostics:
            put(ws, row, [d.code, d.message, d.source, d.record_id, d.severity, d.fix])
            row += 1
        row += 2
        row = begin(ws, row, "REVIEW HISTORY | APPEND-ONLY",
                    ["revision", "action", "reviewer", "timestamp", "gold_id",
                     "extractor_id", "note", "undo_target", "confirmed"])
        if isinstance(value, ReviewedRun):
            for ev in value.events:
                put(ws, row, [ev.revision, ev.action, ev.reviewer, ev.timestamp, ev.gold_id,
                              ev.extractor_id, ev.note, ev.target_revision, ev.confirmed])
                row += 1
        row += 2
        row = begin(ws, row, "EXTRACTOR INVENTORY | INCLUDING UNLINKED AND SUPPRESSED",
                    ["extractor_id", "paper_id", "name", "canonical", "raw", "logical",
                     "assigned_gold", "source", "normalization_status"])
        logical = {eid for p in run.papers for eid in p.logical_extractor_ids}
        owner = {a.extractor_id: a.gold_id for a in associations(value)}
        for e in run.extractors:
            put(ws, row, [e.id, e.paper_id, e.name, e.sequence.canonical,
                          e.sequence.raw, e.id in logical, owner.get(e.id, ""),
                          asdict(e.source), e.sequence.status])
            row += 1
        row += 2
        row = begin(ws, row, "EXTRACTOR DEDUPLICATION",
                    ["duplicate_group_id", "paper_id", "canonical", "raw_members",
                     "logical_representatives", "name_conflict", "multiplicity_exception"])
        for d in run.duplicates:
            put(ws, row, [d.id, d.paper_id, d.canonical, d.members, d.representatives,
                          d.name_conflict, d.multiplicity])
            row += 1
        row += 2
        row = begin(ws, row, "GOLD REFERENCE INVENTORY | ALL SCOPES",
                    ["gold_id", "paper_id", "significant", "scope_status", "canonical",
                     "sequence_status", "source"])
        for g in run.gold:
            put(ws, row, [g.id, g.paper_id, g.significant, g.scope_status,
                          g.sequence.canonical, g.sequence.status, asdict(g.source)])
            row += 1

    if field_data is not None:
        from .field_eval import field_results
        from .field_review import replay
        if field_data["run_id"]!=run.run_id:raise ValueError("Field data belongs to a different evaluation run")
        field_scores = replay(field_data, field_events)
        if "Simple Summary" in selected:
            ws = wb.get_worksheet_by_name("Simple Summary")
            row = ws.dim_rowmax + 3
            row = begin(ws, row, "POOL AND KD | EFFECTIVE FIELD SCORES",
                        ["field", "gold", "predictions", "associations", "passing",
                         "pending_review", "closed_world_precision", "closed_world_recall",
                         "closed_world_F1", "matched_pair_correctness"])
            for kind in ("pool", "kd"):
                m=field_scores[kind]
                if not (m["gold"] or m["predictions"]): continue
                put(ws,row,[kind,m["G"],m["E"],m["M"],m["T"],m["pending"],
                            m["precision"],m["recall"],m["f1"],m["matched_correctness"]])
                row += 1
        if "Debug Log" in selected:
            ws = wb.get_worksheet_by_name("Debug Log")
            row = ws.dim_rowmax + 3
            row = begin(ws,row,"POOL AND KD | REVIEWED FIELD COMPARISONS",
                        ["field","paper_id","gold_id","extractor_id","status",
                         "gold_raw","extracted_raw","gold_nM","extracted_nM",
                         "gold_type","extracted_type","exact","tolerant",
                         "relative_error_pct","gold_source","prediction_source",
                         "automatic_extractor"])
            for kind in ("pool","kd"):
                for item in field_scores[kind]["rows"]:
                    g,e=item["gold"],item["extractor"]
                    cmp=item["comparison"]
                    put(ws,row,[kind,g["paper_id"],g["id"],e["id"] if e else "",
                                item["status"],g.get("raw"),e.get("raw") if e else "",
                                str(g["nm"]) if g.get("nm") is not None else "",
                                str(e["nm"]) if e and e.get("nm") is not None else "",
                                g.get("pool_type"),e.get("pool_type") if e else "",
                                cmp.get("exact"),cmp.get("tolerant"),cmp.get("relative_error_pct"),
                                g.get("source"),e.get("source") if e else "",item.get("auto_extractor_id")])
                    row += 1
        if "Logistics" in selected:
            ws = wb.get_worksheet_by_name("Logistics")
            row = ws.dim_rowmax + 3
            row = begin(ws,row,"POOL/KD INPUT MAPPINGS AND WARNINGS",["key","value"])
            for key,val in (("field_configuration",json.loads(field_data["config"])),
                            ("field_input_warnings",field_data["warnings"]),
                            ("field_review_event_count",len(field_events)),
                            ("field_review_actions",list(field_events))):
                put(ws,row,[key,val]);row+=1

    wb.close()
    return out.getvalue()
