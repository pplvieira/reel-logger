# Pull the phone queue and ingest the newest JSONL into the local API.
# Requires scripts/local.device.json (copy from local.device.json.example).
param(
    [string]$ConfigPath = "",
    [string]$Serial = "",
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $ConfigPath) {
    $ConfigPath = Join-Path $PSScriptRoot "local.device.json"
}
if (-not (Test-Path $ConfigPath)) {
    Write-Error @"
Missing $ConfigPath
Copy the example and fill in IDs from register_device.py:
  copy scripts\local.device.json.example scripts\local.device.json
"@
}

$config = Get-Content -Raw -Encoding utf8 $ConfigPath | ConvertFrom-Json
foreach ($key in @("base_url", "user_id", "device_id")) {
    if (-not $config.$key) { Write-Error "local.device.json missing '$key'" }
}

Write-Host "API: $($config.base_url)"
Write-Host "user_id: $($config.user_id)"
Write-Host "device_id: $($config.device_id)"

# Health check
try {
    $health = Invoke-RestMethod -Uri ($config.base_url.TrimEnd("/") + "/health") -TimeoutSec 3
    Write-Host "health: $($health.status)"
} catch {
    Write-Error "API not reachable at $($config.base_url). Start it with:`n  uvicorn app.main:app --reload"
}

if (-not $SkipPull) {
    & (Join-Path $PSScriptRoot "pull-queue.ps1") -Serial $Serial
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$queueDir = Join-Path $root "data\phone-queue"
$latest = Get-ChildItem (Join-Path $queueDir "events-*.jsonl") -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $latest -or $latest.Length -eq 0) {
    Write-Error "No non-empty queue file in data\phone-queue. Scroll with Logging on, then retry."
}

Write-Host "Ingesting $($latest.Name) ($($latest.Length) bytes)..."
$pyArgs = @(
    "scripts\ingest_queue.py",
    $latest.FullName,
    "--base-url", $config.base_url,
    "--user-id", $config.user_id,
    "--device-id", $config.device_id
)
if ($config.api_token) {
    $pyArgs += @("--token", $config.api_token)
}
& python @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$sessions = Invoke-RestMethod -Uri ($config.base_url.TrimEnd("/") + "/sessions?user_id=$($config.user_id)")
$impressions = Invoke-RestMethod -Uri ($config.base_url.TrimEnd("/") + "/impressions?user_id=$($config.user_id)")
Write-Host "Done. sessions=$($sessions.Count) impressions=$($impressions.Count)"
Write-Host "Docs: $($config.base_url.TrimEnd('/'))/docs"
