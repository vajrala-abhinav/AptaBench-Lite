"""Append-only portable field review actions for the local, single-user dashboard."""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from .performance import timed
from .field_eval import field_results


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=str).encode()


def fingerprint(data):
    return sha256(canonical({
        "run_id": data["run_id"],
        "config": data["config"],
        "gold": data["gold"],
        "predictions": data["predictions"],
    })).hexdigest()


def active_actions(events):
    return [ev for ev in events if ev["action"] != "UNDO_LAST" and
            not any(undo["action"] == "UNDO_LAST" and undo["target"] == ev["revision"] for undo in events)]


def replay(data, events):
    """Reject edited actions by validating every committed history prefix."""
    checked = []
    for i, event in enumerate(events, 1):
        if event["revision"] != i or not event["reviewer"].strip() or not isinstance(event["time"], str):
            raise ValueError("Invalid field-review revision/reviewer")
        if event["action"] == "UNDO_LAST":
            active = active_actions(checked)
            if not active or event.get("target") != active[-1]["revision"]:
                raise ValueError("Undo must target most recent active field action")
        elif event["action"] not in ("confirm", "missing", "reject", "unresolved"):
            raise ValueError("Unsupported field-review action")
        checked.append(event)
        field_results(data, active_actions(checked))
    return field_results(data, active_actions(checked))


def append(data, events, action, reviewer, field="", gold_id="", extractor_id=""):
    if not reviewer.strip():raise ValueError("Reviewer name required")
    if action == "UNDO_LAST":
        active = active_actions(events)
        if not active:raise ValueError("Nothing to undo")
        event = {"revision": len(events)+1, "action": action, "reviewer": reviewer,
                 "time": datetime.now(timezone.utc).isoformat(), "target": active[-1]["revision"]}
    else:
        event = {"revision": len(events)+1, "action": action, "reviewer": reviewer,
                 "time": datetime.now(timezone.utc).isoformat(), "field": field,
                 "gold_id": gold_id, "extractor_id": extractor_id}
    outcome = replay(data, list(events)+[event])
    return list(events)+[event], outcome


def to_bytes(data, events):
    payload = {"schema": "lite-fields-review-1", "fingerprint": fingerprint(data), "events": list(events)}
    return canonical({"payload": payload, "sha256": sha256(canonical(payload)).hexdigest()})


@timed("field_review_restore")
def from_bytes(data, raw):
    if len(raw)>2*1024*1024:raise ValueError("Field review exceeds 2 MiB")
    try:
        wrapper=json.loads(raw)
        payload=wrapper["payload"]
        if sha256(canonical(payload)).hexdigest()!=wrapper["sha256"]:
            raise ValueError("Field-review file checksum mismatch")
        if payload["schema"]!="lite-fields-review-1" or payload["fingerprint"]!=fingerprint(data):
            raise ValueError("Field review belongs to different inputs or mappings")
        events=payload["events"]
        if not isinstance(events,list) or len(events)>2000:
            raise ValueError("Invalid field review history")
        replay(data, events)
        return events
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        raise ValueError("Invalid field-review JSON") from e


def save(data, events, path, expected_revision):
    """Atomic lock-guarded save; do not overwrite another revision."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    lock=path.with_suffix(path.suffix+".lock")
    try:fd=os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("Field-review store busy") from exc
    tmp=None
    try:
        os.close(fd)
        old=from_bytes(data,path.read_bytes()) if path.exists() else []
        if len(old)!=expected_revision:
            raise ValueError("Field-review revision changed; reload before saving")
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=".field-review-",delete=False) as f:
            tmp=Path(f.name);f.write(to_bytes(data,events));f.flush();os.fsync(f.fileno())
        if path.exists():
            backup=path.with_suffix(path.suffix+".bak")
            backup.write_bytes(path.read_bytes())
        os.replace(tmp,path);tmp=None
    finally:
        if tmp:tmp.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)
