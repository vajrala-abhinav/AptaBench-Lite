"""Local, explicit profiling only; never invoked by normal evaluation."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import tracemalloc
from aptabench_lite.engine import evaluate
from aptabench_lite.config import RunConfig
from aptabench_lite.scoring import compute_metrics
from aptabench_lite.exports import export_audit,export_workbook
from aptabench_lite.review import commit_event,export_review,import_review


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--gold',type=Path,required=True);ap.add_argument('--extractor',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args()
    before=[sha256(p.read_bytes()).hexdigest() for p in (args.gold,args.extractor)]
    tracemalloc.start();start=perf_counter()
    run=evaluate(args.gold,args.extractor,RunConfig(gold_filename=args.gold.name,extractor_filename=args.extractor.name));engine=perf_counter()-start
    start=perf_counter();m=compute_metrics(run)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    excel=export_workbook(run,m);audit=export_audit(run,m)
    (args.output_dir/'evaluation.xlsx').write_bytes(excel);(args.output_dir/'audit.json').write_bytes(audit)
    export_s=perf_counter()-start
    # Independent aggregation reconciliation by original IDs.
    lookup={c.id:c for c in run.candidates}
    successful=[a for a in run.automatic if lookup[a.candidate_id].core.distance<=lookup[a.candidate_id].budget]
    assert m['T']==len(successful) and m['TP']+m['FP']==m['E'] and m['TP']+m['FN']==m['G']
    assert len({a.gold_id for a in run.automatic})==len(run.automatic)==len({a.extractor_id for a in run.automatic})
    candidate=next((c for c in run.candidates if c.gold_id not in {a.gold_id for a in run.automatic}),None)
    if candidate:
        reviewed=commit_event(run,'CONFIRM_ASSOCIATION','PROFILE',candidate.gold_id,candidate.extractor_id) if candidate.extractor_id not in {a.extractor_id for a in run.automatic} else None
        if reviewed:
            assert import_review(run,export_review(reviewed))==reviewed
            (args.output_dir/'review.json').write_bytes(export_review(reviewed))
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert before==[sha256(p.read_bytes()).hexdigest() for p in (args.gold,args.extractor)]
    result={'engine_s':engine,'export_s':export_s,'peak_python_memory_MiB':peak/1024**2,'timings':json.loads(run.timings_json),
            'gold_rows':len(run.gold),'extractor_raw':len(run.extractors),'linked_attempted_papers':sum(p.attempted for p in run.papers),
            'candidate_pairs':len(run.candidates),'metrics':m,'source_hashes_unchanged':True,'xlsx_bytes':len(excel),'json_bytes':len(audit)}
    (args.output_dir/'profile.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='metrics'},indent=2))


if __name__=='__main__':main()
