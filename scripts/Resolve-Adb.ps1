# Resolves adb.exe from PATH, ANDROID_HOME, or Android Studio SDK.
function Resolve-Adb {
    $cmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"),
        (Join-Path $env:USERPROFILE "AppData\Local\Android\Sdk\platform-tools\adb.exe")
    )
    if ($env:ANDROID_HOME) {
        $candidates += (Join-Path $env:ANDROID_HOME "platform-tools\adb.exe")
    }
    if ($env:ANDROID_SDK_ROOT) {
        $candidates += (Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe")
    }

    $root = Split-Path -Parent $PSScriptRoot
    $lp = Join-Path $root "android\local.properties"
    if (Test-Path $lp) {
        foreach ($line in Get-Content $lp) {
            if ($line -match '^\s*sdk\.dir=(.+)$') {
                $raw = $Matches[1].Trim()
                $sdk = $raw -replace '\\\\', '\' -replace '\\:', ':'
                $candidates += (Join-Path $sdk "platform-tools\adb.exe")
            }
        }
    }

    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }

    throw "adb not found. Install Android SDK platform-tools, or add this to PATH:`n  $env:LOCALAPPDATA\Android\Sdk\platform-tools"
}

function Resolve-AdbSerial {
    param(
        [Parameter(Mandatory = $true)][string]$AdbExe,
        [string]$Serial = ""
    )

    if ($Serial) { return $Serial }

    $lines = & $AdbExe devices | Select-Object -Skip 1 | Where-Object { $_ -match "\S+\s+device$" }
    $serials = @()
    foreach ($line in $lines) {
        if ($line -match "^(\S+)\s+device") { $serials += $Matches[1] }
    }

    if ($serials.Count -eq 0) {
        throw "No phone listed as 'device'. Connect USB or Wireless debugging, then: adb devices"
    }

    if ($serials.Count -eq 1) { return $serials[0] }

    # Same phone often appears twice (IP:port + adb-tls mDNS). Prefer numeric IP:port.
    $ip = $serials | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+:\d+$' } | Select-Object -First 1
    if ($ip) {
        Write-Host "Multiple adb connections; using $ip"
        return $ip
    }

    Write-Host "Multiple devices: $($serials -join ', ')"
    Write-Host "Using first: $($serials[0]) (pass -Serial to pick another)"
    return $serials[0]
}
