# Pull the on-device JSONL queue via adb.
param(
    [string]$Serial = "",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "Resolve-Adb.ps1")
$adbExe = Resolve-Adb
$serial = Resolve-AdbSerial -AdbExe $adbExe -Serial $Serial
Write-Host "Using device: $serial"

if (-not $OutDir) {
    $OutDir = Join-Path $root "data\phone-queue"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$adbArgs = @("-s", $serial)
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$local = Join-Path $OutDir "events-$stamp.jsonl"

$bytes = & $adbExe @adbArgs exec-out run-as dk.sdu.scrolllogger cat files/queue/events.jsonl
if ($LASTEXITCODE -ne 0) {
    Write-Host "exec-out failed; trying adb shell run-as..."
    $bytes = & $adbExe @adbArgs shell "run-as dk.sdu.scrolllogger cat files/queue/events.jsonl"
}

# adb may return string[] from PowerShell; normalize to text
$text = if ($null -eq $bytes) { "" }
    elseif ($bytes -is [byte[]]) { [System.Text.Encoding]::UTF8.GetString($bytes) }
    elseif ($bytes -is [System.Array]) { ($bytes | ForEach-Object { "$_" }) -join "`n" }
    else { [string]$bytes }

# Strip adb error noise
$clean = ($text -split "`n" | Where-Object {
    $_ -notmatch '^error:' -and $_ -notmatch '^adb\.exe:'
}) -join "`n"

if ([string]::IsNullOrWhiteSpace($clean)) {
    Write-Host "Queue file is empty or missing on the phone."
    Write-Host "In Scroll logger: Logging ON, Accessibility enabled, scroll Reels, check Queue lines > 0."
    Set-Content -Path $local -Value "" -Encoding utf8
    Write-Host "Wrote empty $local"
    exit 1
}

# Ensure trailing newline for JSONL
if (-not $clean.EndsWith("`n")) { $clean += "`n" }
[System.IO.File]::WriteAllText($local, $clean.Replace("`r`n", "`n"), [System.Text.UTF8Encoding]::new($false))

$lines = ($clean -split "`n" | Where-Object { $_.Trim().Length -gt 0 }).Count
Write-Host "Wrote $local ($lines events)"
Write-Host "Ingest with:"
Write-Host "  python scripts/ingest_queue.py `"$local`" --user-id <id> --device-id <id>"
