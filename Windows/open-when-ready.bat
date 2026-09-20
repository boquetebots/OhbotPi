@echo off
REM ===========================================================================
REM  open-when-ready.bat  -  open a page once the server is actually up
REM ===========================================================================
REM
REM  Usage:   open-when-ready.bat <port> <url>
REM
REM  Called by the other .bat files in this folder. Not something to run on
REM  its own.
REM
REM  WHY THIS EXISTS
REM  ---------------
REM  yobot-launcher.bat used to do this:
REM
REM      start "" http://localhost:5000
REM      "%PY%" launcher_server.py
REM
REM  The browser was opened BEFORE the server was started. Not a race it
REM  usually lost - a race it could never win. The page said it could not
REM  reach the site, and a refresh a second later worked, so it read as
REM  "the pages are slow" rather than as a bug. Reported on Windows and on
REM  the Pi, and present since the file was written.
REM
REM  yobot-show.bat waited a fixed 4 seconds instead. Better, but a guess:
REM  fine on a fast PC, not enough on a Pi or on the first run from a USB
REM  stick, where Python is loading several thousand small files off flash.
REM  Any fixed number is either too short somewhere or wasted everywhere.
REM
REM  So: ask the port. Poll until something is listening, then open the
REM  browser. Fast machines open almost instantly, slow ones take as long as
REM  they take, and nobody sees a "cannot reach this page".
REM
REM  Up to 60 seconds, then it opens the browser anyway - if the server is
REM  never coming up, an error page the person can see beats a browser that
REM  never appears and no explanation at all.
REM ===========================================================================

setlocal

set "PORT=%~1"
set "URL=%~2"

if "%PORT%"=="" (
    echo   [X] open-when-ready.bat needs a port and a URL.
    endlocal
    exit /b 2
)
if "%URL%"=="" (
    echo   [X] open-when-ready.bat needs a port and a URL.
    endlocal
    exit /b 2
)

REM  The wait itself is done in PowerShell rather than a cmd loop. A cmd loop
REM  wants "netstat | findstr" inside a FOR block, and a pipe inside a
REM  parenthesised block in cmd is a good way to get a subtly wrong answer.
REM  Opening a TCP connection is the question we actually mean to ask anyway:
REM  not "is a port mentioned in netstat" but "will this thing accept a
REM  connection".
REM
REM  120 tries, half a second apart.
powershell -NoProfile -ExecutionPolicy Bypass -Command "for($i=0;$i -lt 120;$i++){try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',%PORT%);$c.Close();exit 0}catch{Start-Sleep -Milliseconds 500}};exit 1"

if errorlevel 1 (
    REM  Never came up. Open anyway - the browser's own error is more use to
    REM  the person than silence, and a refresh will work if it starts late.
    start "" "%URL%"
    endlocal
    exit /b 1
)

start "" "%URL%"
endlocal
exit /b 0
