@echo off
rem ============================================================
rem  Daily Steam data update (called by Windows Task Scheduler)
rem  Task name: SteamMarketCrawlerDaily, every day at 22:00
rem  Steps: cd to project -> write timestamp -> run crawler -> append log
rem  Exit code: 0 = success, non-zero = failed (old data is kept)
rem  Keep this file ASCII-only: cmd.exe breaks on UTF-8 + chcp.
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
"%NODE_EXE%" scripts\crawler.js >> "%LOG_FILE%" 2>&1
set "CODE=%errorlevel%"

if not "%CODE%"=="0" (
  echo ===== [%date% %time%] update FAILED, exit code %CODE%, previous data kept =====>> "%LOG_FILE%"
) else (
  echo ===== [%date% %time%] update OK =====>> "%LOG_FILE%"
)

exit /b %CODE%
