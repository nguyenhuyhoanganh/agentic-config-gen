@echo off
REM Tao venv va cai dependencies - chay tu thu muc project root
set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv" (
    echo Creating .venv...
    python -m venv .venv
)

echo Activating .venv...
call .venv\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt

echo Done. To activate manually: .venv\Scripts\activate
pause
