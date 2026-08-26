@echo off
REM ===========================================================================
REM  SETUP.bat  -  one-click Windows setup for Yobot
REM ===========================================================================
REM  DOUBLE-CLICK THIS FILE. That is the whole instruction.
REM  This is Step 3 of "START HERE.md" in this folder.
REM
REM  It checks Python, builds Yobot's private Python sandbox, installs every
REM  package, then tells you plainly what is still missing.
REM  It changes nothing outside the project folder and %USERPROFILE%\yobot-venv.
REM  Safe to run again any time.
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

title Yobot Windows Setup
set "VENV=%USERPROFILE%\yobot-venv"
set "VENVPY=%VENV%\Scripts\python.exe"
set "PROBLEMS=0"

echo.
echo ===========================================================
echo    YOBOT  -  WINDOWS SETUP
echo ===========================================================
echo.
echo  Project folder : %PROJ%
echo  Sandbox to make: %VENV%
echo.
echo  This takes about 5 minutes. The Azure speech package is
echo  large, so there will be a long quiet patch. That is normal.
echo.
pause
echo.

echo [1/5] Checking I can find the project...
if not exist "%PROJ%\yobot_win.py" goto :wrongfolder
if not exist "%PROJ%\requirements.txt" goto :wrongfolder
echo       OK - found the project at %PROJ%
echo.

echo [2/5] Looking for Python...
set "PY="
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

echo [4/5] Installing the packages Yobot needs...
echo       (long quiet patch here - do not close this window)
echo.
"%VENVPY%" -m pip install --upgrade pip --quiet
"%VENVPY%" -m pip install -r "%PROJ%\requirements.txt"
if errorlevel 1 goto :pipfailed
echo.
echo       OK - packages installed.
"%VENVPY%" -c "import serial, azure.cognitiveservices.speech" >nul 2>&1
if errorlevel 1 (
    echo       [!] Packages installed but a test import failed.
    echo           Try running this file again.
    set "PROBLEMS=1"
) else (
    echo       OK - test import passed.
)
echo.

echo [5/5] Checking the files that are not in the download...
echo.
if exist "%PROJ%\.env" (
    findstr /C:"your_azure_speech_key_here" "%PROJ%\.env" >nul 2>&1
    if errorlevel 1 (
        echo       OK  .env is present and looks filled in.
    ) else (
        echo       [!] .env is present but still has PLACEHOLDER keys in it.
        echo           Yobot cannot speak or think until the real ones go in.
        set "PROBLEMS=1"
    )
) else (
    if exist "%PROJ%\.env.example" (
        copy "%PROJ%\.env.example" "%PROJ%\.env" >nul
        echo       [!] .env was missing. I made you one from .env.example.
        echo           It has PLACEHOLDER keys - paste your real ones in.
        echo           See "Getting your API keys.md" in the main folder.
    ) else (
        echo       [!] .env is missing and there is no .env.example to copy.
    )
    set "PROBLEMS=1"
)

if exist "%PROJ%\ohbotData\MotorDefinitions*.omd" (
    echo       OK  robot calibration found in ohbotData
) else (
    echo       [!] No MotorDefinitions .omd file in ohbotData
    echo           The robot will still move, but on generic limits
    echo           rather than your robot's own measured ones.
    set "PROBLEMS=1"
)
echo.

echo ===========================================================
if "%PROBLEMS%"=="0" (
    echo    SETUP COMPLETE - nothing outstanding.
) else (
    echo    SETUP DONE - but read the [!] lines above first.
)
echo ===========================================================
echo.
echo  What to double-click next, in this folder, in this order:
echo.
echo      yobot-test.bat       plug Yobot in, power on, check it moves
echo      yobot-launcher.bat   the control page - this is the everyday one
echo      yobot-stop.bat       only if something gets stuck
echo.
echo  Stuck? "START HERE.md" in this folder is the plain-English guide.
echo.
pause
endlocal
exit /b 0

:wrongfolder
echo.
echo  [X] I could not find the Yobot project files.
echo.
echo      I looked in:
echo        %HERE%
echo        and one level up.
echo.
echo      This file belongs in the project's "Windows" folder. If you
echo      moved it somewhere else, move it back and try again.
echo.
echo      Also check you actually EXTRACTED the ZIP. Windows lets you
echo      peek inside a ZIP as if it were a folder, and nothing works
echo      properly from in there. Right-click the ZIP - Extract All.
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
echo      that is Windows' placeholder, not the real thing.
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
echo      Most likely:
echo        - the Python install is missing its venv part
echo          re-run the python.org installer, choose Modify,
echo          and make sure everything is ticked
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
echo        - an old Python. Yobot wants Python 3.9 or newer.
echo.
echo      Scroll up - the LAST few red lines say which package stopped
echo      and why. Copy those lines to Claude if they mean nothing to you.
echo.
echo      Running this file again is safe and often just works.
echo.
pause
endlocal
exit /b 1
