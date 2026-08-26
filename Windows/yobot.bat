@echo off
REM ===========================================================================
REM  yobot.bat  -  the easy way to run Yobot on Windows
REM ===========================================================================
REM      .\yobot.bat ports          list the COM ports Windows can see
REM      .\yobot.bat test           move the head - no internet needed
REM      .\yobot.bat say "Hello"    speak with lip sync
REM      .\yobot.bat                the full conversation bot
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

if not exist "%PROJ%\yobot_win.py" (
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
    echo [!] Yobot's venv was not found at %VENVPY%
    echo     Falling back to the system python. If packages are missing,
    echo     double-click SETUP.bat in this folder.
    echo.
    set "PY=python"
)

cd /d "%PROJ%"
"%PY%" "%PROJ%\yobot_win.py" %*
endlocal
