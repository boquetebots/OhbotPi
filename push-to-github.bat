@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  push-to-github.bat
REM
REM  The Windows twin of push_to_github.command (which only runs on the Mac).
REM  Commits whatever you've changed on this Windows PC and sends it to GitHub,
REM  so the Mac and the Pi can pull it down.
REM
REM  HOW TO USE IT: double-click this file. That's it. It will talk you through
REM  everything and stop safely if anything looks wrong.
REM
REM  It refuses to push if it spots an API key in what you're about to send.
REM
REM  Created 2026-08-12.  Updated same day to auto-fix "dubious ownership".
REM ============================================================================

cd /d "%~dp0"
title Push Ohbot work to GitHub
cls
echo.
echo   ============================================
echo     Push Ohbot work to GitHub  (Windows)
echo   ============================================
echo.
echo   Folder: %CD%
echo.

REM ---------------------------------------------------------------------------
REM  Check 1 - is git even installed?
REM ---------------------------------------------------------------------------
git --version >nul 2>&1
if errorlevel 1 (
    echo   [X] Git isn't installed, or Windows can't find it.
    echo       Install it from https://git-scm.com/download/win
    echo       then close this window and try again.
    echo.
    pause
    exit /b 1
)
echo   [ok] Git is installed

REM ---------------------------------------------------------------------------
REM  Check 1b - "dubious ownership"
REM
REM  This folder was created by a different Windows user account than the one
REM  you're logged in as. Git blocks that by default, because on a SHARED
REM  computer someone else's repo could contain scripts that run as you.
REM
REM  On your own PC it's a false alarm, so we tell git this folder is fine.
REM  It only has to happen once; after that this block does nothing.
REM ---------------------------------------------------------------------------
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo   [!] Windows says this folder belongs to another user account.
    echo       On your own PC that's harmless. Telling git it's safe...
    git config --global --add safe.directory "%CD:\=/%"
    git rev-parse --is-inside-work-tree >nul 2>&1
    if errorlevel 1 (
        echo.
        echo   [X] That didn't clear it. Show this whole window to Claude.
        echo.
        pause
        exit /b 1
    )
    echo   [ok] Sorted - you won't see that message again
)

REM ---------------------------------------------------------------------------
REM  Check 2 - are we on the main branch?
REM ---------------------------------------------------------------------------
set "BRANCH="
for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%B
if not "%BRANCH%"=="main" (
    echo   [X] This folder is on branch "%BRANCH%", but it should be "main".
    echo       Nothing has been changed. Ask Claude before going further.
    echo.
    pause
    exit /b 1
)
echo   [ok] On branch main

REM ---------------------------------------------------------------------------
REM  Check 3 - is a crashed git process blocking us?
REM  A leftover lock file makes every git command fail with
REM  "Another git process seems to be running". Usually it's just debris.
REM ---------------------------------------------------------------------------
if exist ".git\index.lock" (
    echo   [!] Found a leftover git lock file from a crashed command.
    del /q ".git\index.lock" >nul 2>&1
    if exist ".git\index.lock" (
        echo   [X] Couldn't remove .git\index.lock - close any other git
        echo       windows or editors, then run this again.
        echo.
        pause
        exit /b 1
    )
    echo   [ok] Cleared it
)

