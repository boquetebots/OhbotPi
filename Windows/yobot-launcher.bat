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

REM --- Which Python runs Yobot ----------------------------------------------
REM  THE STICK'S OWN PYTHON COMES FIRST. This order matters more than it looks.
REM
REM  WHAT THIS FIXES (found 2026-10-02, by the first outside tester)
REM  ---------------------------------------------------------------
REM  This file used to look ONLY at %USERPROFILE%\yobot-venv, and if that was
REM  missing it printed "run SETUP.bat" and fell through to a bare "python".
REM  It never looked at the stick's own python folder at all. So:
REM
REM    - on a laptop that HAS a venv, it ran the venv and worked. Every
REM      machine Yobot was ever tested on had one.
REM    - on a stranger's laptop with no venv, it ran whatever "python" meant
REM      on that machine - usually nothing, sometimes a Python with none of
REM      the packages - and died with "No module named 'flask'".
REM
REM  The stick carries a complete Python with every package already in it, two
REM  folders up from here, and it was never once used. The bug could not be
REM  seen from inside the project because everyone in the project had a venv.
REM
REM  The chess launchers were fixed for this on 2026-09-17 and a comment there
REM  claims this file already used that order. It did not. That wrong note is
REM  why nobody came and checked. Do not trust a comment about another file.
REM
REM  Written longhand with gotos, not as if/else blocks. cmd decides what to
REM  expand inside a parenthesised block before it decides which branch to
REM  take, so the tidy-looking version is the one that goes subtly wrong.
set "PY="

for %%I in ("%PROJ%\..\python\python.exe") do set "STICKPY=%%~fI"
if exist "%STICKPY%" set "PY=%STICKPY%"
if not "%PY%"=="" goto have_python

set "VENVPY=%USERPROFILE%\yobot-venv\Scripts\python.exe"
if exist "%VENVPY%" set "PY=%VENVPY%"
if not "%PY%"=="" goto have_python

where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if not "%PY%"=="" goto have_python

where py >nul 2>&1
if not errorlevel 1 set "PY=py"

:have_python
if "%PY%"=="" goto no_python

echo.
echo   Python: %PY%

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
exit /b

:no_python
echo.
echo ===========================================================
echo    NO PYTHON FOUND
echo ===========================================================
echo.
echo    Yobot could not find a Python to run with. It looked for:
echo.
echo      1. The Yobot drive's own Python, which should be at
echo         %PROJ%\..\python\python.exe
echo      2. An installed Yobot's Python, at
echo         %USERPROFILE%\yobot-venv
echo      3. "python" or "py" on this computer
echo.
echo    IF YOU ARE RUNNING FROM A USB DRIVE, number 1 is the one
echo    that should have worked. The usual cause is that the ZIP
echo    was not fully extracted - the python folder is large and
echo    is often the part that gets cut short. Extract it again
echo    and let it finish.
echo.
pause
endlocal
exit /b 1
