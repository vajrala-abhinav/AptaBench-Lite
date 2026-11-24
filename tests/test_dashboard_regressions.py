"""Regression coverage for the two branches merged into main in November 2026."""
from dataclasses import replace
import json
from pathlib import Path
from hashlib import sha256

import pytest
from streamlit.testing.v1 import AppTest

from aptabench_lite.engine import evaluate
from aptabench_lite.models import base_run
from aptabench_lite.field_eval import FieldConfig, load_fields, field_results
from aptabench_lite.field_review import append, to_bytes, from_bytes, canonical
from aptabench_lite.exports import export_audit
from test_field_eval import synthetic
from conftest import inputs,xlsx

ROOT=Path(__file__).resolve().parents[1]


def test_unresolved_first_keeps_resolved_records_inspectable(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    app.checkbox(key='demo').check().run()
    app.button[0].click().run()
    app.selectbox(key='paper').set_value('DEMO2').run()
    app.checkbox(key='only-unresolved').check().run()
    assert app.selectbox(key='gold-DEMO2').options[0].startswith('G4 ·')
    assert any(option.startswith('G3 ·') for option in app.selectbox(key='gold-DEMO2').options)


def test_optional_fields_dashboard_run_review_export_and_restore(tmp_path,monkeypatch):
    from aptabench_lite import ui
    gb,eb=synthetic()
    examples=tmp_path/'examples';examples.mkdir()
    (examples/'gold.xlsx').write_bytes(gb);(examples/'extractor.xlsx').write_bytes(eb)
    monkeypatch.chdir(tmp_path);monkeypatch.setattr(ui,'ROOT',tmp_path)
    monkeypatch.setattr(ui,'STORE',tmp_path/'.local/reviews')
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    app.checkbox(key='demo').check().run()
    app.checkbox(key='evaluate-pool').check().run()
    app.checkbox(key='evaluate-kd').check().run()
    app.button[0].click().run()
    assert not app.exception
    assert any(h.value=='Pool & Kd results' for h in app.header)
    data=app.session_state['field-data'];assert field_results(data)['kd']['T']==2
    original=base_run(app.session_state['value']).automatic
    app.checkbox(key='field-review-all').check().run()
    app.text_input(key='field-reviewer').set_value('PI').run()
    app.selectbox(key='field-record').set_value('kd:G1').run()
    app.button(key='field-missing').click().run()
    assert not app.exception
    events=app.session_state['field-review-events']
    assert len(events)==1 and field_results(data,[events[0]])['kd']['T']==1
    assert base_run(app.session_state['value']).automatic==original
    next(b for b in app.button if b.label=='Undo latest field review').click().run()
    assert not app.exception and len(app.session_state['field-review-events'])==2
    app.radio(key='population').set_value('Matched only').run()
    assert not app.exception and base_run(app.session_state['value']).automatic==original


def test_field_predictions_outside_attempted_scope_do_not_inflate_E():
    from io import BytesIO
    from openpyxl import load_workbook
    gb,eb=inputs([('g1','ACGT','','significant_sequence','P'),('g2','TGCA','','significant_sequence','Q')],[('P',[])])
    book=load_workbook(BytesIO(eb));ws=book.create_sheet('kd');ws.append(['pk','raw_values'])
    ws.append(['P','[{"amount": 10, "unit": "nM"}]']);ws.append(['Q','[{"amount": 20, "unit": "nM"}]'])
    out=BytesIO();book.save(out)
    run=evaluate(gb,out.getvalue())
    data=load_fields(run,gb,out.getvalue(),FieldConfig(kd_enabled=True))
    assert field_results(data)['kd']['E']==1
    assert any(w['problem']=='Unattempted paper excluded from field scores' for w in data['warnings'])
    assert len(data['predictions']['kd'])==2 # raw inventory remains auditable


def test_json_audit_contains_effective_field_results():
    gb,eb=synthetic();run=evaluate(gb,eb)
    data=load_fields(run,gb,eb,FieldConfig(pool_enabled=True,kd_enabled=True))
    events,_=append(data,[],'missing','PI','kd','kd:G1')
    audit=json.loads(export_audit(run,field_data=data,field_events=events))
    assert audit['optional_fields']['automatic_results']['kd']['T']==2
    assert audit['optional_fields']['effective_results']['kd']['T']==1
    assert audit['optional_fields']['review_events']==events


@pytest.mark.parametrize('mutate',[
    lambda e:e.update(reviewer=123),lambda e:e.update(time='not a timestamp'),
    lambda e:e.update(field='not-a-field'),lambda e:e.update(revision=True),
])
def test_field_review_invalid_events_fail_readably(mutate):
    gb,eb=synthetic();run=evaluate(gb,eb);data=load_fields(run,gb,eb,FieldConfig(kd_enabled=True))
    events,_=append(data,[],'missing','PI','kd','kd:G1')
    wrapper=json.loads(to_bytes(data,events));mutate(wrapper['payload']['events'][0])
    wrapper['sha256']=sha256(canonical(wrapper['payload'])).hexdigest()
    with pytest.raises(ValueError):from_bytes(data,json.dumps(wrapper).encode())


def test_optional_field_load_error_does_not_publish_partial_run(tmp_path,monkeypatch):
    from aptabench_lite import ui
    gb,eb=synthetic();examples=tmp_path/'examples';examples.mkdir()
    (examples/'gold.xlsx').write_bytes(gb);(examples/'extractor.xlsx').write_bytes(eb)
    monkeypatch.chdir(tmp_path);monkeypatch.setattr(ui,'ROOT',tmp_path)
    monkeypatch.setattr(ui,'STORE',tmp_path/'.local/reviews')
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    app.checkbox(key='demo').check().run()
    app.checkbox(key='evaluate-kd').check().run()
    def fail(*args,**kwargs):raise ValueError('Cannot read optional field worksheet')
    monkeypatch.setattr(ui,'load_fields',fail)
    app.button[0].click().run()
    assert not app.exception and any('Cannot read optional' in e.value for e in app.error)
    assert 'value' not in app.session_state


def test_existing_field_backup_remains_portable():
    from copy import deepcopy
    gb,eb=synthetic();run=evaluate(gb,eb);data=load_fields(run,gb,eb,FieldConfig(kd_enabled=True))
    old=deepcopy(data)
    for kind in old['predictions']:
        for row in old['predictions'][kind]:row.pop('in_scope',None)
    events,_=append(old,[],'missing','PI','kd','kd:G1')
    assert from_bytes(data,to_bytes(old,events))==events
