@echo off
REM ===========================================================================
REM  yobot.bat  —  the easy way to run Yobot on Windows
REM ===========================================================================
REM  Works the same in PowerShell and in Command Prompt, so you don't have to
REM  remember which one you're in or how each spells things.
REM
REM  Use it like this (from D:\Projects\OhbotPi2):
REM
REM      .\yobot.bat ports          list the COM ports Windows can see
REM      .\yobot.bat test           move the head — no internet needed
REM      .\yobot.bat say "Hello"    speak with lip sync
REM      .\yobot.bat                the full conversation bot
REM
REM  It finds Yobot's venv python by itself. If the venv isn't made yet it
REM  falls back to plain python, which will tell you what's missing.
REM ===========================================================================

setlocal
set "HERE=%~dp0"
set "VENVPY=%USERPROFILE%\yobot-venv\Scripts\python.exe"

if exist "%VENVPY%" (
    set "PY=%VENVPY%"
) else (
    echo [!] Yobot's venv was not found at %VENVPY%
    echo     Falling back to the system python. If packages are missing,
    echo     see Step 2 of SETUP_Windows.md.
    echo.
    set "PY=python"
)

cd /d "%HERE%"
"%PY%" "%HERE%yobot_win.py" %*
endlocal
