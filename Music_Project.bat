@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "MPLCONFIGDIR=%~dp0data\matplotlib"
set "PROJECT_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PROJECT_PY%" (
    echo Project virtual environment not found. See README.md for installation.
    pause
    exit /b 1
)
"%PROJECT_PY%" -c "import streamlit, numpy, scipy, matplotlib, mutagen"
if errorlevel 1 (
    echo Missing Python dependencies. Run: .venv\Scripts\python.exe -m pip install -e .
    pause
    exit /b 1
)
"%PROJECT_PY%" -c "import shutil; print('FFmpeg: '+(shutil.which('ffmpeg') or 'Backend unavailable; configure in Settings')); print('ffprobe: '+(shutil.which('ffprobe') or 'Backend unavailable; configure in Settings'))"
"%PROJECT_PY%" -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 pause
