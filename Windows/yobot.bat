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

REM --- Which Python runs Yobot ----------------------------------------------
REM  THE STICK'S OWN PYTHON COMES FIRST. See yobot-launcher.bat for the full
REM  story. Same order in all four of these files and in the chess launchers,
REM  because the last bug of this kind survived by living in four copies of
REM  which only one got fixed.
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

cd /d "%PROJ%"
"%PY%" "%PROJ%\yobot_win.py" %*
endlocal
exit /b

:no_python
echo.
echo ===========================================================
echo    NO PYTHON FOUND
echo ===========================================================
echo.
echo    Looked for, in order:
echo.
echo      1. %PROJ%\..\python\python.exe   (a Yobot drive)
echo      2. %USERPROFILE%\yobot-venv      (an installed Yobot)
echo      3. "python" or "py" on this computer
echo.
pause
endlocal
exit /b 1
