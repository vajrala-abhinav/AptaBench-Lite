"""Opt-in integration checks using caller-supplied XLSX files only.

Set APTABENCH_TEST_GOLD and APTABENCH_TEST_EXTRACTOR to private local paths.
No sample/synthetic workbook is loaded, created, or substituted by these checks.
"""
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from openpyxl import load_workbook
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]


def supplied_inputs():
    names=('APTABENCH_TEST_GOLD','APTABENCH_TEST_EXTRACTOR')
    if not all(os.environ.get(n) for n in names):pytest.skip('Supply the two private workbook paths explicitly')
    paths=tuple(Path(os.environ[n]).resolve(strict=True) for n in names)
    assert all(p.suffix.lower()=='.xlsx' for p in paths)
    return paths


def test_supplied_engine_and_all_field_variants(tmp_path):
    gold,extractor=supplied_inputs()
    # Reuse the explicit verifier; it has no sample-input defaults.
    result=subprocess.run([sys.executable,str(ROOT/'scripts/verify_supplied_workbooks.py'),
        '--gold',str(gold),'--extractor',str(extractor),'--output-dir',str(tmp_path/'results')],
        cwd=ROOT,timeout=120,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['source_hashes_unchanged'] and report['sequence_and_field_review_roundtrip']
    assert len({json.dumps(v['sequence_counts'],sort_keys=True) for v in report['variants'].values()})==1


def test_supplied_browser_variants_lazy_exports_review_and_reload(tmp_path):
    gold,extractor=supplied_inputs();before=[sha256(p.read_bytes()).hexdigest() for p in (gold,extractor)]
    chromium=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:pytest.skip('A Chromium executable is required')
    log=(tmp_path/'server.log').open('w')
    proc=subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),
        '--server.address','127.0.0.1','--server.port','8505','--server.headless','true'],
        cwd=tmp_path,stdout=log,stderr=log,env={**os.environ,'STREAMLIT_BROWSER_GATHER_USAGE_STATS':'false'})
    try:
        for _ in range(100):
            try:
                if urlopen('http://127.0.0.1:8505/_stcore/health',timeout=1).status==200:break
            except OSError:time.sleep(.1)
        else:pytest.fail('Streamlit startup failed')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=chromium,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            page=browser.new_page(viewport={'width':1500,'height':1000});page.set_default_timeout(30000)
            def idle():expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning',timeout=30000)
            def audit(name):
                idle()
                with page.expect_download() as d:page.get_by_role('button',name='Download JSON audit',exact=True).click()
                path=tmp_path/name;d.value.save_as(path);return json.loads(path.read_text())
            def prepare(name):
                assert page.get_by_role('button',name='Download Excel report',exact=True).count()==0
                start=time.perf_counter();page.get_by_role('button',name='Prepare Excel report',exact=True).click()
                expect(page.get_by_role('button',name='Download Excel report',exact=True)).to_be_visible();idle()
                with page.expect_download() as d:page.get_by_role('button',name='Download Excel report',exact=True).click()
                path=tmp_path/name;d.value.save_as(path)
                book=load_workbook(path,read_only=True)
                assert book.sheetnames==['Simple Summary','Per-Paper Results','Matched Pairs','Debug Log','Logistics & Review','Record Inventory'];book.close()
                return time.perf_counter()-start
            def upload():
                uploads=page.get_by_test_id('stFileUploader').locator('input[type=file]')
                uploads.nth(0).set_input_files(str(gold));uploads.nth(1).set_input_files(str(extractor))
                expect(page.get_by_role('button',name='Run evaluation',exact=True)).to_be_visible()
            page.goto('http://127.0.0.1:8505');upload()
            page.get_by_text('Optional Pool and Kd evaluation',exact=True).click()
            variants={};original_links=None
            for label,pool,kd in [('sequence',False,False),('pool',True,False),('kd',False,True),('pool_kd',True,True)]:
                for text,wanted in [('Evaluate pool',pool),('Evaluate Kd',kd)]:
                    if page.get_by_label(text,exact=True).is_checked()!=wanted:
                        page.get_by_text(text,exact=True).click()
                        expect(page.get_by_label(text,exact=True)).to_be_checked(checked=wanted);idle()
                start=time.perf_counter();page.get_by_role('button',name='Run evaluation',exact=True).click()
                expect(page.get_by_role('heading',name='Overview',exact=True)).to_be_visible(timeout=30000);idle()
                if pool or kd:expect(page.get_by_role('heading',name='Pool & Kd results',exact=True)).to_be_visible()
                run_s=time.perf_counter()-start
                assert page.get_by_role('button',name='Download Excel report',exact=True).count()==0
                current=audit(label+'-audit.json');links=current['effective_associations']
                if original_links is None:original_links=links
                assert links==original_links
                if pool or kd:
                    fields=current['optional_fields']['effective_results']
                    if pool:assert fields['pool']['G']>0
                    if kd:assert fields['kd']['G']>0
                assert not page.get_by_test_id('stException').count()
                assert urlopen('http://127.0.0.1:8505/_stcore/health',timeout=2).status==200
                variants[label]={'run_s':run_s,'sequence_counts':{k:current['selected_metrics'][k] for k in ('G','E','M','T')}}
            report_s=prepare('all-fields.xlsx')
            # Scoring changes invalidate the prepared report but do not rematch.
            page.get_by_text('Matched only',exact=True).click()
            expect(page.get_by_text('Matched-pair correctness',exact=True)).to_be_visible();idle()
            expect(page.get_by_role('button',name='Download Excel report',exact=True)).to_have_count(0)
            assert audit('matched-audit.json')['effective_associations']==original_links
            prepare('matched-fields.xlsx')
            # A real field action must invalidate both metrics and prepared bytes.
            page.get_by_label('Field reviewer identity',exact=True).fill('VERIFICATION_ONLY')
            page.get_by_label('Field reviewer identity',exact=True).press('Enter');idle()
            page.get_by_role('button',name='Mark missing',exact=True).click()
            expect(page.get_by_text('Pool/Kd review revision 1 saved locally.',exact=True)).to_be_visible();idle()
            expect(page.get_by_role('button',name='Download Excel report',exact=True)).to_have_count(0)
            changed=audit('reviewed-audit.json');assert len(changed['optional_fields']['review_events'])==1
            assert changed['effective_associations']==original_links
            page.get_by_role('button',name='Undo latest field review',exact=True).click()
            expect(page.get_by_text('Pool/Kd review revision 2 saved locally.',exact=True)).to_be_visible();idle()
            undone=audit('undone-audit.json')
            assert undone['optional_fields']['effective_results']==undone['optional_fields']['automatic_results']
            with page.expect_download() as d:page.get_by_role('button',name='Download Pool/Kd review backup',exact=True).click()
            state=tmp_path/'field-review.json';d.value.save_as(state)
            assert len(json.loads(state.read_text())['payload']['events'])==2
            page.reload();upload()
            page.get_by_text('Optional Pool and Kd evaluation',exact=True).click()
            for text in ('Evaluate pool','Evaluate Kd'):
                page.get_by_text(text,exact=True).click();expect(page.get_by_label(text,exact=True)).to_be_checked();idle()
            page.get_by_role('button',name='Run evaluation',exact=True).click()
            expect(page.get_by_role('heading',name='Pool & Kd results',exact=True)).to_be_visible();idle()
            restored=audit('restored-audit.json')
            assert len(restored['optional_fields']['review_events'])==2
            assert restored['effective_associations']==original_links
            assert not page.get_by_test_id('stException').count()
            page.get_by_role('heading',name='Overview',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(tmp_path/'dashboard.png'),full_page=True)
            (tmp_path/'browser-evidence.json').write_text(json.dumps({'variants':variants,'report_prepare_download_s':report_s,
                'explicit_report_preparation':True,'invalidation_on_scoring_and_review':True,'review_undo_reload':True},indent=2))
            browser.close()
    finally:
        proc.terminate();proc.wait(timeout=10);log.close()
    assert before==[sha256(p.read_bytes()).hexdigest() for p in (gold,extractor)]
