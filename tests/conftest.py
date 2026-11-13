import json
from io import BytesIO
import pytest
from openpyxl import Workbook
from aptabench_lite.engine import evaluate


def xlsx(headers,rows,sheet):
    b=Workbook();w=b.active;w.title=sheet;w.append(headers)
    for row in rows:w.append(row)
    out=BytesIO();b.save(out);return out.getvalue()


def inputs(golds,extractors,paper='P'):
    # Gold tuples (id, sequence, name?, type?, paper?, filename?)
    gs=[]
    for g in golds:
        rid,seq,*rest=g;name=rest[0] if rest else '';typ=rest[1] if len(rest)>1 else 'significant_sequence'
        pid=rest[2] if len(rest)>2 else paper;key=rest[3] if len(rest)>3 else pid+'.pdf'
        gs.append([pid,key,rid,seq,name,typ,'present'])
    es=[]
    for key,items in extractors:es.append([key,json.dumps(items)])
    return xlsx(['paper_id','pdf_name','record_id','gold_sequence','aptamer_label_optional','aptamer_type','sequence_status'],gs,'Sheet1'),xlsx(['pk','value'],es,'aptamer_seq')


@pytest.fixture
def make_run():
    def make(golds,extractors,**kwargs):return evaluate(*inputs(golds,extractors),**kwargs)
    return make
