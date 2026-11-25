"""Opt-in checks on explicitly supplied full workbooks; never use demo fallbacks."""
import os
from pathlib import Path
import pytest
from aptabench_lite.config import RunConfig
from aptabench_lite.field_eval import FieldConfig
from aptabench_lite.performance import Capture


def supplied_paths():
    keys=('APTABENCH_TEST_GOLD','APTABENCH_TEST_EXTRACTOR')
    if not all(os.environ.get(k) for k in keys):pytest.skip('Private full-input paths not supplied')
    return tuple(Path(os.environ[k]).resolve(strict=True) for k in keys)


def test_full_input_preview_and_no_workbook_or_sequence_recompute():
    from aptabench_lite import ui
    gold,extractor=supplied_paths();gb,eb=gold.read_bytes(),extractor.read_bytes();cfg=RunConfig().to_json()
    for fn in (ui._inspect,ui._preview,ui._evaluate,ui._load_fields):fn.clear()
    first=Capture()
    with first.activate():
        ui._inspect(gb);ui._inspect(eb)
        gs,es,attempted,_=ui._preview(gb,eb,cfg)
        run=ui._evaluate(gb,eb,cfg)
        data=ui._load_fields(gb,eb,run.run_id,FieldConfig(pool_enabled=True,kd_enabled=True).to_json(),run)
    counts=(len(gs),sum(g.significant for g in gs),sum(len(g.sequence.canonical or '') for g in gs if g.significant),len(attempted),len(es))
    assert counts==(248,116,6309,44,308),'Full-input preview does not match the specified workload'
    second=Capture()
    with second.activate():
        ui._inspect(gb);ui._inspect(eb);ui._preview(gb,eb,cfg)
        again=ui._evaluate(gb,eb,cfg)
        cached=ui._load_fields(gb,eb,again.run_id,FieldConfig(pool_enabled=True,kd_enabled=True).to_json(),again)
    assert second.stages.get('excel_parse',{}).get('calls',0)==0
    assert second.stages.get('sequence_evaluation',{}).get('calls',0)==0
    assert second.stages.get('sequence_alignment',{}).get('calls',0)==0
    assert second.stages.get('optional_field_loading',{}).get('calls',0)==0
    if run.automatic!=again.automatic:raise RuntimeError('Cached associations changed')
    if data!=cached:raise RuntimeError('Cached field inventory changed')


