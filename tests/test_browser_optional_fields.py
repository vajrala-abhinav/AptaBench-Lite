"""Real browser reproduction of the merged optional Pool/Kd Run path."""
from io import BytesIO
import json
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from openpyxl import load_workbook
from playwright.sync_api import sync_playwright,expect
from test_field_eval import synthetic

ROOT=Path(__file__).resolve().parents[1]


def test_optional_pool_kd_run_review_and_reload(tmp_path):
    chromium=shutil.which('chromium') or shutil.which('google-chrome') or os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE')
    if not chromium:pytest.skip('A Chromium executable is required')
    gb,eb=synthetic();book=load_workbook(BytesIO(gb))
    book['Sheet1']['H2']='A'*60+'X' # previously hangs the entire Streamlit process
    out=BytesIO();book.save(out)
    gold=tmp_path/'gold.xlsx';extractor=tmp_path/'extractor.xlsx'
    gold.write_bytes(out.getvalue());extractor.write_bytes(eb)
    log=(tmp_path/'server.log').open('w')
    proc=subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),
        '--server.address','127.0.0.1','--server.port','8504','--server.headless','true'],
        cwd=tmp_path,stdout=log,stderr=log,env={**os.environ,'STREAMLIT_BROWSER_GATHER_USAGE_STATS':'false'})
    try:
        for _ in range(100):
            try:
                if urlopen('http://127.0.0.1:8504/_stcore/health',timeout=1).status==200:break
            except OSError:time.sleep(.1)
        else:pytest.fail('Streamlit startup failed')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=chromium,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            page=browser.new_page(viewport={'width':1500,'height':1000});page.set_default_timeout(15000)
            def idle():expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning')
            def configure():
                inputs=page.get_by_test_id('stFileUploader').locator('input[type=file]')
                inputs.nth(0).set_input_files(str(gold));inputs.nth(1).set_input_files(str(extractor))
                page.get_by_text('Optional Pool and Kd evaluation',exact=True).click()
                page.get_by_text('Evaluate pool',exact=True).click()
                expect(page.get_by_text('Gold pool template',exact=True)).to_be_visible();idle()
                page.get_by_text('Evaluate Kd',exact=True).click()
                expect(page.get_by_text('Gold Kd value',exact=True)).to_be_visible();idle()
                start=time.perf_counter();page.get_by_role('button',name='Run evaluation',exact=True).click()
                expect(page.get_by_role('heading',name='Pool & Kd results',exact=True)).to_be_visible();idle()
                return time.perf_counter()-start
            page.goto('http://127.0.0.1:8504');run_s=configure()
            assert urlopen('http://127.0.0.1:8504/_stcore/health',timeout=2).status==200
            page.get_by_text('Show resolved records as well',exact=True).click();idle()
            control=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Gold field record',exact=True)).get_by_role('combobox')
            # Streamlit may finish the show-all rerun while the first popup is
            # opening. Retry that transient popup, but assert the final record.
            for attempt in range(3):
                control.click();control.fill('kd:G1');control.press('ArrowDown')
                try:
                    expect(page.get_by_role('option',name='KD · P · kd:G1',exact=True)).to_be_visible(timeout=2000)
                    control.press('Enter');idle()
                    expect(control).to_have_value('KD · P · kd:G1')
                    break
                except AssertionError:
                    if attempt==2:raise
            
            page.get_by_label('Field reviewer identity',exact=True).fill('FIELD-PI')
            page.get_by_label('Field reviewer identity',exact=True).press('Enter');idle()
            page.get_by_role('button',name='Mark missing',exact=True).click()
            expect(page.get_by_text('Pool/Kd review revision 1 saved locally.',exact=True)).to_be_visible();idle()
            with page.expect_download() as download:page.get_by_role('button',name='Download JSON audit',exact=True).click()
            audit_path=tmp_path/'audit.json';download.value.save_as(audit_path)
            audit=json.loads(audit_path.read_text())
            assert audit['optional_fields']['automatic_results']['kd']['T']==2
            assert audit['optional_fields']['effective_results']['kd']['T']==1
            assert len(audit['optional_fields']['review_events'])==1
            page.get_by_role('button',name='Prepare Excel report',exact=True).click();idle()
            with page.expect_download() as download:page.get_by_role('button',name='Download Excel report',exact=True).click()
            report=tmp_path/'report.xlsx';download.value.save_as(report)
            assert load_workbook(report).sheetnames==['Simple Summary','Debug Log','Logistics']
            page.get_by_role('button',name='Undo latest field review',exact=True).click()
            expect(page.get_by_text('Pool/Kd review revision 2 saved locally.',exact=True)).to_be_visible();idle()
            with page.expect_download() as download:page.get_by_role('button',name='Download Pool/Kd review backup',exact=True).click()
            backup=tmp_path/'field-review.json';download.value.save_as(backup)
            assert len(json.loads(backup.read_text())['payload']['events'])==2
            page.reload();configure()
            with page.expect_download() as download:page.get_by_role('button',name='Download JSON audit',exact=True).click()
            download.value.save_as(audit_path);audit=json.loads(audit_path.read_text())
            assert audit['optional_fields']['effective_results']['kd']['T']==2
            assert len(audit['optional_fields']['review_events'])==2
            assert not page.get_by_test_id('stException').count()
            page.get_by_role('heading',name='Pool & Kd results',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(tmp_path/'optional-fields.png'),full_page=True)
            (tmp_path/'evidence.json').write_text(json.dumps({'run_s':run_s,'pool_and_kd_enabled':True,
                'invalid_long_pool_tail':True,'server_responsive_after_run':True,'review_export_undo_reload':True},indent=2))
            browser.close()
    finally:
        proc.terminate();proc.wait(timeout=10);log.close()
