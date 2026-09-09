@echo off
REM ===========================================================================
REM  catch-up-from-github.bat  -  bring THIS Windows PC up to date
REM ===========================================================================
REM  Use this when work was done on the Mac (or a Pi) and pushed to GitHub,
REM  and this computer does not have it yet.
REM
REM  It is careful on purpose: if you have your own unsaved work here, it
REM  STOPS and tells you, rather than writing over it.
REM ===========================================================================

setlocal enabledelayedexpansion
title Yobot - catch up from GitHub

set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "PROJ=%HERE%"
if not exist "%PROJ%\show_server.py" (
    for %%I in ("%HERE%\..") do set "PROJ=%%~fI"
)
if not exist "%PROJ%\.git" (
    echo.
    echo  [X] This folder is not a git copy of the project.
    echo      Nothing to catch up. You can download a fresh ZIP from GitHub
    echo      instead: github.com/boquetebots/OhbotPi
    echo.
    pause
    endlocal
    exit /b 1
)

cd /d "%PROJ%"
echo ============================================================
echo   CATCHING UP FROM GITHUB
echo   Folder: %PROJ%
echo ============================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo  [X] Git is not installed on this computer.
    echo      Download it from git-scm.com, then run this again.
    echo.
    pause
    endlocal
    exit /b 1
)

echo  Checking GitHub...
git fetch origin
if errorlevel 1 (
    echo.
    echo  [X] Could not reach GitHub. Is this computer online?
    echo.
    pause
    endlocal
    exit /b 1
)

REM --- Any of your own unsaved work here? ----------------------------------
set "DIRTY="
for /f "delims=" %%L in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo.
    echo  [!] STOPPING - you have changes here that are not saved to GitHub:
    echo.
    git status --short
    echo.
    echo      Nothing has been changed. Two choices:
    echo        - If this work matters, run push-to-github.bat FIRST.
    echo        - If it does not, tell Michael before going any further.
    echo.
    pause
    endlocal
    exit /b 1
)

REM --- Behind, ahead, or split? --------------------------------------------
for /f %%A in ('git rev-list --count HEAD..origin/main') do set "BEHIND=%%A"
for /f %%B in ('git rev-list --count origin/main..HEAD') do set "AHEAD=%%B"

if "%BEHIND%"=="0" if "%AHEAD%"=="0" (
    echo.
    echo  Already up to date. Nothing to do.
    echo.
    pause
    endlocal
    exit /b 0
)

if not "%AHEAD%"=="0" (
    echo.
    echo  [!] STOPPING - this computer has %AHEAD% change^(s^) GitHub does not,
    echo      and GitHub has %BEHIND% this computer does not.
    echo.
    echo      That is a genuine fork and only a person can decide it.
    echo      Tell Claude "Windows and GitHub have split" and it will sort it.
    echo.
    pause
    endlocal
    exit /b 1
)

echo.
echo  GitHub has %BEHIND% change^(s^) to bring down.
echo.
git merge --ff-only origin/main
if errorlevel 1 (
    echo.
    echo  [X] Could not update cleanly. Nothing was half-done - your files
    echo      are as they were. Tell Claude what this window says.
    echo.
    pause
    endlocal
    exit /b 1
)

echo.
echo  ============================================================
echo   Up to date.
echo  ============================================================
echo.
echo   Your keys (.env), your recordings (voice_cache) and the robot
echo   calibration in use are NOT part of GitHub, so they were left
echo   exactly as they were. That is on purpose.
echo.
pause
endlocal
