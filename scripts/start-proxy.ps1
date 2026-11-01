# Ensure a local HTTP proxy (Clash Verge / mihomo core) listens on 127.0.0.1:7897.
# Exit 0  -> proxy ready (started by us or already running)
# Exit 1  -> no proxy available, caller should fall back to direct connection
# The core binary path is derived at runtime from the clash_verge_service entry,
# so no non-ASCII path literal is needed here.
$ErrorActionPreference = 'SilentlyContinue'
$port = 7897
$pidFile = Join-Path $PSScriptRoot '..\data\.proxy.pid'

function Test-Listen([int]$p) {
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $iar = $client.BeginConnect('127.0.0.1', $p, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne(500)) { return $false }
    $client.EndConnect($iar)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

if (Test-Listen $port) {
  Write-Output "proxy already listening on 127.0.0.1:$port"
  exit 0
}

$svc = Get-CimInstance Win32_Service -Filter "Name='clash_verge_service'"
if (-not $svc) {
  Write-Output 'clash_verge_service not found, skip proxy'
  exit 1
}

$serviceExe = $svc.PathName.Trim('"')
$resourcesDir = Split-Path $serviceExe -Parent
$installDir = Split-Path $resourcesDir -Parent
$coreExe = Join-Path $installDir 'verge-mihomo.exe'
$cfgDir = Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
$cfgFile = Join-Path $cfgDir 'clash-verge.yaml'

if (-not (Test-Path $coreExe) -or -not (Test-Path $cfgFile)) {
  Write-Output "proxy core or config missing: $coreExe / $cfgFile"
  exit 1
}

$proc = Start-Process -FilePath $coreExe -ArgumentList @('-d', $cfgDir, '-f', $cfgFile) -WindowStyle Hidden -PassThru
Set-Content -Path $pidFile -Value $proc.Id -Encoding ASCII

for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 500
  if (Test-Listen $port) {
    Write-Output "started mihomo pid $($proc.Id), proxy 127.0.0.1:$port ready"
    exit 0
  }
}

Stop-Process -Id $proc.Id -Force
Remove-Item $pidFile -Force
Write-Output 'mihomo started but port 7897 never became ready'
exit 1
