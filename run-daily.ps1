$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$logDirectory = Join-Path $env:LOCALAPPDATA 'DailyBuilds'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$logPath = Join-Path $logDirectory ((Get-Date -Format 'yyyy-MM-dd') + '.log')
& 'C:/Users/Mudit/AppData/Local/Programs/Python/Python310/python.exe' -u (Join-Path $PSScriptRoot 'daily_builds.py') --write *>> $logPath
if ($LASTEXITCODE -ne 0) { throw "Daily Builds failed. See $logPath" }
