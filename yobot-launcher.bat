@echo off
REM ===========================================================================
REM  yobot-launcher.bat  —  starts the Launcher web page and opens the browser
REM ===========================================================================
REM  The Launcher is the easy front door: one page with buttons that start and
REM  stop the Greeter, the Sequence Builder, the Timeline, and Calibration.
REM
REM  Run it from D:\Projects\OhbotPi2 with:   .\yobot-launcher.bat
REM
REM  Leave this window open — closing it stops the Launcher.
REM  Press Ctrl-C in this window to stop it deliberately.
REM
REM  The first time you run it, Windows Firewall will ask for permission.
REM  Click "Allow access" (Private networks is enough).
REM ===========================================================================

setlocal
set "HERE=%~dp0"
set "VENVPY=%USERPROFILE%\yobot-venv\Scripts\python.exe"

if exist "%VENVPY%" (
    set "PY=%VENVPY%"
) else (
    echo [!] Yobot's venv was not found at %VENVPY%
    echo     Falling back to the system python. See Step 2 of SETUP_Windows.md.
    echo.
    set "PY=python"
)

cd /d "%HERE%"
start "" http://localhost:5000
"%PY%" "%HERE%launcher_server.py"
endlocal
