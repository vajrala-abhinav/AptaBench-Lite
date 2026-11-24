"""Small Pool/Kd contract, regression and live-review tests using synthetic data."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
import json

import pytest
from openpyxl import load_workbook

from aptabench_lite.engine import evaluate
from aptabench_lite.config import RunConfig
from aptabench_lite.field_eval import FieldConfig, kd_nm, normalized_pool, load_fields, field_results
from aptabench_lite.field_review import append, replay, from_bytes, to_bytes
from aptabench_lite.exports import export_workbook
from aptabench_lite.scoring import compute_metrics
from conftest import xlsx


def synthetic():
    gold=xlsx(["paper_id","pdf_name","record_id","gold_sequence","aptamer_label_optional",
               "aptamer_type","sequence_status","gold_pool_sequence","gold_pool_type",
               "gold_kd_value","gold_kd_unit"],
        [["P","P.pdf","G1","ACGTCAGT","A","significant_sequence","present",
          "ACGT[N40]GTCA","ssDNA","100","nM"],
         ["P","P.pdf","G2","TGCACGTA","B","significant_sequence","present",
          "ACGT[N40]GTCA","ssDNA","30","nM"]],"Sheet1")
    from openpyxl import Workbook
    wb=Workbook();ws=wb.active;ws.title="aptamer_seq"
    ws.append(["pk","value"]);ws.append(["P",json.dumps([{"sequence":"ACGTCAGT","name":"A"},{"sequence":"TGCACGTA","name":"B"}])])
    ws=wb.create_sheet("pool_type")
    ws.append(["pk","value","where_in_text"])
    ws.append(["P","ACGT[N40]GTCA","ssDNA library"])
    ws=wb.create_sheet("kd")
    ws.append(["pk","raw_values"])
    ws.append(["P",json.dumps([{"amount":"0.10","unit":"uM","notes":"Aptamer: A"},
                                {"amount":"31","unit":"nM","notes":"Aptamer: B"}])])
    out=BytesIO();wb.save(out)
    return gold,out.getvalue()


def test_numeric_units_and_uncertainty():
    assert kd_nm("0.1","uM")==Decimal("100")
    assert kd_nm("100","nM")==Decimal("100")
    assert kd_nm("100 ± 9 by SPR","nM")==Decimal("100")
    assert kd_nm("100-120","nM") is None
    assert kd_nm("< 100","nM") is None
    assert kd_nm("100","unknown") is None
    assert normalized_pool("5′-ACGT-[N40]-GTCA-3′")=="ACGTN40GTCA"


def test_fields_and_manual_review_do_not_modify_sequences():
    gb,eb=synthetic()
    run=evaluate(gb,eb)
    original=compute_metrics(run)
    extra=load_fields(run,gb,eb,FieldConfig(pool_enabled=True,kd_enabled=True))
    result=field_results(extra)
    assert (result["pool"]["G"],result["pool"]["E"],result["pool"]["T"])==(1,1,1)
    assert (result["kd"]["G"],result["kd"]["E"],result["kd"]["T"])==(2,2,2)
    assert result["kd"]["rows"][0]["comparison"]["exact"]
    assert not result["kd"]["rows"][1]["comparison"]["exact"]
    events,after=append(extra,[],"missing","PI","kd","kd:G1")
    assert after["kd"]["T"]==1
    assert after["kd"]["pending"]==0
    assert from_bytes(extra,to_bytes(extra,events))==events
    events,back=append(extra,events,"UNDO_LAST","PI")
    assert back["kd"]["T"]==2
    assert compute_metrics(run)==original
    wb=load_workbook(BytesIO(export_workbook(run,field_data=extra,field_events=events)))
    assert wb.sheetnames==["Simple Summary","Debug Log","Logistics"]
    assert any(cell.value=="POOL AND KD | EFFECTIVE FIELD SCORES" for row in wb["Simple Summary"] for cell in row)


def test_kd_multiple_unnamed_predictions_remain_ambiguous():
    gb,eb=synthetic()
    run=evaluate(gb,eb)
    data=load_fields(run,gb,eb,FieldConfig(kd_enabled=True))
    for e in data["predictions"]["kd"]:e["name"]=""
    result=field_results(data)
    assert result["kd"]["M"]==0 and result["kd"]["pending"]==2
    e=data["predictions"]["kd"][0]["id"]
    events,new=append(data,[],"confirm","PI","kd","kd:G1",e)
    assert new["kd"]["M"]==1 and new["kd"]["pending"]==1
    with pytest.raises(ValueError,match="already assigned"):
        append(data,events,"confirm","PI","kd","kd:G2",e)
