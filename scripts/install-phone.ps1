# Android-only. Reinstalls the debug APK on a connected device.
# The Android module is not in this repo yet; this script is the update path once it exists.
param(
    [string]$Serial = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$androidDir = Join-Path $root "android"
if (-not (Test-Path $androidDir)) {
    Write-Host "Android module not present yet (expected ./android)."
    Write-Host "After the Kotlin logger is added, this script will run: gradlew installDebug"
    exit 1
}

$adbArgs = @()
if ($Serial) {
    $adbArgs += @("-s", $Serial)
}

$devices = & adb @adbArgs devices
Write-Host $devices

Set-Location $androidDir
if ($Serial) {
    $env:ANDROID_SERIAL = $Serial
}
.\gradlew.bat installDebug
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "Installed debug build. Confirm Accessibility is still enabled for the logger."
