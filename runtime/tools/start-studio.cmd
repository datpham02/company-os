@echo off
rem Start the Game Studio on the studio machine (runtime-management.md):
rem   1. Paperclip, from %USERPROFILE%\game-studio-workspace (global install, not npx; OQ-034)
rem   2. the review-wake watchdog (OQ-035)
rem   3. the Paperclip UI in the default browser
rem Each process gets its own window; close a window (or press Ctrl+C in it) to stop that process.
rem Safe to run twice: anything already running is left alone.
setlocal

for %%I in ("%~dp0..\..") do set "REPO=%%~fI"
set "WORKSPACE=%USERPROFILE%\game-studio-workspace"
set "HEALTH=http://127.0.0.1:3100/api/health"
if not exist "%WORKSPACE%" mkdir "%WORKSPACE%"

rem Find paperclipai. It is a global npm package, so it lives with one Node version. With nvm-windows the
rem active Node can change (nvm use), which hides paperclipai from PATH. Order: PAPERCLIP_NODE_DIR if set,
rem then PATH, then the newest nvm Node folder that has paperclipai.cmd. The folder found is put first on
rem PATH for the windows started below, so Paperclip runs on the Node it was installed with.
set "PAPERCLIP_DIR="
if not defined NVM_HOME set "NVM_HOME=%LOCALAPPDATA%\nvm"
if defined PAPERCLIP_NODE_DIR if exist "%PAPERCLIP_NODE_DIR%\paperclipai.cmd" set "PAPERCLIP_DIR=%PAPERCLIP_NODE_DIR%"
if not defined PAPERCLIP_DIR (
  where paperclipai >nul 2>nul
  if not errorlevel 1 set "PAPERCLIP_DIR=PATH"
)
if not defined PAPERCLIP_DIR (
  for /f "delims=" %%D in ('dir /b /ad /on "%NVM_HOME%\v*" 2^>nul') do (
    if exist "%NVM_HOME%\%%D\paperclipai.cmd" set "PAPERCLIP_DIR=%NVM_HOME%\%%D"
  )
)
if not defined PAPERCLIP_DIR (
  echo paperclipai was not found on PATH or in any nvm Node folder. Set PAPERCLIP_NODE_DIR to the folder that holds paperclipai.cmd.
  pause
  exit /b 1
)
if /i "%PAPERCLIP_DIR%"=="PATH" (
  echo Using paperclipai from PATH.
) else (
  echo Using paperclipai from %PAPERCLIP_DIR%
  set "PATH=%PAPERCLIP_DIR%;%PATH%"
)

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing '%HEALTH%' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 (
  echo Paperclip is already running.
) else (
  start "Game Studio - Paperclip" /D "%WORKSPACE%" cmd /k paperclipai run
  echo Waiting for Paperclip to start...
  powershell -NoProfile -Command "$end = (Get-Date).AddMinutes(3); while ((Get-Date) -lt $end) { try { Invoke-WebRequest -UseBasicParsing '%HEALTH%' -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Seconds 2 } }; exit 1"
  if errorlevel 1 (
    echo Paperclip did not answer within 3 minutes. Check the "Game Studio - Paperclip" window.
    pause
    exit /b 1
  )
)

rem Window titles are unreliable under Windows Terminal, so look for the node process itself.
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $_.CommandLine -like '*review-wake-watchdog*' }) { exit 0 } else { exit 1 }"
if not errorlevel 1 (
  echo The review watchdog is already running.
) else (
  start "Game Studio - review watchdog" /D "%REPO%" cmd /k node runtime\tools\review-wake-watchdog.ts
)

start "" http://localhost:3100
echo Game Studio is up: Paperclip at http://localhost:3100
rem Keep this window readable for a few seconds (ping works without a keyboard, unlike timeout).
ping -n 6 127.0.0.1 >nul