def test_full_input_browser_phase_timings_exports_and_review(tmp_path):
    import json
    import shutil
    import subprocess
    import sys
    import time
    from hashlib import sha256
    from urllib.request import urlopen
    from openpyxl import load_workbook
    from playwright.sync_api import sync_playwright,expect
    gold,extractor=supplied_paths();hashes=[sha256(p.read_bytes()).hexdigest() for p in (gold,extractor)]
    chromium=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:pytest.skip('Chromium is required for the opt-in real-input browser check')
    root=Path(__file__).resolve().parents[1]
    trace=tmp_path/'timings.jsonl';log=(tmp_path/'server.log').open('w')
    process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(root/'app.py'),'--server.address','127.0.0.1','--server.port','8506','--server.headless','true'],cwd=tmp_path,
        stdout=log,stderr=log,env={**os.environ,'STREAMLIT_BROWSER_GATHER_USAGE_STATS':'false','APTABENCH_PERFORMANCE_LOG':str(trace)})
    step='startup'
    def rows():
        return [json.loads(line) for line in trace.read_text().splitlines() if line.strip()] if trace.exists() else []
    def wait_trace(start,predicate):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            for row in rows()[start:]:
                if predicate(row):return row
            time.sleep(.025)
        raise RuntimeError('Timing observation timeout')
    def check(condition,category):
        if not condition:raise RuntimeError('Real-input verification: '+category)
    def no_input_work(row):
        for stage in ('excel_parse','sequence_evaluation','sequence_alignment','optional_field_loading'):
            check(row['stages'].get(stage,{}).get('calls',0)==0,'rerun unexpectedly recomputed '+stage)
    try:
        for _ in range(100):
            try:
                if urlopen('http://127.0.0.1:8506/_stcore/health',timeout=1).status==200:break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Startup health timeout')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=chromium,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            page=browser.new_page(viewport={'width':1500,'height':1000});page.set_default_timeout(30000)
            def idle():expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning',timeout=30000)
            def upload():
                inputs=page.get_by_test_id('stFileUploader').locator('input[type=file]')
                inputs.nth(0).set_input_files(str(gold));inputs.nth(1).set_input_files(str(extractor))
                expect(page.get_by_role('button',name='Run evaluation',exact=True)).to_be_visible();idle()
                expect(page.get_by_text('248 gold rows · 116 significant records · 6309 significant bases · 44 linked attempted papers · 308 raw extractor items',exact=True)).to_be_visible()
                page.get_by_text('Optional Pool and Kd evaluation',exact=True).click()
            def options(pool,kd):
                for label,wanted in [('Evaluate pool',pool),('Evaluate Kd',kd)]:
                    if page.get_by_label(label,exact=True).is_checked()!=wanted:
                        page.get_by_text(label,exact=True).click()
                        expect(page.get_by_label(label,exact=True)).to_be_checked(checked=wanted);idle()
            def run():
                start=len(rows());wall=time.perf_counter()
                page.get_by_role('button',name='Run evaluation',exact=True).click()
                record=wait_trace(start,lambda r:r['stages'].get('run_evaluation',{}).get('calls')==1)
                expect(page.get_by_role('heading',name='Overview',exact=True)).to_be_visible();idle()
                check(page.get_by_role('button',name='Download Excel report',exact=True).count()==0,'report built without explicit request')
                check(record['stages'].get('excel_export',{}).get('calls',0)==0,'export inside Run spinner')
                check(not page.get_by_test_id('stException').count(),'visible app error')
                return {'wall_s':time.perf_counter()-wall,**record}
            step='upload';page.goto('http://127.0.0.1:8506');upload();results={}
            for label,pool,kd in [('sequence',False,False),('pool',True,False),('kd',False,True),('pool_kd',True,True)]:
                step='run-'+label;options(pool,kd);results[label]=run()
                if label!='sequence':check(results[label]['stages'].get('sequence_evaluation',{}).get('calls',0)==0,'field toggle recomputed sequence')
            step='repeat-run';repeat=run();no_input_work(repeat)
            start=len(rows());step='score-toggle'
            page.get_by_text('Matched only',exact=True).click()
            expect(page.get_by_text('Matched-pair correctness',exact=True)).to_be_visible();idle()
            toggle=wait_trace(start,lambda r:r.get('has_run') and not r['stages'].get('run_evaluation'))
            no_input_work(toggle)
            step='explicit-export';start=len(rows())
            page.get_by_role('button',name='Prepare Excel report',exact=True).click()
            prepared=wait_trace(start,lambda r:r['stages'].get('excel_export',{}).get('calls')==1)
            expect(page.get_by_role('button',name='Download Excel report',exact=True)).to_be_visible();idle();no_input_work(prepared)
            with page.expect_download() as download:page.get_by_role('button',name='Download Excel report',exact=True).click()
            report=tmp_path/'evaluation.xlsx';download.value.save_as(report)
            book=load_workbook(report,read_only=True);check(book.sheetnames==['Simple Summary','Per-Paper Results','Matched Pairs','Debug Log','Logistics & Review','Record Inventory'],'six Excel sheets');book.close()
            step='review';page.get_by_label('Field reviewer identity',exact=True).fill('VERIFICATION_ONLY')
            page.get_by_label('Field reviewer identity',exact=True).press('Enter');idle()
            review_start=len(rows())
            page.get_by_role('button',name='Mark missing',exact=True).click()
            wait_trace(review_start,lambda r:r.get('completed') and r.get('field_review_revision')==1);idle()
            # Read only the small local review overlay, not the biological audit.
            deadline=time.monotonic()+10
            files=[]
            while time.monotonic()<deadline:
                files=list((tmp_path/'.local/reviews').glob('*fields*.json'))
                if files and len(json.loads(files[0].read_text())['payload']['events'])==1:break
                time.sleep(.025)
            check(bool(files),'field action not saved')
            idle();expect(page.get_by_role('button',name='Download Excel report',exact=True)).to_have_count(0)
            undo_start=len(rows())
            page.get_by_role('button',name='Undo latest field review',exact=True).click()
            wait_trace(undo_start,lambda r:r.get('completed') and r.get('field_review_revision')==2);idle()
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                if len(json.loads(files[0].read_text())['payload']['events'])==2:break
                time.sleep(.025)
            check(len(json.loads(files[0].read_text())['payload']['events'])==2,'field undo not persisted')
            with page.expect_download() as download:page.get_by_role('button',name='Download Pool/Kd review backup',exact=True).click()
            backup=tmp_path/'field-review.json';download.value.save_as(backup)
            check(len(json.loads(backup.read_text())['payload']['events'])==2,'field backup incomplete')
            step='reload-restore';page.reload();upload();options(True,True);restored=run()
            check(restored['stages'].get('field_review_restore',{}).get('calls')==1,'saved field history not restored')
            page.get_by_text('Restore Pool/Kd review backup',exact=True).click()
            uploader=page.get_by_test_id('stFileUploader').filter(has=page.get_by_text('Restore field review-state JSON',exact=True))
            uploader.locator('input[type=file]').set_input_files(str(backup))
            page.get_by_role('button',name='Restore field review',exact=True).click();idle()
            check(not page.get_by_test_id('stException').count(),'field review import error')
            evidence={'variants':results,'repeat_run':repeat,'scoring_toggle':toggle,'explicit_export':prepared,'review_restore':restored,
                'preview_verified':True,'field_review_undo_import_verified':True,'no_raw_data_recorded':True}
            (tmp_path/'browser-benchmark.json').write_text(json.dumps(evidence,indent=2))
            browser.close()
    except Exception as exc:
        # Do not include Playwright's full DOM or real sequence strings in logs.
        category=str(exc) if type(exc) is RuntimeError and str(exc).startswith('Real-input verification:') else type(exc).__name__
        raise RuntimeError('Real-input browser verification failed at '+step+' ('+category+')') from None
    finally:
        process.terminate();process.wait(timeout=10);log.close()
    check(hashes==[sha256(p.read_bytes()).hexdigest() for p in (gold,extractor)],'source workbooks changed')
