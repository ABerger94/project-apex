@echo off
setlocal
cd /d "%~dp0.."
set "PY=C:\Users\alekn\AppData\Local\Programs\Python\Python312\python.exe"

if exist "%PY%" (
  "%PY%" apex_loop.py --cycles 1
) else (
  python apex_loop.py --cycles 1
)

echo.
pause
