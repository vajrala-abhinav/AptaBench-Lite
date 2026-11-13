"""Append-only identity overlay, checksummed portable state and atomic persistence."""
from dataclasses import asdict
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from .models import ReviewedRun,ReviewEvent,Association,base_run

ACTIONS={'CONFIRM_ASSOCIATION','REJECT_PAIR','MARK_GOLD_MISSING','LEAVE_UNRESOLVED','REASSIGN','UNDO'}


def apply_review_events(run,events):
    run=base_run(run);events=tuple(events)
    inactive=set()
    for i,event in enumerate(events,1):
        if not isinstance(event,ReviewEvent) or type(event.revision) is not int or event.revision!=i:raise ValueError('Review revision sequence invalid')
        if any(not isinstance(getattr(event,k),str) for k in ('action','reviewer','timestamp','gold_id','extractor_id','note')) or type(event.confirmed) is not bool:
            raise ValueError('Review event field types invalid')
        if len(event.note)>10000:raise ValueError('Review note exceeds 10000 characters')
        if event.action not in ACTIONS or not event.reviewer.strip():raise ValueError('Unknown action or missing reviewer')
        try:
            stamp=datetime.fromisoformat(event.timestamp)
            if stamp.tzinfo is None:raise ValueError('Timezone required')
        except (TypeError,ValueError) as exc:raise ValueError('Review timestamp must be timezone-aware ISO format') from exc
        if event.action=='UNDO':
            target=event.target_revision
            if type(target) is not int or not 1<=target<i or target in inactive or events[target-1].action=='UNDO':
                raise ValueError('Undo must target an active earlier non-undo revision')
            inactive.add(target)
    pairs={a.gold_id:a for a in run.automatic};missing=set();rejected=set()
    gold={g.id:g for g in run.gold};ext={e.id:e for e in run.extractors}
    lookup={(c.gold_id,c.extractor_id):c for c in run.candidates}
    logical={e for p in run.papers if p.attempted for e in p.logical_extractor_ids}
    eligible={g for p in run.papers if p.attempted for g in p.gold_ids}
    for ev in events:
        if ev.revision in inactive or ev.action=='UNDO':continue
        g,e=ev.gold_id,ev.extractor_id
        if g not in eligible:raise ValueError('Gold is not an attempted scoreable significant record')
        if ev.action in ('CONFIRM_ASSOCIATION','REASSIGN','REJECT_PAIR'):
            if e not in logical or e not in ext:raise ValueError('Extractor is invalid, suppressed or absent')
            if gold[g].paper_id!=ext[e].paper_id:raise ValueError('Cross-paper review association prohibited')
            if (g,e) not in lookup:raise ValueError('Stored candidate comparison missing')
        if ev.action in ('CONFIRM_ASSOCIATION','REASSIGN'):
            owners=[gid for gid,a in pairs.items() if a.extractor_id==e and gid!=g]
            conflict=owners or g in missing or (g in pairs and pairs[g].extractor_id!=e)
            if ev.action=='CONFIRM_ASSOCIATION' and conflict:raise ValueError('Conflict: explicit reassignment and reason required')
            if ev.action=='REASSIGN' and (not ev.confirmed or not ev.note.strip()):raise ValueError('Reassignment requires explicit confirmation and reason')
            for old in owners:del pairs[old]
            pairs.pop(g,None);missing.discard(g);rejected.discard((g,e))
            c=lookup[g,e]
            pairs[g]=Association(g,e,c.id,'MATCHED_HUMAN',('MANUAL_REASSIGNED' if ev.action=='REASSIGN' else 'MANUAL_CONFIRMED_ASSOCIATION',))
        elif ev.action=='REJECT_PAIR':
            rejected.add((g,e))
            if g in pairs and pairs[g].extractor_id==e:del pairs[g]
        elif ev.action=='MARK_GOLD_MISSING':
            if g in pairs and not ev.confirmed:raise ValueError('Confirm removal of current association before marking missing')
            pairs.pop(g,None);missing.add(g)
        elif ev.action=='LEAVE_UNRESOLVED':
            pass # Auditable note; does not silently remove an accepted association.
    assert len({a.extractor_id for a in pairs.values()})==len(pairs)
    return ReviewedRun(run,events,tuple(pairs[g] for g in sorted(pairs)),tuple(sorted(missing)),tuple(sorted(rejected)))


def commit_event(value,action,reviewer,gold_id='',extractor_id='',note='',target_revision=None,confirmed=False,expected_revision=None):
    run=base_run(value);events=value.events if isinstance(value,ReviewedRun) else ()
    if expected_revision is not None and expected_revision!=len(events):raise ValueError('Review changed—reload/reconcile')
    ev=ReviewEvent(len(events)+1,action,reviewer,datetime.now(timezone.utc).isoformat(),gold_id,extractor_id,note,target_revision,confirmed)
    return apply_review_events(run,events+(ev,))


def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def export_review(value):
    run=base_run(value)
    payload={'schema_version':'lite-review-1','run_id':run.run_id,'gold_sha256':run.gold_sha256,'extractor_sha256':run.extractor_sha256,
             'policy_version':run.policy_version,'config_json':run.config_json,
             'events':[asdict(e) for e in value.events] if isinstance(value,ReviewedRun) else []}
    return canonical({'payload':payload,'sha256':sha256(canonical(payload)).hexdigest()})


def import_review(run,data):
    if len(data)>10*1024*1024:raise ValueError('Review file exceeds 10 MiB')
    try:
        wrapper=json.loads(data)
        if not isinstance(wrapper,dict) or not isinstance(wrapper.get('payload'),dict):raise ValueError('Invalid review-state schema')
        payload=wrapper['payload']
        if sha256(canonical(payload)).hexdigest()!=wrapper['sha256']:raise ValueError('Review checksum mismatch')
        expected={'schema_version':'lite-review-1','run_id':run.run_id,'gold_sha256':run.gold_sha256,'extractor_sha256':run.extractor_sha256,'policy_version':run.policy_version,'config_json':run.config_json}
        if any(payload.get(k)!=v for k,v in expected.items()):raise ValueError('Review fingerprint/configuration/policy mismatch')
        events=tuple(ReviewEvent(**e) for e in payload['events'])
        if len(events)>5000:raise ValueError('Review history exceeds 5000-event local limit')
        # Validate every historical transaction, including actions later undone.
        for i in range(1,len(events)+1):apply_review_events(run,events[:i])
        return apply_review_events(run,events)
    except (KeyError,TypeError,json.JSONDecodeError) as exc:raise ValueError('Invalid review-state schema') from exc


def save_review(value,path,expected_revision=None):
    """Single-user local store with process-safe lock, revision check and backup.
    Returns only after fsync + atomic replace. Caller updates UI after success.
    """
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);lock=path.with_suffix(path.suffix+'.lock')
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:raise ValueError('Review store busy; reload/retry (never overwrite a concurrent writer)') from exc
    temp=None
    try:
        os.close(fd)
        if path.exists():
            previous=import_review(base_run(value),path.read_bytes())
            if expected_revision is not None and len(previous.events)!=expected_revision:raise ValueError('Review changed—reload/reconcile')
        elif expected_revision not in (None,0):raise ValueError('Review store missing expected revision')
        data=export_review(value)
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.review-',delete=False) as f:
            temp=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
        if path.exists():
            backup=path.with_suffix(path.suffix+'.bak')
            with backup.open('wb') as f:f.write(path.read_bytes());f.flush();os.fsync(f.fileno())
        os.replace(temp,path);temp=None
    finally:
        if temp is not None:temp.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)
