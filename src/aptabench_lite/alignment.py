"""Independent unit-cost DP. All gold bases consumed; only extractor ends free.
Trace ties prefer diagonal, then deletion, then insertion; placement ambiguity
tracks ALL minimum-distance intervals, independent of chosen display traceback.
"""
from functools import lru_cache
from math import isqrt
from .models import Trace
from .performance import timed


def budget(length):
    if type(length) is not int or length < 1:raise ValueError("Gold length must be positive integer")
    return max(1,min(4,isqrt(length//9)))


@lru_cache(maxsize=8192)
@timed("sequence_alignment")
def align(gold: str, extractor: str, mode="core") -> Trace:
    if not gold or not extractor:raise ValueError("Alignment requires nonempty canonical sequences")
    if mode not in ("core","whole"):raise ValueError("Unknown alignment mode")
    n,m=len(gold),len(extractor)
    if gold==extractor:
        return Trace(gold,extractor,("MATCH",)*n,0,0,n,0,m,"","",1,mode)
    if n*m>4_000_000:raise ValueError("Alignment exceeds 4 million cells; inspect sequence lengths (no records skipped).")
    free=mode=="core"
    prev=[0]*(m+1) if free else list(range(m+1))
    pointers=[bytearray(m+1) for _ in range(n+1)]
    prev_matches=[0]*(m+1)
    starts=[1<<j for j in range(m+1)] if free else [1]*(m+1)
    for j in range(1,m+1):pointers[0][j]=3
    for i,g in enumerate(gold,1):
        row=[i]+[0]*m; matches=[0]*(m+1); masks=[1]+[0]*m; pointers[i][0]=2
        for j,e in enumerate(extractor,1):
            costs=(prev[j-1]+(g!=e),prev[j]+1,row[j-1]+1)
            best=min(costs); row[j]=best
            match_counts=(prev_matches[j-1]+(g==e),prev_matches[j],matches[j-1])
            chosen=min(range(3),key=lambda k:(costs[k],-match_counts[k],k))
            pointers[i][j]=chosen+1;matches[j]=match_counts[chosen]
            if free:
                masks[j]=(starts[j-1] if costs[0]==best else 0)|(starts[j] if costs[1]==best else 0)|(masks[j-1] if costs[2]==best else 0)
        prev,starts,prev_matches=row,masks,matches
    end=min(range(m+1),key=lambda j:(prev[j],-prev_matches[j],j)) if free else m
    distance=prev[end]
    count=sum(starts[j].bit_count() for j in range(m+1) if prev[j]==distance) if free else 1
    i,j=n,end; ag=[];ae=[];ops=[]
    while i or (j and not free):
        p=pointers[i][j]
        if p==1:
            ag.append(gold[i-1]);ae.append(extractor[j-1]);ops.append("MATCH" if gold[i-1]==extractor[j-1] else "SUBSTITUTION");i-=1;j-=1
        elif p==2:ag.append(gold[i-1]);ae.append("-");ops.append("DELETION");i-=1
        else:ag.append("-");ae.append(extractor[j-1]);ops.append("INSERTION");j-=1
    left,right=extractor[:j],extractor[end:]
    ag="-"*len(left)+"".join(reversed(ag))+"-"*len(right)
    ae=left+"".join(reversed(ae))+right
    ops=("FREE_EXTRACTOR_FLANK",)*len(left)+tuple(reversed(ops))+("FREE_EXTRACTOR_FLANK",)*len(right)
    trace=Trace(ag,ae,ops,distance,0,n,j,end,left,right,count,mode)
    assert sum(trace.counts[x] for x in ("SUBSTITUTION","INSERTION","DELETION"))==distance
    assert trace.aligned_gold.replace("-","")==gold
    assert trace.aligned_extractor.replace("-","")==extractor
    return trace
