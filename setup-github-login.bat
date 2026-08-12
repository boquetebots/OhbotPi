@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  setup-github-login.bat
REM
REM  RUN THIS ONCE. After it succeeds, you never touch it again and
REM  push-to-github.bat will just work.
REM
REM  It teaches git on this PC how to log in to GitHub, using the access token
REM  already sitting in git_keys.txt. No browser, no pop-up windows.
REM
REM  HOW IT WORKS (plain English):
REM  GitHub stopped accepting passwords for git in 2021. Instead you use an
REM  "access token" - a long random string that acts as the password. Git can
REM  remember it for you so you're never asked again. This script writes it
REM  into the file git looks in.
REM
REM  WHERE THE TOKEN ENDS UP:
REM      %USERPROFILE%\.git-credentials
REM  It is stored as PLAIN TEXT, unscrambled. That's the trade-off you chose:
REM  simple and always works, but anyone who can read that file has your
REM  GitHub account. Fine on a PC only you use.
REM
REM  Created 2026-08-12.
REM ============================================================================

cd /d "%~dp0"
title One-time GitHub login setup
cls
echo.
echo   ============================================
echo     One-time GitHub login setup
echo   ============================================
echo.

REM ---------------------------------------------------------------------------
REM  Step 1 - find the token
REM ---------------------------------------------------------------------------
if not exist "git_keys.txt" (
    echo   [X] Can't find git_keys.txt in this folder.
    echo       That's the file holding your GitHub access token.
    echo.
    pause
    exit /b 1
)

set "TOKEN="
for /f "usebackq tokens=* delims=" %%T in (`findstr /b /c:"github_pat_" "git_keys.txt"`) do (
    if not defined TOKEN set "TOKEN=%%T"
)
if not defined TOKEN (
    for /f "usebackq tokens=* delims=" %%T in (`findstr /b /c:"ghp_" "git_keys.txt"`) do (
        if not defined TOKEN set "TOKEN=%%T"
    )
)

if not defined TOKEN (
    echo   [X] No GitHub token found inside git_keys.txt.
    echo       A token starts with  github_pat_  or  ghp_
    echo.
    echo       Make a new one at:
    echo         https://github.com/settings/personal-access-tokens
    echo       Give it Contents = Read and write on the OhbotPi repository,
    echo       then paste it on its own line at the top of git_keys.txt.
    echo.
    pause
    exit /b 1
)

REM  trim any stray trailing space
for /l %%N in (1,1,4) do if "!TOKEN:~-1!"==" " set "TOKEN=!TOKEN:~0,-1!"

set "MASKED=!TOKEN:~0,14!..........!TOKEN:~-4!"
echo   [ok] Found a token in git_keys.txt  ^(!MASKED!^)

REM ---------------------------------------------------------------------------
REM  Step 2 - clear out any half-configured login from before, so the old
REM  settings can't fight with the new ones.
REM ---------------------------------------------------------------------------
git config --global --unset-all credential.helper >nul 2>&1
git config --global credential.helper store
echo   [ok] Told git to remember logins

REM ---------------------------------------------------------------------------
REM  Step 3 - make sure this folder is trusted (the "dubious ownership" fix)
REM ---------------------------------------------------------------------------
git config --global --add safe.directory "%CD:\=/%" >nul 2>&1
echo   [ok] This folder is trusted

REM ---------------------------------------------------------------------------
REM  Step 4 - write the login file git reads
REM ---------------------------------------------------------------------------
>"%USERPROFILE%\.git-credentials" echo https://boquetebots:!TOKEN!@github.com
echo   [ok] Saved your login to %USERPROFILE%\.git-credentials

REM ---------------------------------------------------------------------------
REM  Step 5 - actually test it against GitHub
REM ---------------------------------------------------------------------------
echo.
echo   ... testing the connection to GitHub
echo.
git ls-remote --heads origin >nul 2>&1
if errorlevel 1 (
    echo   ############################################
    echo     The token did NOT work
    echo   ############################################
    echo.
    echo   Most likely it has expired - GitHub tokens do, and yours is
    echo   from around June 19th.
    echo.
    echo   Make a fresh one here:
    echo     https://github.com/settings/personal-access-tokens
    echo.
    echo   Settings to choose:
    echo     Resource owner ........ boquetebots
    echo     Repository access ..... Only select repositories  -^>  OhbotPi
    echo     Permissions ........... Contents = Read and write
    echo.
    echo   Then replace the old token on the first line of git_keys.txt
    echo   with the new one, and run this script again.
    echo.
    pause
    exit /b 1
)

echo   ============================================
echo     Success - GitHub login is working
echo   ============================================
echo.
echo   You won't be asked for a password again.
echo.
echo   Next: double-click  push-to-github.bat  to send your work.
echo.
pause
exit /b 0
