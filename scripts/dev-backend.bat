@echo off
setlocal
cd /d "%~dp0..\backend"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
echo Starting API at http://127.0.0.1:8000 (cwd: %CD%)

where python >nul 2>&1
if %errorlevel%==0 (
  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  goto end
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  goto end
)
echo ERROR: Neither python nor py found on PATH.
exit /b 1

:end
