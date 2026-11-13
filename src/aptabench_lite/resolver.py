"""Exact one-to-one resolver with optional unmatched nodes and bounded stability.
Priority: local-name support, cardinality, total full-gold completion; only in
contested graphs, total global completion. Integer lexicographic encoding uses
exact fractions, no confidence weights or arbitrary acceptance margin.
"""
from collections import Counter
from dataclasses import replace
from fractions import Fraction
from math import lcm
from .models import Association,Decision


def maximize(matrix):
    """Rectangular primal-dual assignment, arbitrary-size integer weights."""
    if not matrix:return []
    n,m=len(matrix),len(matrix[0]);u=[0]*(n+1);v=[0]*(m+1);p=[0]*(m+1);way=[0]*(m+1)
    for row in range(1,n+1):
        p[0]=row;col=0;minimum=[None]*(m+1);used=[False]*(m+1)
        while True:
            used[col]=True;active=p[col];delta=None;next_col=0
            for j in range(1,m+1):
                if used[j]:continue
                reduced=-matrix[active-1][j-1]-u[active]-v[j]
                if minimum[j] is None or reduced<minimum[j]:minimum[j]=reduced;way[j]=col
                if delta is None or minimum[j]<delta:delta=minimum[j];next_col=j
            for j in range(m+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                elif minimum[j] is not None:minimum[j]-=delta
            col=next_col
            if p[col]==0:break
        while col:
            before=way[col];p[col]=p[before];col=before
    result=[-1]*n
    for j in range(1,m+1):
        if p[j]:result[p[j]-1]=j-1
    return result


def resolve(golds,extractors,candidates):
    candidates=list(candidates);gids=sorted(g.id for g in golds);eids=sorted(e.id for e in extractors)
    exact=[c for c in candidates if c.whole.distance==0]
    gc=Counter(c.gold_id for c in exact);ec=Counter(c.extractor_id for c in exact)
    anchors=[c for c in exact if c.viable and gc[c.gold_id]==1 and ec[c.extractor_id]==1]
    # An item named for G1 but equal to G2 is a material conflict for both hypotheses.
    conflicted_e={c.extractor_id for c in candidates if c.name_conflict and c.whole.distance==0}
    anchors=[c for c in anchors if c.extractor_id not in conflicted_e]
    locked_g={c.gold_id for c in anchors};locked_e={c.extractor_id for c in anchors}
    remaining=[c for c in candidates if c.gold_id not in locked_g and c.extractor_id not in locked_e and c.viable and c.extractor_id not in conflicted_e]
    gs=[x for x in gids if x not in locked_g];es=[x for x in eids if x not in locked_e]
    gd=Counter(c.gold_id for c in remaining);ed=Counter(c.extractor_id for c in remaining)
    contested={c.id for c in remaining if gd[c.gold_id]>1 or ed[c.extractor_id]>1}
    scale=lcm(*(len(g.sequence.canonical) for g in golds)) if golds else 1
    bound=max(1,len(gs))*scale; radix=bound+1
    lookup={(c.gold_id,c.extractor_id):c for c in remaining}
    def matrix(tiebreak):
        result=[]
        for g in gs:
            row=[]
            for e in es:
                c=lookup.get((g,e))
                if not c:row.append(-1);continue
                length=c.core.gold_end
                core=(length-c.core.distance)*scale//length
                glob=max(0,length-c.whole.distance)*scale//length if tiebreak and c.id in contested else 0
                row.append(((int(c.name_support)*radix+scale)*radix+core)*radix+glob)
            result.append(row+[0]*len(gs))
        return result
    def solve(weights):
        indices=maximize(weights)
        chosen=[lookup[gs[i],es[j]] for i,j in enumerate(indices) if j<len(es) and weights[i][j]>0]
        total=sum(weights[i][j] for i,j in enumerate(indices))
        return chosen,total
    base,_=solve(matrix(False));weights=matrix(True);preferred,total=solve(weights)
    unstable=set()
    for edge in preferred:
        i,j=gs.index(edge.gold_id),es.index(edge.extractor_id)
        altered=[r[:] for r in weights];altered[i][j]=-1
        alternative,score=solve(altered)
        if score==total:
            unstable.add(edge.id)
            # Only fixed edges across all optima may survive. Forbidding each
            # selected edge separately is sufficient to test that invariant.
    accepted=[]
    for c in anchors:accepted.append(Association(c.gold_id,c.extractor_id,c.id,'MATCHED_STRICT',('UNIQUE_STRICT_WHOLE',)))
    base_ids={c.id for c in base};accepted_ids=set()
    for c in preferred:
        if c.id in unstable:continue
        reasons=c.reasons+('ONE_TO_ONE_UNIQUE_OPTIMUM',)
        if c.id in contested:reasons+=('GLOBAL_TIEBREAK_PREFERRED','BOUNDED_RUNNER_UP_CHECK')
        accepted.append(Association(c.gold_id,c.extractor_id,c.id,'MATCHED_CONTEXTUAL',reasons));accepted_ids.add(c.id)
    resolved={a.gold_id:a for a in accepted};decisions=[]
    for g in golds:
        if g.id in resolved:decisions.append(Decision(g.id,resolved[g.id].origin,resolved[g.id].reasons));continue
        edges=[c for c in candidates if c.gold_id==g.id]
        reasons=set(r for c in edges for r in c.reasons)
        if any(c.id in contested for c in edges):reasons.add('CONTESTED_EXTRACTOR')
        if any(c.id in unstable for c in edges) or any(c.gold_id==g.id for c in remaining):
            reasons.update(('EQUIVALENT_GLOBAL_ASSIGNMENT','GLOBAL_TIEBREAK_INCONCLUSIVE'))
        if not edges:reasons.add('NO_EXTRACTOR_CANDIDATE')
        decisions.append(Decision(g.id,'MANUAL_REVIEW' if edges else 'UNMATCHED_GOLD',tuple(sorted(reasons))))
    annotated=[]
    for c in candidates:
        reasons=c.reasons;stage='S3'
        if c in anchors:stage='S1'
        elif c.gold_id in locked_g or c.extractor_id in locked_e:stage='PREEMPTED_BY_STRICT_ANCHOR';reasons+=('STRICT_ANCHOR_PREEMPTED',)
        elif c.name_support:stage='S2+S3'
        if c.id in contested:reasons+=('CONTESTED_EXTRACTOR','GLOBAL_TIEBREAK_ACTIVATED')
        if c.id in unstable:reasons+=('EQUIVALENT_GLOBAL_ASSIGNMENT',)
        annotated.append(replace(c,reasons=reasons,stage=stage))
    return tuple(accepted),tuple(decisions),tuple(annotated)
