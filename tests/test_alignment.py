from itertools import product
from math import floor,sqrt
import pytest
from aptabench_lite.alignment import align,budget
from aptabench_lite.normalization import normalize,name_key


def distance(a,b):
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):row.append(min(prev[j]+1,row[-1]+1,prev[j-1]+(x!=y)))
        prev=row
    return prev[-1]


def test_exhaustive_fitting_against_all_substrings():
    words=[''.join(x) for n in range(1,5) for x in product('AC',repeat=n)]
    for g in words:
        for e in words:
            trace=align(g,e)
            expected=min(distance(g,e[i:j]) for i in range(len(e)+1) for j in range(i,len(e)+1))
            assert trace.distance==expected
            assert align(g,e,'whole').distance==distance(g,e)
            intervals={(i,j) for i in range(len(e)+1) for j in range(i,len(e)+1) if distance(g,e[i:j])==expected}
            assert trace.optimal_interval_count==len(intervals)
            assert trace.distance==sum(trace.counts[o] for o in ('SUBSTITUTION','INSERTION','DELETION'))


def test_budget_exact():
    for n in range(1,10001):assert budget(n)==max(1,min(4,floor(sqrt(n)/3)))
    for n in (0,-1,True,3.5):
        with pytest.raises(ValueError):budget(n)


@pytest.mark.parametrize('g,e,d,op',[('ACGTACGT','ACGACGT',1,'DELETION'),('ACTG','ACATG',1,'INSERTION'),('ACTG','ACAG',1,'SUBSTITUTION')])
def test_edits(g,e,d,op):
    t=align(g,e);assert t.distance==d and op in t.operations


def test_full_gold_and_flanks():
    t=align('ACGTCAGT','GGACGTCAGTTT');assert t.distance==0 and t.left_flank=='GG' and t.right_flank=='TT'
    assert align('ACGTCAGT','CAGT').distance>=4
    assert align('ACG','ACGACG').optimal_interval_count>1


def test_normalization():
    n=normalize(" 5′-ac gt-3' ")
    assert n.canonical=='ACGT' and ''.join(n.raw[i] for i in n.offsets).upper()=='ACGT'
    for raw in ('/5Bio/ACGT','ACG-T','ACGТ','5-ACG-3'):
        assert normalize(raw).canonical is None
    assert normalize('ACGN').status=='review'
    assert normalize('ACGTU').status=='review'
    assert normalize('ACGU').canonical=='ACGU'
    assert name_key(' HF3-58 ')!='hf3 58'
