"""Explicit local verification on supplied workbooks only; no example fallback.
Writes private results to an ignored output directory chosen by the caller.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from io import BytesIO
from openpyxl import load_workbook
from aptabench_lite.engine import evaluate
from aptabench_lite.field_eval import FieldConfig,load_fields,field_results
from aptabench_lite.field_review import replay,append,to_bytes,from_bytes
from aptabench_lite.scoring import compute_metrics
from aptabench_lite.review import commit_event,export_review,import_review
from aptabench_lite.exports import export_audit,export_workbook


def verify(gold,extractor,output):
    paths=[Path(gold),Path(extractor)];before=[sha256(p.read_bytes()).hexdigest() for p in paths]
    gb,eb=[p.read_bytes() for p in paths];output=Path(output);output.mkdir(parents=True,exist_ok=True)
    start=perf_counter();run=evaluate(gb,eb);sequence_s=perf_counter()-start
    seq_counts=compute_metrics(run);original=run.automatic
    results={};all_data=None
    for name,pool,kd in [('sequence',False,False),('pool',True,False),('kd',False,True),('pool_kd',True,True)]:
        start=perf_counter();data=load_fields(run,gb,eb,FieldConfig(pool_enabled=pool,kd_enabled=kd)) if pool or kd else None
        fields=field_results(data) if data else {}
        results[name]={'optional_load_and_score_s':perf_counter()-start,
            'sequence_counts':{k:seq_counts[k] for k in ('G','E','M','T')},
            'fields':{kind:{k:m[k] for k in ('G','E','M','T','pending')} for kind,m in fields.items()}}
        assert run.automatic==original
        for m in fields.values():
            assert m['TP']+m['FP']==m['E'] and m['TP']+m['FN']==m['G']
            assert len(set(m['pairs'].values()))==m['M']
        if name=='pool_kd':all_data=data
    candidates={c.id:c for c in run.candidates}
    for pop in ('all','matched'):
        for tol in ('strict','adaptive'):
            for scope in ('core','whole'):
                m=compute_metrics(run,pop,tol,scope)
                assert 0<=m['T']<=m['M']<=min(m['G'],m['E'])
                if pop=='all':assert m['TP']+m['FP']==m['E'] and m['TP']+m['FN']==m['G']
    # Exercise review on throwaway local overlay; inputs and automatic results stay pristine.
    first=next((g for p in run.papers if p.attempted for g in p.gold_ids),None)
    if first:
        reviewed=commit_event(run,'MARK_GOLD_MISSING','VERIFICATION_ONLY',first,confirmed=True)
        assert import_review(run,export_review(reviewed))==reviewed
        undone=commit_event(reviewed,'UNDO','VERIFICATION_ONLY',target_revision=1)
        assert undone.associations==original
    for kind in ('pool','kd'):
        if all_data['gold'][kind]:
            gid=all_data['gold'][kind][0]['id']
            events,_=append(all_data,[],'missing','VERIFICATION_ONLY',kind,gid)
            assert from_bytes(all_data,to_bytes(all_data,events))==events
            events,back=append(all_data,events,'UNDO_LAST','VERIFICATION_ONLY')
            assert back==replay(all_data,[])
    start=perf_counter();xlsx=export_workbook(run,field_data=all_data);excel_s=perf_counter()-start
    book=load_workbook(BytesIO(xlsx),read_only=True)
    assert book.sheetnames==['Simple Summary','Debug Log','Logistics'];book.close()
    (output/'evaluation.xlsx').write_bytes(xlsx)
    start=perf_counter();audit=export_audit(run,field_data=all_data);audit_s=perf_counter()-start
    payload=json.loads(audit);assert payload['selected_metrics']==seq_counts
    (output/'audit.json').write_bytes(audit)
    assert before==[sha256(p.read_bytes()).hexdigest() for p in paths]
    summary={'input_sha256':dict(zip(('gold','extractor'),before)),'sequence_s':sequence_s,
        'engine_timings':json.loads(run.timings_json),'variants':results,'excel_s':excel_s,'audit_s':audit_s,
        'source_hashes_unchanged':True,'sequence_and_field_review_roundtrip':True,
        'gold_records':len(run.gold),'extractor_items':len(run.extractors),'candidate_pairs':len(run.candidates)}
    (output/'verification.json').write_text(json.dumps(summary,indent=2));return summary


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--gold',required=True,type=Path);ap.add_argument('--extractor',required=True,type=Path);ap.add_argument('--output-dir',required=True,type=Path)
    args=ap.parse_args();print(json.dumps(verify(args.gold,args.extractor,args.output_dir),indent=2))


if __name__=='__main__':main()
