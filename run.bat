@echo off
cd /d "%~dp0"
call "%~dp0.venv\Scripts\activate.bat"
python "%~dp0certificate-downloader\download_by_nop.py"
pause
