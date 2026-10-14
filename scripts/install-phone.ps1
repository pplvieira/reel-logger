# Android-only. Reinstalls the debug APK on a connected device.
param(
    [string]$Serial = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
. (Join-Path $PSScriptRoot "Resolve-Adb.ps1")
$adbExe = Resolve-Adb
Write-Host "Using adb: $adbExe"

$androidDir = Join-Path $root "android"
if (-not (Test-Path $androidDir)) {
    Write-Error "Android module missing at ./android"
}

$ksPropsExample = Join-Path $androidDir "keystore.properties.example"
$ksProps = Join-Path $androidDir "keystore.properties"
if (-not (Test-Path $ksProps) -and (Test-Path $ksPropsExample)) {
    Copy-Item $ksPropsExample $ksProps
    Write-Host "Created android/keystore.properties from example"
}

$keystore = Join-Path $androidDir "debug.keystore"
if (-not (Test-Path $keystore)) {
    Write-Host "Generating debug.keystore..."
    & (Join-Path $PSScriptRoot "generate-debug-keystore.ps1")
}

$serial = Resolve-AdbSerial -AdbExe $adbExe -Serial $Serial
Write-Host "Using device: $serial"
& $adbExe -s $serial devices

Set-Location $androidDir
$env:ANDROID_SERIAL = $serial

. (Join-Path $PSScriptRoot "Resolve-JavaHome.ps1")
$env:JAVA_HOME = Resolve-JavaHome
Write-Host "JAVA_HOME=$env:JAVA_HOME"

if (Test-Path ".\gradlew.bat") {
    .\gradlew.bat installDebug
} else {
    Write-Error "gradlew.bat missing. Open ./android in Android Studio once to sync Gradle."
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installed dk.sdu.scrolllogger debug build."
Write-Host "Confirm Accessibility is enabled for Scroll logger (Instagram)."
