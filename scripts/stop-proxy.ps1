# Stop the mihomo core only when this project started it (pid recorded by start-proxy.ps1).
# A proxy that was already running before the job (started by the Clash Verge GUI) is left alone.
$ErrorActionPreference = 'SilentlyContinue'
$pidFile = Join-Path $PSScriptRoot '..\data\.proxy.pid'

if (-not (Test-Path $pidFile)) { exit 0 }

$savedId = (Get-Content -Path $pidFile -Raw).Trim()
if ($savedId -match '^\d+$') {
  $proc = Get-Process -Id ([int]$savedId)
  if ($proc -and $proc.ProcessName -match 'mihomo') {
    Stop-Process -Id ([int]$savedId) -Force
    Write-Output "stopped mihomo pid $savedId"
  }
}

Remove-Item -Path $pidFile -Force
exit 0
