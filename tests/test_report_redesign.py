"""Presentation contract: project fixed results without changing scientific state."""
from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries
import pytest

from aptabench_lite.exports import export_workbook, export_audit, REPORT_SHEETS
from aptabench_lite.models import associations
from aptabench_lite.review import commit_event
from aptabench_lite.scoring import compute_metrics
from aptabench_lite.engine import evaluate
from aptabench_lite.field_eval import FieldConfig, load_fields
from aptabench_lite.field_review import append, replay
from test_field_eval import synthetic


def section(ws, title):
    """Read actual Excel table rows by their section title, independent of row positions."""
    row = next(r for r in range(1, ws.max_row+1) if ws.cell(r, 1).value == title)
    header_row = row+1
    table = next((t for t in ws.tables.values() if range_boundaries(t.ref)[1] == header_row), None)
    if table is None:
        return []
    left, top, right, bottom = range_boundaries(table.ref)
    headers = [ws.cell(top, c).value for c in range(left, right+1)]
    return [dict(zip(headers, [ws.cell(r, c).value for c in range(left, right+1)])) for r in range(top+1, bottom+1)]


def report_case(make_run):
    run = make_run([('a','ACGTCAGT'), ('b','TGCACGTA'), ('c','CGTAGTCA'),
                    ('excluded','AAAA','','non_significant_sequence'), ('invalid','XXX')],
                   [('P',[{'sequence':'ACGTCAGT'}, {'sequence':'TTTGCACGTAGG'},
                          {'sequence':'CCCCGGGG'}, {'sequence':'CCCCGGGG'}])])
    ext = next(e for e in run.extractors if e.sequence.canonical == 'CCCCGGGG')
    return commit_event(run, 'CONFIRM_ASSOCIATION', 'SYNTHETIC_PI', 'c', ext.id)


def test_summary_is_compact_and_defines_scientific_counts(make_run):
    value = report_case(make_run)
    book = load_workbook(BytesIO(export_workbook(value)))
    assert book.sheetnames == list(REPORT_SHEETS)
    ws = book['Simple Summary']
    text = ' '.join(str(c.value) for row in ws for c in row if c.value is not None)
    for phrase in ('Closed-world FP does not mean verified hallucination', 'True negatives are not defined',
                   'conditional matched-pair correctness', 'T is not shorthand', 'TP = T', 'FP = E − T', 'FN = G − T'):
        assert phrase.lower() in text.lower()
    for symbol in ('G','E','M','T','TP','FP','FN'):
        assert any(row[0].value == symbol for row in ws)
    for forbidden in ('paper_id','gold_id','extractor_id','PER-PAPER','PER-RECORD','core_completion_%'):
        assert forbidden not in text
    assert ws.max_row < 65
    rows = section(ws, 'A | ALL EIGHT SCORING VIEWS — OVERALL')
    assert len(rows) == 8 and sum(r['selected_view'] for r in rows) == 1
    for row in rows:
        m = compute_metrics(value, row['population'], row['tolerance'], row['scope'])
        for col, key in [('precision','precision'),('recall','recall'),('F1','f1'),('significant_recovery','significant_recovery'),('matched_correctness','matched_correctness')]:
            assert row[col] == pytest.approx(m[key])
    assert ws['D5'].number_format == '0.0%'
    assert ws.freeze_panes


