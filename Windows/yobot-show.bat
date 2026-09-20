@echo off
REM ===========================================================================
REM  yobot-show.bat  -  Yobot's offline show, and the cue editor
REM ===========================================================================
REM  Double-click this. It starts the show and opens the page in your browser.
REM
REM  NO INTERNET IS NEEDED to run the show. Internet is only needed to RECORD
REM  new lines, which you do at the Clubhouse before you travel.
REM
REM  Leave this window open - closing it stops Yobot.
REM  The first time, Windows Firewall will ask. Click "Allow access".
REM ===========================================================================

setlocal enabledelayedexpansion
title Yobot Show

set "PORT=5004"

REM --- Find the project folder (works from Windows\ or from the root) -------
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "PROJ=%HERE%"
if not exist "%PROJ%\show_server.py" (
    for %%I in ("%HERE%\..") do set "PROJ=%%~fI"
)

if not exist "%PROJ%\show_server.py" (
    echo.
    echo  [X] Could not find the Yobot project files.
    echo      This file belongs in the project's Windows folder.
    echo.
    pause
    endlocal
    exit /b 1
)

cd /d "%PROJ%"

REM --- Yobot's own Python --------------------------------------------------
set "VENVPY=%USERPROFILE%\yobot-venv\Scripts\python.exe"
if exist "%VENVPY%" (
    set "PY=%VENVPY%"
) else (
    echo.
    echo  [!] Yobot's Python was not found.
    echo      Double-click SETUP.bat in this folder first.
    echo.
    set "PY=python"
)

echo ============================================================
echo   YOBOT SHOW
echo   Folder: %PROJ%
echo ============================================================
echo.

REM --- Already running? Just open the page ---------------------------------
netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo  The show is already running. Opening the page.
    start "" "http://localhost:%PORT%"
    echo.
    pause
    endlocal
    exit /b 0
)

REM --- Are there any recordings? -------------------------------------------
set "CACHED=0"
if exist "voice_cache" (
    for /f %%C in ('dir /b "voice_cache\*.wav" 2^>nul ^| find /c /v ""') do set "CACHED=%%C"
)
if "!CACHED!"=="0" (
    echo  [!] NOTHING IS RECORDED YET - Yobot will not be able to speak.
    echo.
    echo      Open the editor once you are running, and press
    echo      "Record the new lines". THAT STEP NEEDS INTERNET.
    echo.
    pause
) else (
    echo  Recorded lines: !CACHED!
)

REM --- Which robot? --------------------------------------------------------
set "CURRENT=(none)"
if exist "ohbotData\active_robot.txt" (
    set /p CURRENT=<"ohbotData\active_robot.txt"
)
echo.
echo  Calibration currently loaded: !CURRENT!
set "ROBOT="
set /p "ROBOT=Robot name to load, or press Enter to keep !CURRENT!: "

set "ARGS="
if not "!ROBOT!"=="" set "ARGS=--robot !ROBOT!"

REM --- Go ------------------------------------------------------------------
echo.
echo  Starting... the page will open on its own.
echo.
REM  Wait for the server to answer, then open the browser.
REM
REM  This was a fixed 4-second pause. Better than the launcher's version,
REM  which did not wait at all - but still a guess: comfortable on this PC,
REM  short on a Pi, and much too short on the first run from a USB stick,
REM  where Python is loading thousands of small files off flash. Asking the
REM  port is right on every machine and wastes no time on a fast one.
REM  %HERE%, not %~dp0. This file is called by name from the stick's
REM  START YOBOT.bat, which does a "cd /d" into the Windows folder and then
REM  call "yobot-launcher.bat" - a RELATIVE name. That makes %0 relative, so
REM  %~dp0 is resolved against the CURRENT directory each time it is expanded,
REM  and line 40 above has already changed that to the project folder. The
REM  result was "cannot find F:\OhbotPi2\open-when-ready.bat" - one folder up
REM  from where it lives. %HERE% is captured at the top, before any cd, which
REM  is exactly why it is captured at the top.
REM  "cmd /c call", not the bare .bat - see yobot-launcher.bat. Handing a
REM  batch file straight to START silently did nothing at all on 2026-09-20.
start "Yobot browser" /b cmd /c call "%HERE%\open-when-ready.bat" %PORT% "http://localhost:%PORT%"

"%PY%" show_server.py %ARGS%

echo.
echo  The show has stopped.
pause
endlocal
