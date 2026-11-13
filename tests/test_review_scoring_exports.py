from dataclasses import asdict
from io import BytesIO
import json
import pytest
from openpyxl import load_workbook
from aptabench_lite.review import commit_event,export_review,import_review,save_review
from aptabench_lite.scoring import compute_metrics,paper_status
from aptabench_lite.exports import export_workbook,export_audit
from aptabench_lite.models import ReviewedRun


def review_fixture(make_run):
    return make_run([('a','ACGTCAGT'),('b','TGCACGTA')],[('P',[{'sequence':'ACGTCAGT'},{'sequence':'TGCACGTA'},{'sequence':'CCCCGGGG'}])])


def test_M05_bad_sequence_confirmation(make_run):
    r=make_run([('g','ACGTCAGT')],[('P',[{'sequence':'GGGGCCCC'}])]);before=asdict(r)
    v=commit_event(r,'CONFIRM_ASSOCIATION','PI','g',r.extractors[0].id)
    m=compute_metrics(v);assert (m['M'],m['T'],m['FP'],m['FN'])==(1,0,1,1)
    assert compute_metrics(v,'matched')['matched_correctness']==0
    assert asdict(r)==before
    assert import_review(r,export_review(v))==v


def test_M06_M07_M08_M09(make_run):
    r=review_fixture(make_run);a,b=r.automatic;old=asdict(r)
    v=commit_event(r,'REJECT_PAIR','PI',a.gold_id,a.extractor_id)
    assert len(v.associations)==1 and len(r.candidates)==6
    v=commit_event(v,'MARK_GOLD_MISSING','PI',a.gold_id)
    assert compute_metrics(v)['FN']==1
    with pytest.raises(ValueError,match='Conflict'):commit_event(v,'CONFIRM_ASSOCIATION','PI',a.gold_id,b.extractor_id)
    with pytest.raises(ValueError):commit_event(v,'REASSIGN','PI',a.gold_id,b.extractor_id)
    v=commit_event(v,'REASSIGN','PI',a.gold_id,b.extractor_id,note='Identity corrected',confirmed=True)
    assert len(v.associations)==1 and v.associations[0].gold_id==a.gold_id and not v.missing
    v=commit_event(v,'UNDO','PI',target_revision=3)
    assert a.gold_id in v.missing and v.associations[0]==b
    v=commit_event(v,'UNDO','PI',target_revision=2)
    v=commit_event(v,'UNDO','PI',target_revision=1)
    assert v.associations==r.automatic and asdict(r)==old


def test_M10_checksum_fingerprint_concurrency(make_run,tmp_path):
    r=review_fixture(make_run);a=r.automatic[0];v=commit_event(r,'REJECT_PAIR','PI',a.gold_id,a.extractor_id)
    file=tmp_path/'review.json';save_review(v,file,expected_revision=0)
    assert import_review(r,file.read_bytes())==v
    with pytest.raises(ValueError,match='changed'):save_review(v,file,expected_revision=0)
    bad=json.loads(export_review(v));bad['payload']['events'][0]['note']='tampered'
    with pytest.raises(ValueError,match='checksum'):import_review(r,json.dumps(bad).encode())
    other=make_run([('g','ACGT')],[('P',[])])
    with pytest.raises(ValueError,match='mismatch'):import_review(other,export_review(v))
    with pytest.raises(ValueError,match='changed'):commit_event(v,'LEAVE_UNRESOLVED','PI',a.gold_id,expected_revision=0)


def test_M16_toggle_invariance(make_run,monkeypatch):
    r=review_fixture(make_run);before=asdict(r)
    import aptabench_lite.alignment as alignment
    monkeypatch.setattr(alignment,'align',lambda *a:pytest.fail('Rematched during scoring/export/review'))
    for p in ('all','matched'):
        for t in ('strict','adaptive'):
            for s in ('whole','core'):
                m=compute_metrics(r,p,t,s);assert m['M']==2
                assert load_workbook(BytesIO(export_workbook(r,m))).sheetnames
    assert asdict(r)==before


