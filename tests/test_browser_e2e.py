"""Actual HTTP/WebSocket Streamlit upload → review → download workflow.
Use system Chromium or PLAYWRIGHT_CHROMIUM_EXECUTABLE. No browser download required.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
import pytest
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]


def test_browser_upload_review_export(tmp_path):
    chromium=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:pytest.skip('Install a Playwright Chromium browser or set PLAYWRIGHT_CHROMIUM_EXECUTABLE')
    env=os.environ.copy();env['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
    process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),'--server.address','127.0.0.1','--server.port','8503','--server.headless','true'],cwd=tmp_path,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for attempt in range(100):
            try:
                if urlopen('http://127.0.0.1:8503/_stcore/health',timeout=1).status==200:break
            except OSError:time.sleep(.1)
        else:pytest.fail('Streamlit did not become healthy')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=chromium,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            page=browser.new_page(viewport={'width':1500,'height':1000});page.set_default_timeout(20000)
            page.goto('http://127.0.0.1:8503')
            def idle():expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning')
            uploads=page.get_by_test_id('stFileUploader').locator('input[type=file]')
            uploads.nth(0).set_input_files(str(ROOT/'examples/gold.xlsx'))
            uploads.nth(1).set_input_files(str(ROOT/'examples/extractor.xlsx'))
            page.get_by_role('button',name='Run evaluation',exact=True).click()
            expect(page.get_by_role('heading',name='Overview',exact=True)).to_be_visible();idle()
            def select(label,option):
                control=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True))
                control.get_by_role('combobox').click();control.get_by_role('combobox').fill(option);control.get_by_role('combobox').press('ArrowDown');expect(page.get_by_role('option',name=option,exact=True)).to_be_visible();control.get_by_role('combobox').press('Enter');idle()
            select('Paper','DEMO2')
            expect(page.get_by_role('heading',name='DEMO2 — Sequence detail',exact=True)).to_be_visible()
            page.get_by_text('Enable review / correction actions',exact=True).click();idle()
            page.get_by_label('Reviewer identity',exact=True).fill('BROWSER-PI');page.get_by_label('Reviewer identity',exact=True).press('Enter');idle()
            control=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Gold record',exact=True))
            control.get_by_role('combobox').click();control.get_by_role('combobox').fill('G4');control.get_by_role('combobox').press('ArrowDown');expect(page.get_by_role('option',name=re.compile('G4 ·'))).to_be_visible();control.get_by_role('combobox').press('Enter');idle()
            expect(control.get_by_role('combobox')).to_have_value(re.compile('G4 ·'))
            control=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Extractor record',exact=True))
            control.get_by_role('combobox').click();control.get_by_role('combobox').fill('Apt-4');control.get_by_role('combobox').press('ArrowDown');expect(page.get_by_role('option',name=re.compile('Apt-4 ·'))).to_be_visible();control.get_by_role('combobox').press('Enter');idle()
            expect(control.get_by_role('combobox')).to_have_value(re.compile('Apt-4 ·'))
            page.get_by_role('button',name='Confirm association',exact=True).click();idle()
            expect(page.get_by_text('After human review',exact=True)).to_be_visible()
            expect(page.get_by_text('Review saved locally;',exact=False)).to_be_visible()
            expect(page.get_by_text('G=5 significant golds · E=5 logical predictions · M=4 accepted pairs · T=3 passing pairs',exact=True)).to_be_visible();idle()
            rerun_start=time.perf_counter()
            page.get_by_text('Matched only',exact=True).click()
            expect(page.get_by_text('Matched-pair correctness',exact=True)).to_be_visible();idle()
            rerun_s=time.perf_counter()-rerun_start
            with page.expect_download() as download:
                page.get_by_role('button',name='Download JSON audit',exact=True).click()
            file=tmp_path/'audit.json';download.value.save_as(file)
            audit=json.loads(file.read_text());m=audit['selected_metrics']
            assert (m['M'],m['T'],m['matched_correctness'])==(4,3,.75)
            assert len(audit['run']['automatic'])==3 and len(audit['effective_associations'])==4
            with page.expect_download() as download:page.get_by_role('button',name='Download Excel report',exact=True).click()
            download.value.save_as(tmp_path/'evaluation.xlsx')
            from openpyxl import load_workbook
            assert load_workbook(tmp_path/'evaluation.xlsx').sheetnames==['Simple Summary','Debug Log','Logistics']
            page.get_by_text('Core edits:',exact=False).scroll_into_view_if_needed()
            page.screenshot(path=str(tmp_path/'review.png'),full_page=True)
            (tmp_path/'browser-evidence.json').write_text(json.dumps({'score_toggle_rerun_s':rerun_s,'metrics':m,'uploaded_files':2,'automatic_links_preserved':True},indent=2))
            # Undo preserves automatic matches; portable review backup survives reload.
            page.get_by_role('button',name='Undo selected action',exact=True).click()
            expect(page.get_by_text('G=5 significant golds · E=5 logical predictions · M=3 accepted pairs · T=3 passing pairs',exact=True)).to_be_visible()
            idle()
            with page.expect_download() as download:page.get_by_role('button',name='Download review state',exact=True).click()
            state=tmp_path/'review.json';download.value.save_as(state)
            assert len(json.loads(state.read_text())['payload']['events'])==2
            # A fresh browser session re-uploads and restores the durable local review.
            page.reload()
            uploads=page.get_by_test_id('stFileUploader').locator('input[type=file]')
            uploads.nth(0).set_input_files(str(ROOT/'examples/gold.xlsx'));uploads.nth(1).set_input_files(str(ROOT/'examples/extractor.xlsx'))
            page.get_by_role('button',name='Run evaluation',exact=True).click()
            expect(page.get_by_text('After human review',exact=True)).to_be_visible()
            restore=page.get_by_test_id('stFileUploader').filter(has=page.get_by_text('Restore review-state JSON',exact=True))
            restore.locator('input[type=file]').set_input_files(str(state))
            page.get_by_role('button',name='Restore review state',exact=True).click();idle()
            assert not page.get_by_test_id('stException').count()
            browser.close()
    finally:
        process.terminate();process.wait(timeout=10)
