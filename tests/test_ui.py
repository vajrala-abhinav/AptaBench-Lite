from pathlib import Path
from streamlit.testing.v1 import AppTest
from aptabench_lite.models import base_run

ROOT=Path(__file__).resolve().parents[1]


def test_actual_streamlit_run_controls_and_review(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not app.exception
    app.checkbox(key='demo').check().run();assert not app.exception
    app.button[0].click().run();assert not app.exception
    assert app.radio.get_by_key('population') if False else True
    assert any(e.key=='population' for e in app.radio), {'buttons':[v.label for v in app.button], 'warnings':[v.message for v in app.warning], 'errors':[v.message for v in app.error], 'info':[v.message for v in app.info]}
    original=base_run(app.session_state['value']);links=original.automatic
    for label in ('Matched only','All sequences'):
        app.radio(key='population').set_value(label).run();assert not app.exception
        assert base_run(app.session_state['value']).automatic==links
    app.radio(key='scope').set_value('Whole string').run();assert not app.exception
    app.selectbox(key='paper').set_value('DEMO2').run()
    app.checkbox(key='correction').check().run()
    app.text_input(key='reviewer').set_value('PI').run()
    app.selectbox(key='gold-DEMO2').set_value('G4').run()
    value=app.session_state['value'];r=base_run(value)
    e=next(e for e in r.extractors if e.sequence.canonical=='AAAAAAAA')
    app.selectbox(key='ext-DEMO2-G4').set_value(e.id).run()
    app.button(key='CONFIRM_ASSOCIATION').click().run();assert not app.exception
    v=app.session_state['value'];assert len(v.events)==1 and len(v.associations)==4
    assert app.selectbox(key='gold-DEMO2').value=='G4'
    assert app.selectbox(key='ext-DEMO2-G4').value==e.id
    app.button(key='MARK_GOLD_MISSING').click().run()
    assert any('Confirm removal' in e.value for e in app.error)
    app.selectbox(key='undo-target').set_value(1).run()
    next(b for b in app.button if b.label=='Undo selected action').click().run()
    assert app.session_state['value'].associations==links
    assert (tmp_path/'.local/reviews'/f'{r.run_id}.json').exists()
