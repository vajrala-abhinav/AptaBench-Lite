"""Developer-only read-only comparison against a selected historical source.
Extracts ONLY the pure align function via AST; never imports the old package.
Creates a tiny synthetic regression corpus with source hash, not research data.
"""
import argparse
import ast
from collections import Counter
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('reference',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    data=args.reference.read_bytes();tree=ast.parse(data)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='align')
    module=ast.Module(body=[function],type_ignores=[]);ns={'Counter':Counter,'lru_cache':lru_cache}
    exec(compile(module,'historical-pure-align','exec'),ns)
    pairs=[('ACGTCAGT','ACGTCAGT'),('ACGTCAGT','TTACGTCAGTGG'),('ACGTCAGT','ACGCAGT'),('ACGTCAGT','ACGACAGT'),('ACTG','ACATG'),('ACGTCAGT','CAGT'),('ACG','ACGACG')]
    rows=[]
    for g,e in pairs:
        for mode in ('core','whole'):
            result=ns['align'](g,e,mode=='core')
            rows.append({'gold':g,'extractor':e,'mode':mode,'distance':result['edit_distance'],'optimal_interval_count':result['optimal_interval_count']})
    payload={'provenance':'Historical deadline_eval.py pure align function; synthetic strings only','reference_sha256':sha256(data).hexdigest(),'cases':rows,
             'intentional_changes':['Lite minimum one-edit budget','Significant-only population','Contextual fixed associations','Conservative tie abstention','Completion uses edit distance / gold length']}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(payload,indent=2))


if __name__=='__main__':main()