def test_effective_pairs_candidates_missing_and_inventory_are_complete(make_run):
    value = report_case(make_run)
    # Also leave a previously accepted gold unresolved; automatic result stays intact.
    old = associations(value)[0]
    value = commit_event(value, 'REJECT_PAIR', 'SYNTHETIC_PI', old.gold_id, old.extractor_id)
    book = load_workbook(BytesIO(export_workbook(value)), rich_text=True)
    pairs = section(book['Matched Pairs'], 'EFFECTIVE ACCEPTED ASSOCIATIONS | IDENTITY DOES NOT IMPLY NUCLEOTIDE CORRECTNESS')
    assert {(p['gold_id'], p['extractor_id']) for p in pairs} == {(a.gold_id, a.extractor_id) for a in associations(value)}
    assert len({p['extractor_id'] for p in pairs}) == len(pairs)
    manual = next(p for p in pairs if p['gold_id']=='c')
    assert manual['review_status']=='HUMAN_CONFIRMED'
    assert manual['tolerant_core'] is False and manual['core_edits'] > manual['budget']
    outcomes = section(book['Debug Log'], 'UNMATCHED AND UNRESOLVED GOLD OUTCOMES')
    assert old.gold_id in {r['gold_id'] for r in outcomes}
    candidates = section(book['Debug Log'], 'ALL CANDIDATE PAIRS | FULL AUDIT INCLUDING SELECTED, UNSELECTED AND PREEMPTED')
    assert {r['candidate_id'] for r in candidates} == {c.id for c in value.run.candidates}
    assert len(candidates) == len(value.run.candidates)
    for row in candidates:
        c=next(c for c in value.run.candidates if c.id==row['candidate_id'])
        assert str(row['core_aligned_gold']) == c.core.aligned_gold
        assert str(row['whole_aligned_extractor']) == c.whole.aligned_extractor
        assert json.loads(row['core_operations']) == list(c.core.operations)
    inventory = book['Record Inventory']
    raw = section(inventory,'EXTRACTOR INVENTORY | RAW, UNLINKED AND SUPPRESSED')
    assert len(raw)==len(value.run.extractors)
    assert sum(r['logical'] for r in raw)==compute_metrics(value)['E']
    assert len(section(inventory,'EXTRACTOR DEDUPLICATION'))==len(value.run.duplicates)
    assert len(section(inventory,'GOLD REFERENCE INVENTORY | ALL SCOPES'))==len(value.run.gold)
    assert len(section(book['Logistics & Review'],'REVIEW HISTORY | APPEND-ONLY'))==len(value.events)


def test_per_paper_selected_and_all_views_use_exact_calculated_metrics(make_run):
    value=report_case(make_run)
    selected=compute_metrics(value,'matched','strict','whole')
    book=load_workbook(BytesIO(export_workbook(value,selected)))
    ws=book['Per-Paper Results']
    main=section(ws,'SELECTED SCORING VIEW | ONE ROW PER PAPER')
    comparison=section(ws,'ALL EIGHT SCORING VIEWS | PER-PAPER COMPARISON')
    assert len(main)==len(value.run.papers) and len(comparison)==8*len(main)
    for row in main+comparison:
        m=compute_metrics(value,row['population'],row['tolerance'],row['scope'],row['paper_id'])
        for key in ('G','E','M','T','TP','FP','FN'):
            assert row[key]==m[key]
        for col,key in [('precision','precision'),('recall','recall'),('F1','f1')]:
            assert row[col]==pytest.approx(m[key])


def test_sheet_subsets_are_canonical_and_independent(make_run):
    value=report_case(make_run)
    for name in REPORT_SHEETS:
        assert load_workbook(BytesIO(export_workbook(value,sheets=[name]))).sheetnames==[name]
    assert load_workbook(BytesIO(export_workbook(value,sheets=['Record Inventory','Simple Summary']))).sheetnames==['Simple Summary','Record Inventory']
    with pytest.raises(ValueError):export_workbook(value,sheets=['Matched Pairs','Matched Pairs'])


def test_pool_kd_metrics_review_and_raw_provenance_are_preserved():
    gb,eb=synthetic();run=evaluate(gb,eb)
    data=load_fields(run,gb,eb,FieldConfig(pool_enabled=True,kd_enabled=True))
    events,_=append(data,[],'missing','SYNTHETIC_PI','kd','kd:G1')
    before=replay(data,events)
    audit_before=export_audit(run,field_data=data,field_events=events)
    book=load_workbook(BytesIO(export_workbook(run,field_data=data,field_events=events)))
    scores=section(book['Simple Summary'],'POOL AND KD | EFFECTIVE FIELD SCORES')
    for row in scores:
        m=before[row['field']]
        for col,key in [('gold','G'),('predictions','E'),('associations','M'),('passing','T'),('pending_review','pending')]:assert row[col]==m[key]
        for col,key in [('closed_world_precision','precision'),('closed_world_recall','recall'),('closed_world_F1','f1'),('matched_pair_correctness','matched_correctness')]:assert row[col]==pytest.approx(m[key])
    assert next(r for r in scores if r['field']=='pool')['gold']==1 # library-level, not per-aptamer
    detailed=section(book['Debug Log'],'POOL AND KD | REVIEWED FIELD COMPARISONS')
    assert len(detailed)==sum(len(before[k]['rows']) for k in ('pool','kd'))
    inventory=section(book['Record Inventory'],'POOL/KD RAW RECORD INVENTORY')
    assert len(inventory)==sum(len(data[role][kind]) for kind in ('pool','kd') for role in ('gold','predictions'))
    logs=section(book['Logistics & Review'],'POOL/KD INPUT MAPPINGS AND WARNINGS')
    assert json.loads(next(r['value'] for r in logs if r['key']=='field_review_actions'))==events
    assert export_audit(run,field_data=data,field_events=events)==audit_before
    assert replay(data,events)==before


