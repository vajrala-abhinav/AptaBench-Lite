import argparse
import json
from pathlib import Path
from .config import RunConfig
from .engine import evaluate
from .review import import_review,export_review
from .scoring import compute_metrics
from .exports import export_audit,export_workbook


def main(argv=None):
    ap=argparse.ArgumentParser(description='AptaBench Lite standalone significant-gold sequence evaluation')
    ap.add_argument('--gold',type=Path,required=True);ap.add_argument('--extractor',type=Path,required=True)
    ap.add_argument('--config',type=Path);ap.add_argument('--review',type=Path);ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--population',choices=['all','matched'],default='all');ap.add_argument('--tolerance',choices=['strict','adaptive'],default='adaptive');ap.add_argument('--scope',choices=['whole','core'],default='core')
    args=ap.parse_args(argv)
    try:
        cfg=RunConfig(**json.loads(args.config.read_text())) if args.config else RunConfig(gold_filename=args.gold.name,extractor_filename=args.extractor.name)
        run=evaluate(args.gold,args.extractor,cfg);value=import_review(run,args.review.read_bytes()) if args.review else run
        metrics=compute_metrics(value,args.population,args.tolerance,args.scope)
        if not metrics['attempted_papers']:raise ValueError('No linked attempted papers; correct linkage before reporting benchmark metrics')
        args.output_dir.mkdir(parents=True,exist_ok=True)
        for name,data in [('evaluation.xlsx',export_workbook(value,metrics)),('audit.json',export_audit(value,metrics)),('review.json',export_review(value))]:
            path=args.output_dir/name
            with path.open('xb') as f:f.write(data)
        print(json.dumps(metrics,indent=2));return 0
    except (ValueError,OSError) as exc:ap.exit(2,f'AptaBench Lite: {exc}\n')


if __name__=='__main__':raise SystemExit(main())
