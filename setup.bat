@echo off
cd /d "%~dp0"
if not exist .venv (
    echo Creation du venv...
    py -3.14 -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo.
echo Installation terminee. Lancez le logiciel avec run.bat
pause