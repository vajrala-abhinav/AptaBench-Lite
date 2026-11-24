from dataclasses import asdict
import pytest
from aptabench_lite.scoring import compute_metrics
from aptabench_lite.alignment import align
from aptabench_lite.engine import evaluate
from conftest import inputs


def test_S01_strict(make_run):
    r=make_run([('g','ACGTCAGT')],[('P',[{'sequence':'acgt cagt'}])])
    assert len(r.automatic)==1 and r.automatic[0].origin=='MATCHED_STRICT'
    for t in ('strict','adaptive'):
        for s in ('whole','core'):assert compute_metrics(r,tolerance=t,sequence_scope=s)['T']==1


def test_S02_S04_unique_core(make_run):
    r=make_run([('g','ACGTCAGT')],[('P',[{'sequence':'TTACGTCAGTGG'}])])
    assert len(r.automatic)==1
    assert compute_metrics(r,tolerance='strict')['T']==1
    assert compute_metrics(r,tolerance='strict',sequence_scope='whole')['T']==0


def test_S03_40_84(make_run):
    core='ACGTCAGTGGACCTGATCGATGCTACGTAGCTGATCGTAC'
    full='T'*22+core+'G'*22
    r=make_run([('core',core),('full',full)],[('P',[{'sequence':full},{'sequence':core}])])
    assert len(r.automatic)==2 and compute_metrics(r)['T']==2
    assert all(c.whole.distance==0 for c in r.candidates if c.id in {a.candidate_id for a in r.automatic})
    assert any(c.stage=='PREEMPTED_BY_STRICT_ANCHOR' for c in r.candidates)


def test_S05_S06_one_edit_eight(make_run):
    for seq in ('ACGCAGT','ACGACAGT'):
        r=make_run([('g','ACGTCAGT')],[('P',[{'sequence':seq,'name':'A'}])])
        assert r.candidates[0].core.distance==1 and r.candidates[0].budget==1
        assert len(r.automatic)==1
        assert compute_metrics(r,tolerance='strict')['T']==0


def test_S09_outside(make_run):
    r=make_run([('g','ACGTCAGT')],[('P',[{'sequence':'ACAACTGT'}])])
    assert not r.automatic and 'OUTSIDE_TOLERANCE_REVIEW' in r.candidates[0].reasons


def test_S10_S29_repeated(make_run):
    r=make_run([('g','ACGACG')],[('P',[{'sequence':'TTACGACGACGGG'}])])
    assert not r.automatic and r.candidates[0].core.optimal_interval_count>1


def test_S11_S13_S14_multiplicity(make_run):
    r=make_run([('a','ACGTCAGT'),('b','ACGTCAGT')],[('P',[{'sequence':'ACGTCAGT'},{'sequence':'ACGTCAGT'}])])
    assert not r.automatic and len(r.papers[0].logical_extractor_ids)==2
    assert 'GOLD_IDENTICAL_CONFLICT' in r.candidates[0].reasons
    r=make_run([('a','ACGTCAGT')],[('P',[{'sequence':'ACGTCAGT'},{'sequence':'acgtcagt'},{'sequence':'ACGACAGT'}])])
    assert len(r.extractors)==3 and len(r.papers[0].logical_extractor_ids)==2
    assert compute_metrics(r)['duplicate_suppressed']==1


def test_S15_duplicate_names(make_run):
    r=make_run([('a','ACGTCAGT','A')],[('P',[{'sequence':'ACGTCAGT','name':'A'},{'sequence':'ACGTCAGT','name':'B'}])])
    assert not r.automatic and any(d.name_conflict for d in r.duplicates)


def test_S16_S18_names(make_run):
    r=make_run([('a','ACGTCAGT','DUX4')],[('P',[{'sequence':'ACGACAGT','name':'DUX4'}])])
    assert r.automatic and r.candidates[0].name_support
    r=make_run([('a','ACGTCAGT','APT7'),('b','TGTACGCA','DUX4')],[('P',[{'sequence':'ACGTCAGT','name':'DUX4'}])])
    assert not r.automatic and any(c.name_conflict for c in r.candidates)


def test_S12_S20_ambiguous_near_gold(make_run):
    r=make_run([('a','ACGTCAGT'),('b','ACGCCAGT')],[('P',[{'sequence':'ACGACAGT'}])])
    assert not r.automatic
    assert any('GOLD_NEAR_DUPLICATE' in c.reasons for c in r.candidates)
    assert any('EQUIVALENT_GLOBAL_ASSIGNMENT' in d.reasons for d in r.decisions)


def test_S19_conditional_global(make_run):
    r=make_run([('a','ACGTCAGT')],[('P',[{'sequence':'TTACGTCAGTGG'},{'sequence':'ACGTCAGTG'}])])
    assert len(r.automatic)==1
    chosen=next(c for c in r.candidates if c.id==r.automatic[0].candidate_id)
    assert chosen.whole.distance==1 and 'GLOBAL_TIEBREAK_ACTIVATED' in chosen.reasons


def test_S21_context_runnerup(make_run):
    r=make_run([('a','ACGTCAGT'),('b','TGCACGTA')],[('P',[{'sequence':'ACGTCAGTTGCACGTA'},{'sequence':'ACGTCAGTG'}])])
    assert len(r.automatic)==2 and len({a.extractor_id for a in r.automatic})==2


def test_S24_S25_empty_unattempted(make_run):
    r=make_run([('a','ACGTCAGT'),('b','AGTC','', 'significant_sequence','Q')],[('P',[])])
    m=compute_metrics(r);assert (m['G'],m['E'],m['FN'],m['f1'],m['precision'])==(1,0,1,0,None)
    assert m['unattempted_papers']==1


def test_significant_only_no_forcing(make_run):
    r=make_run([('a','ACGTCAGT'),('b','TGCACGTA','','non_significant_sequence')],[('P',[{'sequence':'TGCACGTA'},{'sequence':'CCCCGGGG'}])])
    assert not r.automatic and {c.gold_id for c in r.candidates}=={'a'}
    assert compute_metrics(r)['E']==2 and compute_metrics(r)['G']==1


def test_S26_alias_collision(make_run):
    r=make_run([('a','ACGT','','significant_sequence','P','same.pdf'),('b','ACGT','','significant_sequence','Q','same.pdf')],[('same', [{'sequence':'ACGT'}])])
    assert not r.candidates and not r.automatic and any(d.code=='PAPER_LINK_AMBIGUOUS' for d in r.diagnostics)


def test_S27_literal_TU_RC(make_run):
    r=make_run([('a','ACGT')],[('P',[{'sequence':'ACGU'}])])
    assert compute_metrics(r,tolerance='strict')['T']==0
    r=make_run([('a','AACCGT')],[('P',[{'sequence':'ACGGTT'}])])
    assert compute_metrics(r,tolerance='strict')['T']==0


def test_S30_permutation_and_cache(make_run):
    gs=[('a','ACGTCAGT'),('b','TGCACGTA')];es=[{'sequence':'ACGTCAGTG'},{'sequence':'TGCACGTA'}]
    a=make_run(gs,[('P',es)]);align.cache_clear();b=make_run(gs[::-1],[('P',es[::-1])])
    assert a.automatic==b.automatic and a.decisions==b.decisions
    assert compute_metrics(a)==compute_metrics(b)
