@echo off
REM ===========================================================================
REM  yobot-test.bat  -  does the robot move?
REM ===========================================================================
REM
REM  DOUBLE-CLICK THIS FILE. This is Step 6 of START_HERE_Windows.md.
REM
REM  Yobot should turn its head, nod, blink, open its mouth and change eye
REM  colour. No internet needed, no API keys needed - this only talks to the
REM  robot down the USB cable. If this works, the hardware side is good.
REM ===========================================================================

setlocal
title Yobot - Movement Test

set "HERE=%~dp0"
set "VENVPY=%USERPROFILE%\yobot-venv\Scripts\python.exe"

cd /d "%HERE%"

echo.
echo ===========================================================
echo    YOBOT  -  MOVEMENT TEST
echo ===========================================================
echo.

if not exist "%HERE%yobot_win.py" (
    echo  [X] yobot_win.py is not next to this file, so this is not
    echo      the Yobot folder. Move yobot-test.bat into the folder
    echo      that has yobot_win.py in it.
    echo.
    pause
    endlocal
    exit /b 1
)

if not exist "%VENVPY%" (
    echo  [X] Yobot has not been set up on this laptop yet.
    echo.
    echo      Double-click  SETUP.bat  first, let it finish, then
    echo      come back to this one.
    echo.
    pause
    endlocal
    exit /b 1
)

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

"%VENVPY%" "%HERE%yobot_win.py" test
set "RESULT=%ERRORLEVEL%"

echo.
echo -----------------------------------------------------------
if "%RESULT%"=="0" (
    echo   Test finished.
    echo.
    echo   Did the head move and the eyes change colour?
    echo.
    echo     YES - setup is done. Double-click yobot-launcher.bat
    echo           to actually use Yobot.
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
    echo   START_HERE_Windows.md.
)
echo -----------------------------------------------------------
echo.
pause
endlocal
exit /b 0
