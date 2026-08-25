@echo off
REM ===========================================================================
REM  SETUP.bat  -  one-click Windows setup for Yobot / Ohbot
REM ===========================================================================
REM
REM  DOUBLE-CLICK THIS FILE. That is the whole instruction.
REM  This is Step 3 of START_HERE_Windows.md.
REM
REM  It does the fiddly parts for you:
REM
REM    1. checks Python is installed and usable
REM    2. builds Yobot's own private Python sandbox (the "venv")
REM    3. installs every package the robot needs
REM    4. tells you plainly what is still missing (.env keys, calibration)
REM
REM  It changes NOTHING outside this folder and %USERPROFILE%\yobot-venv.
REM  It is safe to run again if it fails partway, or after a code update.
REM ===========================================================================

setlocal
title Yobot Windows Setup
color 07

set "HERE=%~dp0"
set "VENV=%USERPROFILE%\yobot-venv"
set "VENVPY=%VENV%\Scripts\python.exe"
set "PROBLEMS=0"

cd /d "%HERE%"

echo.
echo ===========================================================
echo    YOBOT  -  WINDOWS SETUP
echo ===========================================================
echo.
echo  Project folder : %HERE%
echo  Sandbox to make: %VENV%
echo.
echo  This takes about 5 minutes. The Azure speech package is
echo  large, so there will be a long quiet patch. That is normal.
echo.
pause
echo.


REM ---------------------------------------------------------------------------
REM  STEP 0  -  are we actually in the project folder?
REM ---------------------------------------------------------------------------
echo [1/5] Checking this is the right folder...

if not exist "%HERE%yobot_win.py" goto :wrongfolder
if not exist "%HERE%requirements.txt" goto :wrongfolder
echo       OK - found yobot_win.py and requirements.txt
echo.


REM ---------------------------------------------------------------------------
REM  STEP 1  -  find a working Python
REM ---------------------------------------------------------------------------
echo [2/5] Looking for Python...

set "PY="

REM  Try the Python Launcher first. It is the most reliable, and it is not
REM  fooled by the Microsoft Store placeholder that pretends to be python.exe.
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"

if not defined PY (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY=python"
)

if not defined PY goto :nopython

for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo       OK - found %PYVER%
echo.


REM ---------------------------------------------------------------------------
REM  STEP 2  -  build the venv
REM ---------------------------------------------------------------------------
echo [3/5] Building Yobot's Python sandbox...

if exist "%VENVPY%" (
    echo       Already there - reusing it.
) else (
    %PY% -m venv "%VENV%"
    if errorlevel 1 goto :venvfailed
    if not exist "%VENVPY%" goto :venvfailed
    echo       OK - created %VENV%
)
echo.


REM ---------------------------------------------------------------------------
REM  STEP 3  -  install the packages
REM ---------------------------------------------------------------------------
echo [4/5] Installing the packages Yobot needs...
echo       (long quiet patch here - do not close this window)
echo.

"%VENVPY%" -m pip install --upgrade pip --quiet
"%VENVPY%" -m pip install -r "%HERE%requirements.txt"
if errorlevel 1 goto :pipfailed

echo.
echo       OK - packages installed.
echo.

REM  Prove it: import the two that matter most.
"%VENVPY%" -c "import serial, azure.cognitiveservices.speech" >nul 2>&1
if errorlevel 1 (
    echo       [!] Packages installed but a test import failed.
    echo           Try running this file again.
    set "PROBLEMS=1"
) else (
    echo       OK - test import passed.
)
echo.


REM ---------------------------------------------------------------------------
REM  STEP 4  -  the two things git deliberately does NOT carry
REM ---------------------------------------------------------------------------
echo [5/5] Checking the files that are not in GitHub...
echo.

