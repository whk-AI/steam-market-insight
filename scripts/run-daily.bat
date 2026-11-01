@echo off
rem ============================================================
rem  Daily Steam data update (called by Windows Task Scheduler)
rem  Task name: SteamMarketCrawlerDaily, every day at 22:00
rem  Steps: cd -> ensure proxy -> run crawler
rem  Exit code: 0 = success, non-zero = failed (old data is kept)
rem  Keep this file ASCII-only: cmd.exe breaks on UTF-8 + chcp.
rem
rem  Why the proxy step:
rem    On some networks store.steampowered.com is unreachable directly
rem    (TCP connect timeout) while api.steampowered.com still works.
rem    If a local mihomo/Clash Verge proxy is configured, the job starts
rem    it headless on 127.0.0.1:7897 and routes Node fetch through it.
rem    Everything degrades to a direct connection when no proxy exists.
rem ============================================================
setlocal

set "PROJECT_DIR=F:\steam-market-insight"
set "LOG_FILE=%PROJECT_DIR%\data\crawler.log"

cd /d "%PROJECT_DIR%" 2>nul
if errorlevel 1 (
  echo [%date% %time%] cannot enter %PROJECT_DIR%
  exit /b 1
)

rem Task Scheduler has a minimal PATH: prefer the real node.exe over any shim
set "NODE_EXE=%PROGRAMFILES%\nodejs\node.exe"
if not exist "%NODE_EXE%" set "NODE_EXE=node"

echo.>> "%LOG_FILE%"
echo ===== [%date% %time%] daily update start =====>> "%LOG_FILE%"

rem ---- step 1: make sure a local proxy is available (optional) ----
set "PROXY_READY=0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%\scripts\start-proxy.ps1" >> "%LOG_FILE%" 2>&1
if not errorlevel 1 set "PROXY_READY=1"

if "%PROXY_READY%"=="1" (
  set "NODE_USE_ENV_PROXY=1"
  set "HTTPS_PROXY=http://127.0.0.1:7897"
  set "HTTP_PROXY=http://127.0.0.1:7897"
  echo proxy: 127.0.0.1:7897>> "%LOG_FILE%"
) else (
  echo proxy: none, direct connection>> "%LOG_FILE%"
)

rem ---- step 2: crawl and write data/games.json + meta.json + online.json ----
"%NODE_EXE%" scripts\crawler.js >> "%LOG_FILE%" 2>&1
set "CODE=%errorlevel%"

if not "%CODE%"=="0" (
  echo ===== [%date% %time%] update FAILED, exit code %CODE%, previous data kept =====>> "%LOG_FILE%"
  goto :cleanup
)

echo ===== [%date% %time%] update OK =====>> "%LOG_FILE%"

:cleanup
if "%PROXY_READY%"=="1" (
  "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%\scripts\stop-proxy.ps1" >> "%LOG_FILE%" 2>&1
)

exit /b %CODE%
