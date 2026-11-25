$ErrorActionPreference = 'Stop'
$config = Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml'
$logDir = Join-Path $PSScriptRoot '..\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stdout = Join-Path $logDir 'mihomo.out.log'
$stderr = Join-Path $logDir 'mihomo.err.log'
$exe = (Get-Item 'F:\*\*\verge-mihomo.exe' -ErrorAction Stop | Select-Object -First 1).FullName
if (-not (Test-Path $exe)) { throw "mihomo not found: $exe" }
if (-not (Test-Path $config)) { throw "config not found: $config" }
$root = Split-Path -Parent $exe
$dataDir = Split-Path -Parent $config
Start-Process -FilePath $exe -ArgumentList @('-d', $dataDir, '-f', $config) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Start-Sleep -Seconds 2
Get-Process verge-mihomo -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime | Format-List
