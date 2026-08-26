@echo off
REM ===========================================================================
REM  yobot-launcher.bat  -  starts the control page and opens your browser
REM ===========================================================================
REM  This is the everyday one. One web page with buttons that start and stop
REM  the Greeter, the Sequence Builder, the Timeline and Calibration.
REM
REM  Leave this window open - closing it stops Yobot.
REM  The first time, Windows Firewall will ask. Click "Allow access".
REM ===========================================================================

setlocal
REM --- Find the project folder --------------------------------------------
REM  This works whether the file sits in the Windows folder or in the main
REM  project folder. It looks beside itself first, then one level up.
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "PROJ=%HERE%"
if not exist "%PROJ%\yobot_win.py" (
    for %%I in ("%HERE%\..") do set "PROJ=%%~fI"
)

if not exist "%PROJ%\launcher_server.py" (
    echo [X] Could not find the Yobot project files.
    echo     This file should be in the project's Windows folder.
    pause
    endlocal
    exit /b 1
)

set "VENVPY=%USERPROFILE%\yobot-venv\Scripts\python.exe"
if exist "%VENVPY%" (
    set "PY=%VENVPY%"
) else (
    echo [!] Yobot's venv was not found. Double-click SETUP.bat in this folder first.
    echo.
    set "PY=python"
)

cd /d "%PROJ%"
start "" http://localhost:5000
"%PY%" "%PROJ%\launcher_server.py"
endlocal
