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
REM  A short wait so the robot has time to connect before the browser opens.
REM  If the page looks empty, wait two seconds and refresh it.
start "" /b cmd /c "timeout /t 4 /nobreak >nul & start "" "http://localhost:%PORT%""

"%PY%" show_server.py %ARGS%

echo.
echo  The show has stopped.
pause
endlocal
