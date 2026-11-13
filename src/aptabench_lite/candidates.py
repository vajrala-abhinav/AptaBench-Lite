from .alignment import align,budget
from .models import Candidate
from .normalization import name_key


def repeated(seq):
    """Exact repeated motif diagnostic; no entropy/length confidence threshold."""
    return len(seq)>1 and seq in (seq+seq)[1:-1]


def compare(g,e,duplicate_conflict=False,identical_gold=False,near_duplicate=False):
    core=align(g.sequence.canonical,e.sequence.canonical,'core')
    whole=align(g.sequence.canonical,e.sequence.canonical,'whole')
    b=budget(len(g.sequence.canonical));gn,en=name_key(g.name),name_key(e.name)
    support=bool(gn and en and gn==en)
    conflict=bool(gn and en and gn!=en)
    reasons=[]
    if support:reasons.append('NAME_EXACT_SEQUENCE_LOCAL')
    if conflict:reasons.append('NAME_SEQUENCE_CONFLICT')
    if duplicate_conflict:reasons.append('DUPLICATE_NAME_CONFLICT')
    if identical_gold:reasons.append('GOLD_IDENTICAL_CONFLICT')
    if near_duplicate:reasons.append('GOLD_NEAR_DUPLICATE')
    if core.distance==0:reasons.append('EXACT_FITTED_CORE')
    if core.optimal_interval_count>1:reasons.append('MULTIPLE_EQUAL_FITS')
    if core.distance>b:reasons.append('OUTSIDE_TOLERANCE_REVIEW')
    if g.sequence.status!='valid' or e.sequence.status!='valid':reasons.append('AMBIGUOUS_ALPHABET_REVIEW')
    # Unsupported qualitative identity cases in §24 abstain. Exact whole anchoring
    # remains permitted; no arbitrary short-length threshold is introduced.
    motif=(repeated(g.sequence.canonical) and whole.distance!=0 and not support)
    if motif:reasons.append('NONDISCRIMINATIVE_REPEATED_CORE')
    viable=not(conflict or duplicate_conflict or identical_gold or motif or
        g.sequence.status!='valid' or e.sequence.status!='valid' or core.distance>b or
        (core.optimal_interval_count>1 and whole.distance!=0 and not support))
    return Candidate(f'C:{g.id}:{e.id}',g.paper_id,g.id,e.id,core,whole,b,support,conflict,viable,tuple(reasons))
