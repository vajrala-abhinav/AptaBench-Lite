"""Metrics over fixed associations. Never imports resolver/alignment."""
from .performance import timed
from .models import base_run,associations,ReviewedRun

CAVEAT=('All sequences (closed-world): This score checks every unique extractor prediction against the significant gold reference only. '
'Extractors can report more sequences than the significant gold set contains, including legitimate sequences outside this reference. '
'Those additional predictions lower closed-world precision and F1 by design; they are not independently verified biological false positives. '
'Unresolved manual-review candidates count as unconfirmed recoveries until adjudicated.')


@timed("sequence_scoring")
def compute_metrics(value,population='all',tolerance='adaptive',sequence_scope='core',paper_id=None):
    if population not in ('all','matched') or tolerance not in ('strict','adaptive') or sequence_scope not in ('core','whole'):
        raise ValueError('Unknown scoring view')
    run=base_run(value);papers=[p for p in run.papers if p.attempted and (paper_id is None or p.id==paper_id)]
    gs={g for p in papers for g in p.gold_ids};es={e for p in papers for e in p.logical_extractor_ids}
    pairs=[a for a in associations(value) if a.gold_id in gs and a.extractor_id in es]
    candidates={c.id:c for c in run.candidates}
    passing=[a for a in pairs if candidates[a.candidate_id].passes(tolerance,sequence_scope)]
    G,E,M,T=len(gs),len(es),len(pairs),len(passing)
    missing=set(value.missing) if isinstance(value,ReviewedRun) else set()
    pending=len(gs-{a.gold_id for a in pairs}-missing)
    div=lambda n,d:n/d if d else None
    precision=div(T,E) if population=='all' else div(T,M)
    recall=div(T,G) if population=='all' else div(T,M)
    f1=div(2*T,E+G) if population=='all' else div(T,M)
    raw_ids={e for p in papers for e in p.extractor_ids}
    parseable_raw=sum(e.id in raw_ids and bool(e.sequence.canonical) for e in run.extractors)
    groups=[d for d in run.duplicates if any(p.id==d.paper_id for p in papers)]
    unscoreable=[g.id for g in run.gold if g.significant and not g.sequence.canonical and any(p.id==g.paper_id for p in papers)]
    return dict(population=population,tolerance=tolerance,sequence_scope=sequence_scope,review_mode='effective' if isinstance(value,ReviewedRun) and value.events else 'automatic',
        G=G,E=E,M=M,T=T,TP=T,
        E_raw=len(raw_ids),E_parseable_raw=parseable_raw,E_unique=len(groups),E_logical=E,E_invalid=len(raw_ids)-parseable_raw,
        multiplicity_exception_count=sum(len(d.representatives)-1 for d in groups),FP=E-T if population=='all' else M-T,FN=G-T if population=='all' else M-T,
        precision=precision,recall=recall,f1=f1,matched_correctness=div(T,M),significant_recovery=div(T,G),
        pending_gold=pending,unverified_extractor=E-M,significant_unscoreable=len(unscoreable),
        significant_all=G+len(unscoreable),unattempted_papers=sum(not p.attempted for p in run.papers),
        attempted_papers=len(papers),passing_gold_ids=[a.gold_id for a in passing],
        n_raw_extractor=sum(len(p.extractor_ids) for p in papers),
        duplicate_suppressed=sum(len(d.members)-len(d.representatives) for d in run.duplicates if any(p.id==d.paper_id for p in papers)),
        numerators={'precision':[T,E if population=='all' else M],'recall':[T,G if population=='all' else M],
                    'f1':[2*T,E+G] if population=='all' else [T,M]},provisional=pending>0,
        notes=CAVEAT if population=='all' else 'Conditional paired correctness; recovery is reported separately.')


def paper_status(value,paper):
    metrics=compute_metrics(value,paper_id=paper.id)
    unscoreable=metrics['significant_unscoreable']
    return 'UNATTEMPTED_PAPER' if not paper.attempted else 'REVIEW_COMPLETE' if metrics['pending_gold']==0 and not unscoreable else 'MANUAL_REVIEW'


def review_diagnostics(value, paper_id=None):
    """Gold-level abstention inventory, counting each reason once per unresolved gold.

    Descriptive only: it does not infer which candidate is biologically correct,
    calculate hypothetical TPs, or modify any association or score.
    """
    from collections import Counter
    run = base_run(value)
    matched = {a.gold_id for a in associations(value)}
    missing = set(value.missing) if isinstance(value, ReviewedRun) else set()
    decision = {d.gold_id: d for d in run.decisions}
    eligible = {g for p in run.papers if p.attempted and (paper_id is None or p.id == paper_id)
                for g in p.gold_ids}
    blocked = sorted(eligible - matched - missing)
    counts = Counter()
    for gid in blocked:
        for reason in set(decision[gid].reasons):
            counts[reason] += 1
    return {
        "unresolved_gold": len(blocked),
        "gold_ids": blocked,
        "reason_counts": sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])),
        "interpretation": "Reasons overlap. Counts are unresolved gold records, not errors or demonstrated missed matches.",
    }
