"""Private, opt-in profiling of explicitly supplied real XLSX inputs only.

No example fallback. Public output contains only aggregate counts, durations,
status categories and short fingerprint prefixes. Full workbook/report/review
artifacts stay in the caller's local output directory and must not be committed.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter

from openpyxl import load_workbook
from aptabench_lite.alignment import align
from aptabench_lite.config import RunConfig
from aptabench_lite.engine import evaluate
from aptabench_lite.exports import export_workbook
from aptabench_lite.field_eval import FieldConfig, load_fields, field_results, normalized_pool
from aptabench_lite.field_review import append, to_bytes, from_bytes, replay
from aptabench_lite.performance import Capture, measured
from aptabench_lite.readers import inspect_workbook
from aptabench_lite.review import commit_event, export_review, import_review
from aptabench_lite.scoring import compute_metrics


def check(condition, category):
    if not condition:
        raise RuntimeError('Verification failed: '+category)


def scientific_signature(run, data):
    # Hash internally rather than logging raw strings or full result objects.
    relevant={k:getattr(run,k) for k in ('gold','extractors','papers','duplicates','candidates','automatic','decisions','diagnostics')}
    relevant={k:[asdict(v) for v in rows] for k,rows in relevant.items()}
    relevant['metrics']={f'{p}/{t}/{s}':compute_metrics(run,p,t,s) for p in ('all','matched') for t in ('strict','adaptive') for s in ('whole','core')}
    relevant['fields']=field_results(data) if data else None
    return sha256(json.dumps(relevant,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()


def raw_pool_entries(gold):
    book=load_workbook(gold,read_only=True)
    try:
        iterator=book['Sheet1'].iter_rows(values_only=True)
        headers=list(next(iterator));index=headers.index('gold_pool_sequence')
        return [row[index] for row in iterator if row[index] is not None and str(row[index]).strip()]
    finally:book.close()


def legacy_child(gold):
    values=raw_pool_entries(gold)
    print(json.dumps({'ready':True,'entries':len(values)}),file=sys.stderr,flush=True)
    for index,raw in enumerate(values):
        text=str(raw).strip().upper()
        text=re.sub(r"^\s*5['′’]\s*[- ]*",'',text)
        text=re.sub(r"[- ]*3['′’]\s*$",'',text)
        text=re.sub(r'\s+','',text).replace('-','')
        text=re.sub(r'\[N(\d+)\]',r'N\1',text)
        print(json.dumps({'entry':index+1,'length':len(text)}),flush=True)
        re.fullmatch(r'(?:[ACGTU]+|N\d+)+',text)
    print(json.dumps({'completed':True}),flush=True)



def legacy_pipeline_child(gold,extractor):
    from aptabench_lite import field_eval
    gb,eb=Path(gold).read_bytes(),Path(extractor).read_bytes()
    run=evaluate(gb,eb)
    calls=0
    def old_normalized(raw):
        nonlocal calls
        value=field_eval._text(raw).upper()
        if not value:return None
        value=re.sub(r"^\s*5['′’]\s*[- ]*",'',value)
        value=re.sub(r"[- ]*3['′’]\s*$",'',value)
        value=re.sub(r'\s+','',value).replace('-','')
        value=re.sub(r'\[N(\d+)\]',r'N\1',value)
        calls+=1
        print(json.dumps({'normalizations_started':calls,'length':len(value)}),flush=True)
        return value if re.fullmatch(r'(?:[ACGTU]+|N\d+)+',value) else None
    field_eval.normalized_pool=old_normalized
    print(json.dumps({'ready':True,'sequence_finished':True,'next_stage':'optional_fields'}),file=sys.stderr,flush=True)
    field_eval.load_fields(run,gb,eb,FieldConfig(pool_enabled=True,kd_enabled=True))
    print(json.dumps({'optional_fields_completed':True}),flush=True)


def probe_pipeline(gold,extractor,seconds):
    proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--legacy-pipeline-child',str(gold),str(extractor)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        ready=json.loads(proc.stderr.readline())
        check(ready.get('sequence_finished'),'legacy full-pipeline startup')
        start=perf_counter()
        try:
            stdout,stderr=proc.communicate(timeout=seconds)
            status='completed' if proc.returncode==0 else 'error'
        except subprocess.TimeoutExpired:
            proc.kill();stdout,stderr=proc.communicate();status='timed_out'
        observations=[json.loads(line) for line in stdout.splitlines() if line.strip()]
        last=next((r for r in reversed(observations) if 'normalizations_started' in r),{})
        return {'status':status,'timeout_s':seconds,'observed_s':perf_counter()-start,
            'sequence_finished_before_timing':True,'excel_not_started':True,
            'normalizations_started':last.get('normalizations_started'),'last_length':last.get('length')}
    finally:
        if proc.poll() is None:proc.kill();proc.wait()

def probe_legacy(gold,seconds):
    proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--legacy-child',str(gold)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        ready=json.loads(proc.stderr.readline()) # parsing/import completes before the timed window
        check(ready.get('ready'),'legacy probe startup')
        start=perf_counter()
        try:
            stdout,stderr=proc.communicate(timeout=seconds)
            status='completed' if proc.returncode==0 else 'error'
        except subprocess.TimeoutExpired:
            proc.kill();stdout,stderr=proc.communicate();status='timed_out'
        elapsed=perf_counter()-start
        rows=[json.loads(line) for line in stdout.splitlines() if line.strip()]
        last=next((r for r in reversed(rows) if 'entry' in r),{})
        return {'status':status,'timeout_s':seconds,'observed_s':elapsed,'populated_entries':ready['entries'],
                'last_entry_ordinal':last.get('entry'),'last_entry_length':last.get('length')}
    finally:
        if proc.poll() is None:proc.kill();proc.wait()


def verify_schema(gb,eb):
    gold,extractor=inspect_workbook(gb),inspect_workbook(eb)
    required={'Sheet1':('paper_id','pdf_name','record_id','aptamer_type','sequence_status','gold_sequence','gold_pool_sequence','gold_pool_type','gold_kd_value','gold_kd_unit')}
    for sheet,headers in required.items():check(sheet in gold and set(headers)<=set(gold[sheet]['headers']),'gold schema')
    for sheet,headers in {'aptamer_seq':('pk','value'),'pool_type':('pk','value','where_in_text'),'kd':('pk','raw_values')}.items():
        check(sheet in extractor and set(headers)<=set(extractor[sheet]['headers']),'extractor schema')


def benchmark(gold,extractor,output,repeats=2,legacy_timeout=.25):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    gb,eb=Path(gold).read_bytes(),Path(extractor).read_bytes()
    hashes=[sha256(v).hexdigest() for v in (gb,eb)]
    verify_schema(gb,eb)
    legacy=probe_legacy(gold,legacy_timeout)
    pipeline_probe=probe_pipeline(gold,extractor,legacy_timeout)
    pool_values=raw_pool_entries(gold)
    start=perf_counter();accepted=sum(normalized_pool(v) is not None for v in pool_values);safe_scan=perf_counter()-start
    legacy['safe_scan_s']=safe_scan;legacy['safe_accepted']=accepted;legacy['safe_review']=len(pool_values)-accepted
    legacy['speedup_lower_bound']=legacy_timeout/safe_scan if legacy['status']=='timed_out' and safe_scan else None
    rows=[];signatures={};preview=None
    for repetition in range(1,repeats+1):
        for name,pool,kd in [('sequence',False,False),('pool',True,False),('kd',False,True),('pool_kd',True,True)]:
            align.cache_clear();capture=Capture();start=perf_counter()
            with capture.activate():
                run=evaluate(gb,eb,RunConfig())
                seq_parse_s=capture.stages.get('excel_parse',{}).get('seconds',0)
                if preview is None:
                    preview={'gold_rows':len(run.gold),'significant':sum(g.significant for g in run.gold),
                        'significant_bases':sum(len(g.sequence.canonical or '') for g in run.gold if g.significant),
                        'attempted_papers':sum(p.attempted for p in run.papers),'raw_sequence_items':len(run.extractors)}
                data=load_fields(run,gb,eb,FieldConfig(pool_enabled=pool,kd_enabled=kd)) if pool or kd else None
                # Verification-only local review history, immediately undone.
                # Source data and the automatic result are never changed.
                g=next((g for p in run.papers if p.attempted for g in p.gold_ids),None)
                reviewed=commit_event(run,'MARK_GOLD_MISSING','VERIFICATION_ONLY',g,confirmed=True) if g else None
                reviewed=commit_event(reviewed,'UNDO','VERIFICATION_ONLY',target_revision=1) if reviewed else None
                sequence_path=output/'sequence-review.json'
                sequence_path.write_bytes(export_review(reviewed or run))
                events=[]
                if data:
                    for kind in ('pool','kd'):
                        if data['gold'][kind]:
                            events,_=append(data,events,'missing','VERIFICATION_ONLY',kind,data['gold'][kind][0]['id'])
                            events,_=append(data,events,'UNDO_LAST','VERIFICATION_ONLY')
                    field_path=output/'field-review.json';field_path.write_bytes(to_bytes(data,events))
                with measured('review_state_restore'):
                    restored=import_review(run,sequence_path.read_bytes())
                    check(restored.associations==run.automatic,'sequence review undo/restore')
                    if data:
                        restored_events=from_bytes(data,field_path.read_bytes())
                        check(restored_events==events,'field review restore')
                with measured('population_scoring'):
                    metrics=compute_metrics(restored)
                    fields=replay(data,events) if data else None
                    if data:check(fields==field_results(data),'field review undo')
                scientific=scientific_signature(run,data)
                if name in signatures:check(signatures[name]==scientific,'repeatability')
                signatures[name]=scientific
                check(metrics['TP']+metrics['FP']==metrics['E'] and metrics['TP']+metrics['FN']==metrics['G'],'sequence count reconciliation')
                before_dp=align.cache_info().misses
                report=export_workbook(restored,metrics,field_data=data,field_events=events)
                check(align.cache_info().misses==before_dp,'no export realignment')
            book=load_workbook(BytesIO(report),read_only=True)
            check(book.sheetnames==['Simple Summary','Per-Paper Results','Matched Pairs','Debug Log','Logistics & Review','Record Inventory'],'six Excel sheets');book.close()
            if name=='pool_kd':(output/'evaluation.xlsx').write_bytes(report)
            durations=lambda stage:capture.stages.get(stage,{}).get('seconds',0)
            rows.append({'repetition':repetition,'mode':name,'total_s':perf_counter()-start,
                'excel_parse_s':durations('excel_parse'),'sequence_compute_s':max(0,durations('sequence_evaluation')-seq_parse_s),
                'pool_normalization_s':durations('pool_normalization'),'kd_normalization_s':durations('kd_normalization'),
                'review_restore_s':durations('review_state_restore'),'scoring_s':durations('population_scoring'),
                'excel_export_s':durations('excel_export'),'sequence_evaluation_s':durations('sequence_evaluation'),
                'counts':{k:metrics[k] for k in ('G','E','M','T')},
                'fields':{kind:{k:r[k] for k in ('G','E','M','T','pending')} for kind,r in (fields or {}).items()}})
    # Exact repeatability and scientific comparison stay private; only prefixes
    # of source hashes are included in the shareable aggregate benchmark.
    (output/'private-signatures.json').write_text(json.dumps(signatures))
    check(hashes==[sha256(Path(p).read_bytes()).hexdigest() for p in (gold,extractor)],'unchanged source workbooks')
    summary={'python':sys.version.split()[0],'hash_prefixes':dict(zip(('gold','extractor'),[h[:12] for h in hashes])),
        'preview':preview,'schema_verified':True,'legacy_probe':legacy,'legacy_pipeline_probe':pipeline_probe,'runs':rows,'repeatability_verified':True,'source_hashes_unchanged':True,
        'timing_note':'Inclusive nested stages are not additive; sequence_compute_s excludes its measured Excel parsing. No raw data logged.'}
    (output/'benchmark.json').write_text(json.dumps(summary,indent=2));return summary


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--legacy-child':legacy_child(Path(sys.argv[2]));return
    if len(sys.argv)>1 and sys.argv[1]=='--legacy-pipeline-child':legacy_pipeline_child(Path(sys.argv[2]),Path(sys.argv[3]));return
    ap=argparse.ArgumentParser();ap.add_argument('--gold',type=Path,required=True);ap.add_argument('--extractor',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True);ap.add_argument('--repeats',type=int,default=2);ap.add_argument('--legacy-timeout',type=float,default=.25)
    args=ap.parse_args()
    if not 1<=args.repeats<=10 or not .05<=args.legacy_timeout<=5:ap.error('Use 1–10 repeats and 0.05–5 seconds for the bounded probe')
    print(json.dumps(benchmark(args.gold,args.extractor,args.output_dir,args.repeats,args.legacy_timeout),indent=2))


if __name__=='__main__':main()
