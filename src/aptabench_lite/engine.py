"""UI-independent evaluate API. No output writes, source mutations or network calls."""
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from itertools import combinations
import json
import platform
import subprocess
from pathlib import Path
from time import perf_counter
from . import POLICY_VERSION,__version__
from .alignment import align,budget
from .config import RunConfig
from .readers import source_bytes,ingest
from .duplicates import group_duplicates
from .candidates import compare
from .resolver import resolve,strict_anchors
from .normalization import name_key
from .models import EvaluationRun,Paper,Decision,Diagnostic


def evaluate(gold_file,extractor_file,config=None):
    config=config or RunConfig()
    if isinstance(config,dict):config=RunConfig(**config)
    start=perf_counter();gb,eb=source_bytes(gold_file),source_bytes(extractor_file)
    gh,eh=sha256(gb).hexdigest(),sha256(eb).hexdigest()
    read_timings={};gold,ext,attempted,diags=ingest(gb,eb,config,read_timings);parsed=perf_counter();diags=list(diags)
    assignment_s=0;comparison_s=0
    papers=[];duplicates=[];candidates=[];automatic=[];decisions=[];dp_before=align.cache_info().misses
    for pid in sorted({g.paper_id for g in gold}):
        all_g=[g for g in gold if g.paper_id==pid]
        gs=[g for g in all_g if g.significant and g.sequence.canonical]
        es=[e for e in ext if e.paper_id==pid]
        groups,logical=group_duplicates(pid,gs,es)
        duplicates.extend(groups)
        papers.append(Paper(pid,tuple(sorted({g.paper_key for g in all_g if g.paper_key})),pid in attempted,
            tuple(sorted(g.id for g in gs)),tuple(sorted(e.id for e in es)),logical))
        if pid not in attempted:
            decisions.extend(Decision(g.id,'UNATTEMPTED_PAPER',('PAPER_UNATTEMPTED',)) for g in gs);continue
        active=[e for e in es if e.id in logical];count=Counter(g.sequence.canonical for g in gs)
        near=set();comparison_start=perf_counter()
        for a,b in combinations(gs,2):
            d=align(a.sequence.canonical,b.sequence.canonical,'whole').distance
            if d<=max(budget(len(a.sequence.canonical)),budget(len(b.sequence.canonical))):
                near.update((a.id,b.id));diags.append(Diagnostic('GOLD_NEAR_DUPLICATE',f'{a.id} vs {b.id}: global distance {d}',record_id=a.id))
        conflicts={eid for group in groups if group.name_conflict for eid in group.members}
        # S1 compares strict whole equality before any nonexact identity pass.
        by_pair={}
        def comparison(g,e):
            pair=(g.id,e.id)
            if pair not in by_pair:
                by_pair[pair]=compare(g,e,e.id in conflicts,count[g.sequence.canonical]>1,g.id in near)
        for g in gs:
            for e in active:
                if g.sequence.canonical==e.sequence.canonical:comparison(g,e)
        anchors,_=strict_anchors(tuple(by_pair.values()))
        locked_g={a.gold_id for a in anchors};locked_e={a.extractor_id for a in anchors}
        remaining_g=[g for g in gs if g.id not in locked_g];remaining_e=[e for e in active if e.id not in locked_e]
        # S2 named mini-pass shares exactly the S3 distance/trace provider.
        for g in remaining_g:
            for e in remaining_e:
                if name_key(g.name) and name_key(g.name)==name_key(e.name):comparison(g,e)
        # S3 exhaustive remaining graph; no assignment occurs in the loop.
        for g in remaining_g:
            for e in remaining_e:comparison(g,e)
        # Counterfactual/preempted comparisons are for inspection only; locked
        # endpoints stay excluded from every later solver stage.
        for g in gs:
            for e in active:comparison(g,e)
        edges=list(by_pair.values())
        comparison_s+=perf_counter()-comparison_start
        assignment_start=perf_counter();pairs,status,edges=resolve(gs,active,edges);assignment_s+=perf_counter()-assignment_start
        automatic.extend(pairs);decisions.extend(status);candidates.extend(edges)
    try:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[2],stderr=subprocess.DEVNULL,text=True).strip()
    except (OSError,subprocess.CalledProcessError):commit='unavailable'
    metadata={'python':platform.python_version(),'app_version':__version__,'git_commit':commit,
              'packages':{p:version(p) for p in ('aptabench-lite','openpyxl','streamlit','xlsxwriter')},
              'scope':'significant_only','orientation':'forward','duplicates':'strict canonical unique; retain raw capacity for identical golds',
              'normalization':'ASCII case/whitespace and paired terminal labels only; IUPAC literal review; no T/U conversion',
              'budget':'max(1,min(4,isqrt(L//9)))','solver':'exact lexicographic; names/cardinality/core/global; forbid-edge stability',
              'unscoreable_policy':'missing/unsupported canonical references excluded from G; ambiguous literal bases retained with manual review'}
    rid=sha256((gh+eh+config.to_json()+POLICY_VERSION+__version__).encode()).hexdigest()
    run=EvaluationRun(rid,'lite-1',POLICY_VERSION,gh,eh,config.to_json(),json.dumps(metadata,sort_keys=True),
        tuple(sorted(gold,key=lambda r:r.id)),tuple(sorted(ext,key=lambda r:r.id)),tuple(papers),tuple(duplicates),
        tuple(sorted(candidates,key=lambda c:c.id)),tuple(sorted(automatic,key=lambda a:a.gold_id)),tuple(sorted(decisions,key=lambda d:d.gold_id)),tuple(diags),
        json.dumps({'parse_normalize_link_s':parsed-start,'normalization_s':read_timings.get('normalization_s',0),
                    'parsing_linking_s':parsed-start-read_timings.get('normalization_s',0),'alignment_comparison_s':comparison_s,'assignment_s':assignment_s,
                    'graph_alignment_assignment_s':perf_counter()-parsed,
                    'total_s':perf_counter()-start,'dp_cache_misses':align.cache_info().misses-dp_before}))
    reconcile(run)
    return run


def reconcile(run):
    gids={g.id for g in run.gold};eids={e.id for e in run.extractors}
    assert len(gids)==len(run.gold) and len(eids)==len(run.extractors)
    assert len({a.gold_id for a in run.automatic})==len(run.automatic)
    assert len({a.extractor_id for a in run.automatic})==len(run.automatic)
    lookup={c.id:c for c in run.candidates}
    for a in run.automatic:
        c=lookup[a.candidate_id];assert c.gold_id==a.gold_id and c.extractor_id==a.extractor_id and c.viable
