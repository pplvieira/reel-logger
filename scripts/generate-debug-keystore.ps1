# Generates android/debug.keystore with the standard Android debug identity.
# Requires keytool on PATH (JDK or Android Studio JBR).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$android = Join-Path $root "android"
$store = Join-Path $android "debug.keystore"

$keytool = Get-Command keytool -ErrorAction SilentlyContinue
if (-not $keytool) {
    $candidates = @(
        "$env:ProgramFiles\Android\Android Studio\jbr\bin\keytool.exe",
        "$env:LOCALAPPDATA\Programs\Android\Android Studio\jbr\bin\keytool.exe",
        "$env:JAVA_HOME\bin\keytool.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $keytool = $c; break }
    }
}
if (-not $keytool) {
    Write-Error "keytool not found. Install a JDK or Android Studio, then re-run."
}

if (Test-Path $store) {
    Write-Host "Already exists: $store"
    exit 0
}

& $keytool -genkeypair -v `
    -keystore $store `
    -storepass android `
    -alias androiddebugkey `
    -keypass android `
    -keyalg RSA `
    -keysize 2048 `
    -validity 10000 `
    -dname "CN=Android Debug,O=Android,C=US"

Write-Host "Wrote $store"
