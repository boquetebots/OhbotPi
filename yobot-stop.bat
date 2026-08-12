@echo off
REM ===========================================================================
REM  yobot-stop.bat  —  stop everything Yobot, no matter how it was started
REM ===========================================================================
REM  Run it from D:\Projects\OhbotPi2 with:   .\yobot-stop.bat
REM
REM  Use this when:
REM    - you've lost the window something was running in
REM    - Ctrl-C isn't working
REM    - you get "address already in use" when starting a server
REM    - you just want a clean slate before handing Yobot back to the Pi
REM
REM  It stops anything listening on Yobot's four ports (5000 launcher,
REM  5001 Sequence Builder/Timeline, 5002 brain server, 5003 calibration),
REM  then any python still running one of Yobot's programs.
REM
REM  Safe to run when nothing is going — it just tells you so.
REM ===========================================================================

setlocal enabledelayedexpansion
echo.
echo Stopping Yobot programs...
echo.

set FOUND=0

for %%P in (5000 5001 5002 5003) do (
    for /f "tokens=5" %%A in ('netstat -aon ^| findstr ":%%P " ^| findstr "LISTENING"') do (
        echo   port %%P - stopping process %%A
        taskkill /PID %%A /T /F >nul 2>&1
        set FOUND=1
    )
)

if "%FOUND%"=="0" (
    echo   nothing was listening on Yobot's ports
)

REM The conversation bot has no port of its own, so it has to be found by
REM the script name on its command line instead.
echo.
echo Checking for the conversation bot...
powershell -NoProfile -NonInteractive -Command "$names = 'ohbot_chat.py','ohbotchat_server.py','gui_server.py','calibration_server.py','launcher_server.py','yobot_win.py'; $hits = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine }; $any = $false; foreach ($p in $hits) { foreach ($n in $names) { if ($p.CommandLine -like ('*' + $n + '*')) { Write-Host ('   stopping ' + $n + ' (process ' + $p.ProcessId + ')'); Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; $any = $true; break } } }; if (-not $any) { Write-Host '   none running' }"

echo.
echo Done. Start the Launcher again with:  .\yobot-launcher.bat
echo.
endlocal
