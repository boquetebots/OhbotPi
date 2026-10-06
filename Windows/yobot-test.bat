@echo off
REM ===========================================================================
REM  yobot-test.bat  -  does the robot move?
REM ===========================================================================
REM  DOUBLE-CLICK THIS FILE. This is Step 6 of "START HERE.md" in this folder.
REM  On a Yobot drive it is what "TEST THIS COMPUTER.bat" runs.
REM
REM  Yobot should turn its head, nod, blink, open its mouth and change eye
REM  colour. No internet, no API keys - this only talks to the robot down the
REM  USB cable. If this works, the hardware side is good.
REM ===========================================================================

setlocal
REM --- Find the project folder --------------------------------------------
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "PROJ=%HERE%"
if not exist "%PROJ%\yobot_win.py" (
    for %%I in ("%HERE%\..") do set "PROJ=%%~fI"
)

title Yobot - Movement Test

echo.
echo ===========================================================
echo    YOBOT  -  MOVEMENT TEST
echo ===========================================================
echo.

if not exist "%PROJ%\yobot_win.py" (
    echo  [X] I could not find the Yobot project files.
    echo      This file belongs in the project's "Windows" folder.
    echo.
    pause
    endlocal
    exit /b 1
)

REM --- Which Python runs Yobot ----------------------------------------------
REM  THE STICK'S OWN PYTHON COMES FIRST. See yobot-launcher.bat for the full
REM  story.
REM
REM  This file was the worst of the four. It did not just prefer the venv - it
REM  REFUSED TO RUN without one, with "Yobot has not been set up on this
REM  laptop yet, double-click SETUP.bat". On a Yobot drive there is no
REM  SETUP.bat, by design, and no venv is wanted or needed.
REM
REM  So the one file the guide tells a stranger to run FIRST, to find out
REM  whether their computer can run Yobot, was guaranteed to fail on exactly
REM  the computers it exists to check. Found 2026-10-02 by the first tester
REM  outside the project.
REM
REM  Longhand with gotos on purpose - cmd expands the whole of a parenthesised
REM  block before it picks a branch.
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

echo  Before you carry on, check both of these:
echo.
echo    1. Yobot's USB cable is plugged into THIS laptop
echo    2. Yobot's power supply is switched on
echo.
echo  If Yobot is normally attached to the Raspberry Pi, stop it
echo  there first - only one computer can drive the robot at a time.
echo.
pause
echo.
echo  Running the test - watch the robot, not the screen...
echo.

cd /d "%PROJ%"
"%PY%" "%PROJ%\yobot_win.py" test
set "RESULT=%ERRORLEVEL%"

echo.
echo -----------------------------------------------------------
if "%RESULT%"=="0" (
    echo   Test finished.
    echo.
    echo   Did the head move and the eyes change colour?
    echo.
    echo     YES - setup is done. Now start Yobot properly:
    echo           on a Yobot drive, double-click START YOBOT.bat
    echo           at the top of the drive. On an installed copy,
    echo           double-click yobot-launcher.bat in this folder.
    echo.
    echo     NO  - the laptop found the robot but nothing moved.
    echo           Check the power supply is on, not just the USB.
) else (
    echo   The test did not complete.
    echo.
    echo   If it said "Robot not found":
    echo     1. Unplug the USB cable, count to five, plug it back in
    echo     2. Check the power supply is on
    echo     3. Run this file again
    echo.
    echo   Still nothing? Windows may be missing the driver for
    echo   Yobot's controller board. See Troubleshooting in
    echo   "START HERE.md".
)
echo -----------------------------------------------------------
echo.
pause
endlocal
exit /b 0

:no_python
echo.
echo ===========================================================
echo    NO PYTHON FOUND
echo ===========================================================
echo.
echo    This test could not find a Python to run with. It looked for:
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
