from collections import defaultdict,Counter
from hashlib import sha256
from .models import DuplicateGroup
from .normalization import name_key


def group_duplicates(paper_id,golds,extractors):
    groups=defaultdict(list);logical=[];result=[]
    gold_counts=Counter(g.sequence.canonical for g in golds)
    for e in extractors:
        if e.sequence.canonical:groups[e.sequence.canonical].append(e)
    for seq,members in sorted(groups.items()):
        ids=tuple(sorted(e.id for e in members))
        multiplicity=gold_counts[seq]>1
        names={name_key(e.name) for e in members if e.name}
        conflict=len(names)>1
        retained=ids if multiplicity else ids[:1]
        logical.extend(retained)
        result.append(DuplicateGroup('D-'+sha256((paper_id+'|'+seq).encode()).hexdigest()[:16],paper_id,seq,ids,retained,conflict,multiplicity))
    return tuple(result),tuple(sorted(logical))
