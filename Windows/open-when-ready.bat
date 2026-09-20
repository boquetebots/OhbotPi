@echo off
REM ===========================================================================
REM  open-when-ready.bat  -  open a page once the server is actually up
REM ===========================================================================
REM
REM  Usage:   open-when-ready.bat  PORT  URL
REM
REM  Called by yobot-launcher.bat and yobot-show.bat. Fine to run by hand for
REM  testing - it will tell you what it is doing.
REM
REM  WHY THIS EXISTS
REM  ---------------
REM  yobot-launcher.bat used to do this:
REM
REM      start "" http://localhost:5000
REM      "%PY%" launcher_server.py
REM
REM  The browser was opened BEFORE the server was started. Not a race it
REM  usually lost - one it could never win. The page said it could not reach
REM  the site, a refresh a second later worked, and it read as "the pages are
REM  slow" rather than as a bug. Same on the Pi.
REM
REM  yobot-show.bat waited a fixed 4 seconds instead. Better, but a guess. A
REM  USB stick measured on 2026-09-20 had a MAXIMUM read latency of 2.1
REM  seconds - a single stall can eat half a fixed budget before Python has
REM  done anything. Any fixed number is too short somewhere.
REM
REM  So: ask the port. Poll until something accepts a connection, then open
REM  the browser.
REM
REM  WHY IT TALKS
REM  ------------
REM  The first version printed nothing at all. When it failed to open a
REM  browser on 2026-09-20 there was no way to tell whether it had run, what
REM  arguments it got, or whether the wait had succeeded - the same mistake as
REM  a log that only exists on screen. It is chatty now, on purpose.
REM ===========================================================================

setlocal

set "PORT=%~1"
set "URL=%~2"

if "%PORT%"=="" goto BADARGS
if "%URL%"==""  goto BADARGS

REM  The wait is done in PowerShell rather than a cmd loop. A cmd loop wants
REM  "netstat | findstr" inside a FOR block, and a pipe inside a parenthesised
REM  block in cmd is a good way to get a subtly wrong answer. Opening a TCP
REM  connection is also the question we actually mean: not "is this port
REM  mentioned somewhere" but "will it accept a connection".
REM
REM  120 tries, half a second apart - one minute, which is generous even for a
REM  slow stick.
echo   Waiting for Yobot to be ready...

powershell -NoProfile -ExecutionPolicy Bypass -Command "for($i=0;$i -lt 120;$i++){try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',%PORT%);$c.Close();Write-Host ('  Ready after ' + ($i*0.5) + ' seconds. Opening your browser.');exit 0}catch{Start-Sleep -Milliseconds 500}};Write-Host '';exit 1"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo   Yobot did not answer within a minute - opening the browser anyway.
    echo   If the page shows an error, give it a moment and refresh.
)

start "" "%URL%"
if errorlevel 1 echo   [X] Windows would not open a browser. Go to %URL% yourself.

endlocal
exit /b 0

:BADARGS
echo.
echo   open-when-ready.bat needs a port and a URL, like this:
echo.
echo       open-when-ready.bat 5000 "http://localhost:5000"
echo.
echo   It is normally called by yobot-launcher.bat or yobot-show.bat, so if
echo   you are seeing this from one of those, something is wrong with how it
echo   was called rather than with this file.
echo.
endlocal
exit /b 2
