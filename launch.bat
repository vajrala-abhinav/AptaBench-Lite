@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto fail
  .venv\Scripts\python.exe -m pip install -r requirements.lock
  if errorlevel 1 goto fail
  .venv\Scripts\python.exe -m pip install --no-deps -e .
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m streamlit run app.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Setup or launch failed. Review the error above and README.md.
pause
exit /b 1
