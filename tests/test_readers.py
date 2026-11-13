from dataclasses import replace
import json
import pytest
from aptabench_lite.config import RunConfig
from aptabench_lite.engine import evaluate
from aptabench_lite.readers import parse_items,inspect_workbook
from aptabench_lite.scoring import compute_metrics
from conftest import xlsx,inputs


def test_configurable_simple_mapping_and_scope():
    gb=xlsx(['Paper','PDF','ID','Bases','Label','Scope'],[['P','p.pdf','a','ACGTCAGT','A','yes'],['P','p.pdf','b','CCGG','B','no']],'Custom')
    eb=xlsx(['Document','Nucleotides','Name'],[['p','ACGTCAGT','A']],'Predictions')
    cfg=RunConfig(gold_sheet='Custom',extractor_sheet='Predictions',gold_paper='Paper',gold_key='PDF',gold_id='ID',gold_sequence='Bases',gold_name='Label',gold_type='',gold_status='Scope',significant_values=('yes',),nonsignificant_values=('no',),extractor_key='Document',extractor_value='Nucleotides',extractor_name='Name',parser='simple')
    r=evaluate(gb,eb,cfg);assert compute_metrics(r)['T']==1 and len(r.candidates)==1
    assert r.extractors[0].source.cell=='B2' and r.extractors[0].name_source=='sequence_row'
    assert inspect_workbook(gb)['Custom']['rows']==2


def test_safe_literal_parser():
    assert parse_items("[{'sequence': 'ACGT', 'notes': None}]")[0]['sequence']=='ACGT'
    for value in ('__import__("os").system("id")','"ACGT"','['*13+']'*13,'[','1'):
        with pytest.raises(ValueError):parse_items(value)
    with pytest.raises(ValueError):parse_items('x'*100001)


def test_invalid_inputs_inventory(make_run):
    r=make_run([('a','/Bio/ACGT'),('b','ACGT','','unknown')],[('P',[{'sequence':'ACG-T'},42])])
    assert len(r.extractors)==2 and compute_metrics(r)['significant_unscoreable']==1
    assert not r.candidates and not r.automatic
    assert any(d.code=='UNKNOWN_SIGNIFICANCE' for d in r.diagnostics)


def test_forward_fill_same_paper_only():
    gb,eb=inputs([('a','ACGT','','significant_sequence','P','p.pdf'),('b','ACGT','','significant_sequence','Q',''),('c','ACGT','','significant_sequence','P','')],[('P',[])])
    r=evaluate(gb,eb);g={g.id:g for g in r.gold}
    assert g['c'].paper_key=='p.pdf' and g['b'].paper_key==''


def test_bad_duplicate_ids_and_missing_header():
    gb,eb=inputs([('a','ACGT'),('a','ACGT')],[('P',[])])
    with pytest.raises(ValueError,match='Duplicate'):evaluate(gb,eb)
    gb,eb=inputs([('a','ACGT')],[('P',[])])
    with pytest.raises(ValueError,match='required'):evaluate(gb,eb,replace(RunConfig(),gold_sequence='absent'))
    with pytest.raises(ValueError):evaluate(b'not xlsx',eb)


def test_malformed_attempted_preserved():
    gb,eb=inputs([('a','ACGT')],[('P',[])])
    eb=xlsx(['pk','value'],[['P','not JSON']],'aptamer_seq')
    r=evaluate(gb,eb)
    assert compute_metrics(r)['G']==1 and not r.automatic
    assert len(r.extractors)==1 and 'not JSON' in r.extractors[0].source.raw_json


def test_manifest_attempted_and_no_link():
    gb,eb=inputs([('a','ACGT')],[('UNKNOWN',[])])
    r=evaluate(gb,eb);assert compute_metrics(r)['attempted_papers']==0
    r=evaluate(gb,eb,replace(RunConfig(),attempted_keys=('P',)))
    assert compute_metrics(r)['G']==1 and compute_metrics(r)['FN']==1


def test_independent_name_inventory_ignored():
    from io import BytesIO
    from openpyxl import load_workbook
    gb,eb=inputs([('a','ACGTCAGT','A')],[('P',[{'sequence':'GGGGCCCC'}])])
    book=load_workbook(BytesIO(eb));ws=book.create_sheet('aptamer_name');ws.append(['pk','value']);ws.append(['P','["A"]'])
    out=BytesIO();book.save(out)
    r=evaluate(gb,out.getvalue());assert not r.extractors[0].name and not r.candidates[0].name_support
