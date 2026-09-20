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

REM  Open the browser only once the server is answering.
REM
REM  This used to be a plain "start http://localhost:5000" on the line BEFORE
REM  the server was launched - a race the browser could never win. The page
REM  said it could not reach the site, a refresh a second later worked, and it
REM  read as "the pages are slow" rather than as a bug. Same on the Pi.
REM
REM  /b so this waits in the background and the server starts immediately.
REM  Run the helper through "cmd /c call", not by handing the .bat straight
REM  to START.
REM
REM  START was given an empty title, an option, a quoted path to a batch file
REM  and that batch file's own quoted argument, and left to work out that a
REM  .bat needs an interpreter. It did not run it, and said nothing about not
REM  running it - no error, no output, no browser. Three attempts were spent
REM  on the path before it turned out the path had been right all along and
REM  START simply was not launching the thing. 2026-09-20.
REM
REM  /b keeps it in this window instead of opening a second one.
start "Yobot browser" /b cmd /c call "%HERE%\open-when-ready.bat" 5000 "http://localhost:5000"

"%PY%" "%PROJ%\launcher_server.py"
endlocal
