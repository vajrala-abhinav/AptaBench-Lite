from pathlib import Path
import json
import subprocess
import sys
from io import BytesIO
from openpyxl import load_workbook
from aptabench_lite.alignment import align
from aptabench_lite.presentation import alignment_html,COLORS

ROOT=Path(__file__).resolve().parents[1]


def test_frozen_reference_alignment_parity():
    corpus=json.loads((ROOT/'tests/fixtures/reference-alignments.json').read_text())
    for row in corpus['cases']:
        t=align(row['gold'],row['extractor'],row['mode'])
        assert (t.distance,t.optimal_interval_count)==(row['distance'],row['optimal_interval_count'])


def test_actual_cli_independent_entrypoint(tmp_path):
    out=tmp_path/'output'
    p=subprocess.run([sys.executable,'-I','-m','aptabench_lite.cli','--gold',str(ROOT/'examples/gold.xlsx'),'--extractor',str(ROOT/'examples/extractor.xlsx'),'--output-dir',str(out)],cwd=tmp_path,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    m=json.loads(p.stdout);assert (m['G'],m['E'],m['TP'],m['FP'],m['FN'])==(5,5,3,2,2)
    assert load_workbook(out/'evaluation.xlsx').sheetnames==['Simple Summary','Per-Paper Results','Matched Pairs','Debug Log','Logistics & Review','Record Inventory']
    audit=json.loads((out/'audit.json').read_text());assert audit['selected_metrics']==m
    # Restoring an empty review state uses the same fixed associations.
    replay=tmp_path/'replay'
    p=subprocess.run([sys.executable,'-I','-m','aptabench_lite.cli','--gold',str(ROOT/'examples/gold.xlsx'),'--extractor',str(ROOT/'examples/extractor.xlsx'),'--review',str(out/'review.json'),'--output-dir',str(replay)],cwd=tmp_path,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert json.loads((replay/'audit.json').read_text())['effective_associations']==audit['effective_associations']


def test_same_operation_colors_html():
    trace=align('ACGTCAGT','TTACGTCAGTGG')
    html=alignment_html(trace)
    for op in set(trace.operations):assert html.count(f'title="{op}"')==2*trace.operations.count(op)
    assert COLORS['FREE_EXTRACTOR_FLANK'] in html