def test_frozen_pre_refactor_numerical_contract_and_no_recomputation(make_run,monkeypatch):
    value=report_case(make_run)
    before=asdict(value)
    scores={f'{p}/{t}/{s}':compute_metrics(value,p,t,s) for p in ('all','matched') for t in ('strict','adaptive') for s in ('core','whole')}
    golden=json.loads((Path(__file__).parent/'fixtures/report-metrics-before.json').read_text())
    assert scores==golden['effective_metrics']
    audit_before=export_audit(value)
    import aptabench_lite.alignment as alignment
    import aptabench_lite.engine as engine
    def forbidden(*a,**kw):pytest.fail('Export recomputed scientific results')
    monkeypatch.setattr(alignment,'align',forbidden)
    monkeypatch.setattr(engine,'evaluate',forbidden)
    export_workbook(value)
    assert scores=={f'{p}/{t}/{s}':compute_metrics(value,p,t,s) for p in ('all','matched') for t in ('strict','adaptive') for s in ('core','whole')}
    assert asdict(value)==before and export_audit(value)==audit_before


def test_on_demand_report_invalidation_after_scoring_sheets_and_both_reviews(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from aptabench_lite import ui
    root=Path(__file__).resolve().parents[1]
    gb,eb=synthetic();examples=tmp_path/'examples';examples.mkdir()
    (examples/'gold.xlsx').write_bytes(gb);(examples/'extractor.xlsx').write_bytes(eb)
    monkeypatch.chdir(tmp_path);monkeypatch.setattr(ui,'ROOT',tmp_path)
    monkeypatch.setattr(ui,'STORE',tmp_path/'.local/reviews')
    calls=[]
    def capture(*args,**kw):
        calls.append(kw.get('sheets'));return export_workbook(*args,**kw)
    monkeypatch.setattr(ui,'export_workbook',capture)
    app=AppTest.from_file(str(root/'app.py')).run()
    app.checkbox(key='demo').check().run()
    app.checkbox(key='evaluate-pool').check().run()
    app.checkbox(key='evaluate-kd').check().run()
    app.button[0].click().run()
    assert not app.exception and not calls
    auto=asdict(app.session_state['value'])
    def available():return any(e.proto.label=='Download Excel report' for e in app.get('download_button'))
    def prepare():
        app.button(key='prepare-xlsx').click().run()
        assert not app.exception and available()
        return load_workbook(BytesIO(app.session_state['prepared-xlsx'][1]))
    assert not available()
    assert prepare().sheetnames==list(REPORT_SHEETS)
    app.radio(key='population').set_value('Matched only').run()
    assert not available() and len(calls)==1
    b=prepare()
    scores=section(b['Simple Summary'],'A | ALL EIGHT SCORING VIEWS — OVERALL')
    assert next(r for r in scores if r['selected_view'])['population']=='matched'
    app.multiselect(key='report-sheets').set_value(['Matched Pairs','Logistics & Review']).run()
    assert not available() and len(calls)==2
    assert prepare().sheetnames==['Matched Pairs','Logistics & Review']
    app.checkbox(key='field-review-all').check().run()
    app.text_input(key='field-reviewer').set_value('SYNTHETIC_PI').run()
    app.selectbox(key='field-record').set_value('kd:G1').run()
    app.button(key='field-missing').click().run()
    assert not available() and len(calls)==3
    b=prepare()
    log=section(b['Logistics & Review'],'POOL/KD INPUT MAPPINGS AND WARNINGS')
    assert next(r for r in log if r['key']=='field_review_event_count')['value']==1
    next(b for b in app.button if b.label=='Undo latest field review').click().run()
    assert not available() and len(calls)==4
    # The original evaluation and scientific state are immutable through report operations.
    assert asdict(app.session_state['value'])==auto
    value=app.session_state['value'];a=associations(value)[0]
    changed=commit_event(value,'REJECT_PAIR','SYNTHETIC_PI',a.gold_id,a.extractor_id)
    app.session_state['value']=changed
    app.run()
    assert not available() and len(calls)==4
    b=prepare()
    pairs=section(b['Matched Pairs'],'EFFECTIVE ACCEPTED ASSOCIATIONS | IDENTITY DOES NOT IMPLY NUCLEOTIDE CORRECTNESS')
    assert len(pairs)==len(associations(changed))
    assert (a.gold_id,a.extractor_id) not in {(p['gold_id'],p['extractor_id']) for p in pairs}