def test_M01_M02_numerical_contract(make_run):
    # Install four explicit associations in a 5-gold/8-prediction population.
    gs=[('g'+str(i),s) for i,s in enumerate(['ACGTCAGT','TGCACGTA','CGTAGTCA','GACTCGAT','GGTACCTA'])]
    seqs=['ACGTCAGT','TGCACGTA','CGTAGTCA','TTGACTCGATGG','AAAAAAAA','CCCCCCCC','GGGGGGGG','TTTTTTTT']
    r=make_run(gs,[('P',[{'sequence':s} for s in seqs])])
    assert len(r.automatic)==4
    m=compute_metrics(r);assert (m['G'],m['E'],m['M'],m['T'],m['TP'],m['FP'],m['FN'])==(5,8,4,4,4,4,1)
    assert m['precision']==.5 and m['recall']==.8 and m['f1']==pytest.approx(8/13)
    assert compute_metrics(r,'matched')['matched_correctness']==1
    m=compute_metrics(r,tolerance='strict',sequence_scope='whole');assert (m['T'],m['FP'],m['FN'])==(3,5,2)
    assert m['f1']==pytest.approx(6/13)


def test_M13_no_matches(make_run):
    r=make_run([('g','ACGT')],[('P',[])])
    assert compute_metrics(r,'matched')['f1'] is None


def test_M15_exports_trace_injection(make_run):
    r=make_run([('=gold','ACGTCAGT','=formula')],[('P',[{'sequence':'ACGTCAGT'}])])
    data=export_workbook(r);b=load_workbook(BytesIO(data),rich_text=True)
    assert {'Overview','Sequence','Review History','Run Info','Alignment Detail','Validation'}<=set(b.sheetnames)
    assert b['Sequence']['B2'].value=='=gold' and b['Sequence']['B2'].data_type=='s'
    c=next(c for c in r.candidates if c.id==r.automatic[0].candidate_id)
    assert str(b['Alignment Detail']['C2'].value)==c.core.aligned_gold
    assert json.loads(b['Alignment Detail']['D2'].value)==list(c.core.operations)
    a=json.loads(export_audit(r));assert a['effective_metrics']['all/adaptive/core']['T']==1
    assert a['run']['candidates'][0]['core']['operations']==list(c.core.operations)


def test_M04_confirm_within_tolerance_changes_only_overlay(make_run):
    r=make_run([('a','ACGTCAGT'),('b','ACGCCAGT')],[('P',[{'sequence':'ACGACAGT'}])])
    assert not r.automatic
    v=commit_event(r,'CONFIRM_ASSOCIATION','PI','a',r.extractors[0].id)
    assert compute_metrics(v)['T']==1 and compute_metrics(r)['T']==0
    assert v.run is r


def test_M12_empty_significant_population(make_run):
    r=make_run([('a','ACGT','','non_significant_sequence')],[('P',[])])
    m=compute_metrics(r);assert m['G']==0 and m['significant_recovery'] is None and m['f1'] is None


def test_invalid_review_schema_rejected(make_run):
    from hashlib import sha256
    from aptabench_lite.review import canonical
    r=review_fixture(make_run);a=r.automatic[0];v=commit_event(r,'REJECT_PAIR','PI',a.gold_id,a.extractor_id)
    data=json.loads(export_review(v));data['payload']['events'][0]['reviewer']=123
    data['sha256']=sha256(canonical(data['payload'])).hexdigest()
    with pytest.raises(ValueError,match='types'):import_review(r,json.dumps(data).encode())
    for raw in (b'[]',b'{"payload":[]}',b'not json'):
        with pytest.raises(ValueError):import_review(r,raw)


def test_cross_paper_review_and_invalid_undo(make_run):
    r=make_run([('a','ACGT','','significant_sequence','P'),('b','TGCA','','significant_sequence','Q')],[('P',[{'sequence':'ACGT'}]),('Q',[{'sequence':'TGCA'}])])
    e=next(e for e in r.extractors if e.paper_id=='Q')
    with pytest.raises(ValueError,match='Cross-paper'):commit_event(r,'CONFIRM_ASSOCIATION','PI','a',e.id)
    with pytest.raises(ValueError):commit_event(r,'UNDO','PI',target_revision=1)


def test_html_excel_exact_colors_and_trace(make_run):
    from aptabench_lite.presentation import COLORS
    r=make_run([('a','ACGTCAGT')],[('P',[{'sequence':'TTACGTCAGTGG'}])])
    b=load_workbook(BytesIO(export_workbook(r)));trace=r.candidates[0].core
    for j,(char,op) in enumerate(zip(trace.aligned_gold,trace.operations),3):
        cell=b['Alignment Cells'].cell(2,j)
        assert cell.value==char and cell.fill.fgColor.rgb[-6:]==COLORS[op][1:]