REM ---------------------------------------------------------------------------
REM  Check 4 - has anyone else pushed since you last pulled?
REM  If the Mac or Pi pushed something, you must pull it FIRST or git will
REM  reject your push (or worse, create a tangled merge).
REM ---------------------------------------------------------------------------
echo   ... checking GitHub
git fetch origin main --quiet
if errorlevel 1 (
    echo   [X] Couldn't reach GitHub. Check your internet connection.
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%R in ('git rev-parse origin/main') do set REMOTEHEAD=%%R
for /f "delims=" %%M in ('git merge-base HEAD origin/main') do set MERGEBASE=%%M

if not "%REMOTEHEAD%"=="%MERGEBASE%" (
    echo.
    echo   [!] GitHub has changes you don't have yet - probably pushed
    echo       from the Mac or the Pi.
    echo.
    echo       Run this first, in this same folder:
    echo           git pull origin main
    echo.
    echo       Then run this script again. Stopping now so nothing tangles.
    echo.
    pause
    exit /b 1
)
echo   [ok] You're up to date with GitHub

REM ---------------------------------------------------------------------------
REM  Is there anything to send at all?
REM ---------------------------------------------------------------------------
git status --porcelain > "%TEMP%\ohbot_status.txt"
for /f %%A in ('type "%TEMP%\ohbot_status.txt" ^| find /c /v ""') do set CHANGECOUNT=%%A
if "%CHANGECOUNT%"=="0" (
    echo.
    echo   Nothing has changed. There's nothing to push.
    echo.
    pause
    exit /b 0
)

echo.
echo   ============================================
echo     These %CHANGECOUNT% files will be sent
echo   ============================================
echo.
git status --short
echo.

REM ---------------------------------------------------------------------------
REM  SECRET CHECK - stage everything, then inspect it before committing.
REM  Staging is reversible; nothing leaves this PC until the push at the end.
REM ---------------------------------------------------------------------------
git add -A

echo   ... scanning for API keys
set SECRETFOUND=0

REM  (a) any file whose NAME looks like a secrets file
git diff --cached --name-only > "%TEMP%\ohbot_staged.txt"
findstr /I /R /C:"^\.env$" /C:"git_keys" /C:"id_rsa" /C:"\.pem$" /C:"\.p12$" /C:"credential" "%TEMP%\ohbot_staged.txt" >nul 2>&1
if not errorlevel 1 set SECRETFOUND=1

REM  (b) any key-shaped text inside what you're about to send
git diff --cached -U0 > "%TEMP%\ohbot_diff.txt"
findstr /R /C:"sk-[A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-][A-Za-z0-9_-]" /C:"ghp_[A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9]" /C:"AKIA[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]" "%TEMP%\ohbot_diff.txt" >nul 2>&1
if not errorlevel 1 set SECRETFOUND=1

if "%SECRETFOUND%"=="1" (
    echo.
    echo   ############################################
    echo     STOPPED - possible API key detected
    echo   ############################################
    echo.
    echo   Something in this batch of changes looks like a real API key
    echo   or a secrets file. Nothing has been sent to GitHub.
    echo.
    echo   Everything has been un-staged, so you're back where you started.
    echo   Show this message to Claude and it can tell you which file it is.
    echo.
    git reset >nul
    pause
    exit /b 1
)
echo   [ok] No API keys found in these changes

REM ---------------------------------------------------------------------------
REM  Commit message
REM ---------------------------------------------------------------------------
echo.
echo   ============================================
echo     What did you change?
echo   ============================================
echo.
echo   Write a short note so you can find this later, for example:
echo     Windows audio lead-in fix
echo     Azure voice benchmark script
echo.
set "MSG="
set /p MSG=  Your note:

if "%MSG%"=="" (
    echo.
    echo   No note given - nothing committed. Un-staging and stopping.
    git reset >nul
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM  Commit and push
REM ---------------------------------------------------------------------------
echo.
echo   ... saving your changes
git commit -m "%MSG% (from Windows)"
if errorlevel 1 (
    echo   [X] The commit failed. Nothing was sent. Show this to Claude.
    echo.
    pause
    exit /b 1
)

echo   ... sending to GitHub
git push origin main
if errorlevel 1 (
    echo.
    echo   [X] The push failed. Your work IS saved locally - it just didn't
    echo       reach GitHub. Usually this means your GitHub sign-in expired.
    echo       Show this to Claude.
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM  Done
REM ---------------------------------------------------------------------------
echo.
echo   ============================================
echo     Done - your work is on GitHub
echo   ============================================
echo.
echo   To bring the other machines in line:
echo.
echo     On the Mac:  cd ~/Projects/OhbotPi2
echo                  git pull origin main
echo.
echo     On the Pi:   cd ~/Projects/Ohbot
echo                  git pull origin main
echo                  sudo systemctl restart ohbot-gui
echo.
del "%TEMP%\ohbot_status.txt" "%TEMP%\ohbot_staged.txt" "%TEMP%\ohbot_diff.txt" >nul 2>&1
pause
exit /b 0
