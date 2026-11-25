"""Create a six-sheet report entirely from synthetic inputs; never reads research data."""
import argparse
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from openpyxl import load_workbook
from make_examples import make_examples
from aptabench_lite.engine import evaluate
from aptabench_lite.exports import export_workbook
from aptabench_lite.field_eval import FieldConfig, load_fields
from aptabench_lite.field_review import append
from aptabench_lite.review import commit_event


def create_report(path):
    path=Path(path)
    if path.exists():
        raise FileExistsError('Choose a new output path; the sample generator never overwrites files')
    with TemporaryDirectory() as directory:
        make_examples(directory)
        gold=load_workbook(Path(directory)/'gold.xlsx')
        ws=gold.active
        for col,name in enumerate(('gold_pool_sequence','gold_pool_type','gold_kd_value','gold_kd_unit'),8):
            ws.cell(1,col,name)
        for row in range(2,ws.max_row+1):
            for col,val in enumerate(('ACGT[N40]GTCA','ssDNA',100,'nM'),8):ws.cell(row,col,val)
        out=BytesIO();gold.save(out);gb=out.getvalue()
        ext=load_workbook(Path(directory)/'extractor.xlsx')
        pool=ext.create_sheet('pool_type');pool.append(['pk','value','where_in_text'])
        kd=ext.create_sheet('kd');kd.append(['pk','raw_values'])
        for key,names in [('demo-one',['Apt-1','Apt-2']),('demo-two',['Apt-3','Apt-4']),('demo-three',['Apt-6'])]:
            pool.append([key,'ACGT[N40]GTCA','ssDNA library'])
            kd.append([key,json.dumps([{'amount':100,'unit':'nM','notes':f'Aptamer: {n}'} for n in names])])
        out=BytesIO();ext.save(out);eb=out.getvalue()
    run=evaluate(gb,eb)
    wrong=next(e for e in run.extractors if e.name=='Apt-4')
    value=commit_event(run,'CONFIRM_ASSOCIATION','SYNTHETIC_PI','G4',wrong.id,note='Synthetic identity confirmation; nucleotides still fail')
    data=load_fields(run,gb,eb,FieldConfig(pool_enabled=True,kd_enabled=True))
    events,_=append(data,[],'missing','SYNTHETIC_PI','kd','kd:G1')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(export_workbook(value,field_data=data,field_events=events))
    check=load_workbook(path)
    assert len(check.sheetnames)==6
    print(f'Synthetic six-sheet report: {path}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='.local/report-redesign/synthetic-six-sheet.xlsx')
    create_report(parser.parse_args().output)
