@echo off
setlocal

REM =============================
REM VideoBreak Pro - Build EXE
REM =============================

where python >nul 2>nul
if errorlevel 1 (
  echo Python non trovato. Installa Python 3.10+ e abilita "Add to PATH".
  pause
  exit /b 1
)

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "VideoBreakPro" ^
  --add-data "assets;assets" ^
  src\videobreak_pro.py

echo.
echo OK! EXE creato: dist\VideoBreakPro.exe
pause
