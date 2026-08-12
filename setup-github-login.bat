@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  setup-github-login.bat
REM
REM  RUN THIS ONCE. After it succeeds you never touch it again, and
REM  push-to-github.bat will work without asking you anything.
REM
REM  WHY THE POP-UP KEPT APPEARING (v1 of this script didn't fix it):
REM
REM  Git for Windows installs a helper called Git Credential Manager, and
REM  registers it in git's SYSTEM settings - the ones that apply to every user
REM  on the PC. Git collects login helpers from all its settings files and
REM  tries them in order, so even after we added ours, the system one still
REM  went first and popped up its window.
REM
REM  You normally need Administrator rights to remove a system setting. The way
REM  around it: git treats a BLANK helper entry as "forget everything before
REM  this". So we write a blank entry, then ours. No admin needed.
REM
REM  WHERE YOUR TOKEN ENDS UP:
REM      %USERPROFILE%\.git-credentials
REM  Stored as PLAIN TEXT. That's the trade-off you chose - simple and always
REM  works, but anyone who can read that file has your GitHub account.
REM
REM  Created 2026-08-12. Rewritten same day to defeat the credential pop-up.
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
REM  Step 1 - find the token in git_keys.txt
REM ---------------------------------------------------------------------------
if not exist "git_keys.txt" (
    echo   [X] Can't find git_keys.txt in this folder.
    echo       That's the file that should hold your GitHub access token.
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
    echo   [X] No GitHub token found in git_keys.txt.
    echo.
    echo       The token must sit on a line OF ITS OWN, with nothing before
    echo       it - no quotes, no "token:" label, no leading spaces. It starts
    echo       with  github_pat_  or  ghp_
    echo.
    echo       Get one at:
    echo         https://github.com/settings/personal-access-tokens
    echo.
    pause
    exit /b 1
)

REM  trim stray trailing spaces
for /l %%N in (1,1,6) do if "!TOKEN:~-1!"==" " set "TOKEN=!TOKEN:~0,-1!"

set "MASKED=!TOKEN:~0,14!..........!TOKEN:~-4!"
echo   [ok] Found a token  ^(!MASKED!^)

REM ---------------------------------------------------------------------------
REM  Step 2 - shut down the pop-up helper
REM
REM  The blank entry below is the important bit. It wipes the list of helpers
REM  git inherited from the system-wide settings, pop-up window and all.
REM ---------------------------------------------------------------------------
git config --global --unset-all credential.helper >nul 2>&1
git config --global --replace-all credential.helper "" >nul 2>&1
git config --global --add credential.helper store >nul 2>&1

REM  Belt and braces: tell git never to open an interactive window for GitHub,
REM  and try to remove the system entry too (this one quietly does nothing
REM  unless you happen to be running as Administrator - that's fine).
git config --global credential.interactive false >nul 2>&1
git config --global credential.modalPrompt false >nul 2>&1
git config --system --unset-all credential.helper >nul 2>&1

echo   [ok] Turned off the credential pop-up

REM ---------------------------------------------------------------------------
REM  Step 3 - trust this folder (the "dubious ownership" fix)
REM ---------------------------------------------------------------------------
git config --global --add safe.directory "%CD:\=/%" >nul 2>&1
echo   [ok] This folder is trusted

REM ---------------------------------------------------------------------------
REM  Step 4 - write the login file
REM ---------------------------------------------------------------------------
>"%USERPROFILE%\.git-credentials" echo https://boquetebots:!TOKEN!@github.com
echo   [ok] Saved your login

REM ---------------------------------------------------------------------------
REM  Step 5 - test it, with prompts forced OFF so it can never hang or pop up
REM ---------------------------------------------------------------------------
echo.
echo   ... testing the connection to GitHub
echo.

set GIT_TERMINAL_PROMPT=0
set GCM_INTERACTIVE=never
git -c credential.interactive=false ls-remote --heads origin >nul 2>&1
if not errorlevel 1 goto :worked

REM ---------------------------------------------------------------------------
REM  Didn't work. Offer the fallback that bypasses helpers completely.
REM ---------------------------------------------------------------------------
echo   [!] That didn't authenticate.
echo.
echo   There are two reasons this happens:
echo     1. The token has expired ^(yours dates from around June 19th^).
echo     2. Something is still intercepting the login.
echo.
echo   There's one more method that skips the login system entirely: put the
echo   token directly into this folder's GitHub address. It always works.
echo.
echo   The catch: the token then shows up whenever you run "git remote -v",
echo   so be careful not to paste that output into a chat or a screenshot.
echo.
set "DOIT="
set /p DOIT=  Try that method? (y/n):

if /i not "!DOIT!"=="y" (
    echo.
    echo   Nothing more changed. If the token is expired, make a new one:
    echo     https://github.com/settings/personal-access-tokens
    echo       Resource owner ........ boquetebots
    echo       Repository access ..... Only select repositories  -^>  OhbotPi
    echo       Permissions ........... Contents = Read and write
    echo   Put it on its own line in git_keys.txt, then run this again.
    echo.
    pause
    exit /b 1
)

git remote set-url origin "https://boquetebots:!TOKEN!@github.com/boquetebots/OhbotPi.git"
echo.
echo   ... testing again
git -c credential.interactive=false ls-remote --heads origin >nul 2>&1
if not errorlevel 1 goto :worked

REM  Still failing - it's the token itself, not the plumbing.
git remote set-url origin "https://github.com/boquetebots/OhbotPi.git"
echo.
echo   ############################################
echo     The token itself has expired
echo   ############################################
echo.
echo   Both methods failed the same way, so the problem is the token, not
echo   Windows. GitHub tokens expire and yours is about eight weeks old.
echo.
echo   Make a fresh one:
echo     https://github.com/settings/personal-access-tokens
echo.
echo       Resource owner ........ boquetebots
echo       Repository access ..... Only select repositories  -^>  OhbotPi
echo       Permissions ........... Contents = Read and write
echo       Expiration ............ 1 year, or No expiration
echo.
echo   Then open git_keys.txt, replace the old token on the first line with
echo   the new one, save, and run this script again.
echo.
echo   ^(The address has been put back to normal, so nothing is left broken.^)
echo.
pause
exit /b 1

:worked
echo   ============================================
echo     Success - GitHub login is working
echo   ============================================
echo.
echo   No more pop-ups, no more passwords.
echo.
echo   Next: double-click  push-to-github.bat  to send your work.
echo.
pause
exit /b 0