REM  --- .env (API keys) ---
if exist "%HERE%.env" (
    findstr /C:"your_azure_speech_key_here" "%HERE%.env" >nul 2>&1
    if errorlevel 1 (
        echo       OK  .env is present and looks filled in.
    ) else (
        echo       [!] .env is present but still has the PLACEHOLDER keys in it.
        echo           Yobot will not speak or think until the real ones go in.
        set "PROBLEMS=1"
    )
) else (
    if exist "%HERE%.env.example" (
        copy "%HERE%.env.example" "%HERE%.env" >nul
        echo       [!] .env was missing. I made you one from .env.example.
        echo           It has PLACEHOLDER keys - you must paste the real ones in.
        echo           Copy them from the Pi or the Mac.
    ) else (
        echo       [!] .env is missing and there is no .env.example to copy.
        echo           Copy .env from the Pi or the Mac by hand.
    )
    set "PROBLEMS=1"
)

REM  --- calibration ---
if exist "%HERE%ohbotData\MotorDefinitions*.omd" (
    echo       OK  robot calibration found in ohbotData\
) else (
    echo       [!] No MotorDefinitions*.omd in ohbotData\
    echo           The robot will still move, but on generic limits
    echo           rather than your robot's own measured ones.
    echo           Copy ohbotData\ from the Pi or the Mac.
    set "PROBLEMS=1"
)
echo.


REM ---------------------------------------------------------------------------
REM  DONE
REM ---------------------------------------------------------------------------
echo ===========================================================
if "%PROBLEMS%"=="0" (
    echo    SETUP COMPLETE - nothing outstanding.
) else (
    echo    SETUP DONE - but read the [!] lines above first.
)
echo ===========================================================
echo.
echo  What to double-click next, in this order:
echo.
echo      yobot-test.bat       plug Yobot in, power on, check it moves
echo      yobot-launcher.bat   the web page - this is the everyday one
echo      yobot-stop.bat       only if something gets stuck
echo.
echo  Stuck? START_HERE_Windows.md is the plain-English guide.
echo  SETUP_Windows.md is the longer technical one.
echo.
pause
endlocal
exit /b 0


REM ===========================================================================
REM  Failure exits - each says what to do, not just what went wrong
REM ===========================================================================

:wrongfolder
echo.
echo  [X] This does not look like the Ohbot project folder.
echo.
echo      I could not find yobot_win.py and requirements.txt next to
echo      this batch file.
echo.
echo      If you downloaded the ZIP from GitHub, the unzipped folder is
echo      usually called OhbotPi2-main and there is often a SECOND folder
echo      of the same name inside it. This file has to sit in the one that
echo      actually contains yobot_win.py.
echo.
echo      Move setup-windows.bat in there and double-click it again.
echo.
pause
endlocal
exit /b 1

:nopython
echo       [X] Python was not found.
echo.
echo      Install it from  https://www.python.org/downloads/
echo.
echo      IMPORTANT: on the FIRST screen of the installer, tick
echo      "Add python.exe to PATH" before you click Install.
echo      It is easy to miss and everything here depends on it.
echo.
echo      If the Microsoft Store opened instead of Python just now,
echo      that is Windows' placeholder, not the real thing - the real
echo      installer from python.org replaces it.
echo.
echo      Then run this file again.
echo.
pause
endlocal
exit /b 1

:venvfailed
echo.
echo      [X] Could not build the sandbox at %VENV%
echo.
echo      Most likely causes:
echo        - the Python install is missing its venv part
echo          (re-run the python.org installer, choose Modify,
echo           and make sure everything is ticked)
echo        - a leftover half-made folder is in the way. Delete
echo          %VENV% in File Explorer and run this again.
echo.
pause
endlocal
exit /b 1

:pipfailed
echo.
echo      [X] Installing the packages failed.
echo.
echo      Nearly always one of these:
echo        - no internet connection right now
echo        - a company firewall or VPN blocking pip
echo        - you are on an old Python. Yobot wants Python 3.9 or newer.
echo.
echo      Scroll up - the LAST few red lines say which package stopped
echo      and why. Copy those lines to Claude if they mean nothing to you.
echo.
echo      Running this file again is safe and often just works.
echo.
pause
endlocal
exit /b 1
