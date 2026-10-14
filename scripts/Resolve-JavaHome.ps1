# Prefer JDK 17 for Gradle/AGP. Android Studio's bundled jbr may be JDK 25, which breaks Kotlin.
function Resolve-JavaHome {
    $candidates = @()

    if ($env:SCROLL_LOGGER_JAVA_HOME -and (Test-Path $env:SCROLL_LOGGER_JAVA_HOME)) {
        $candidates += $env:SCROLL_LOGGER_JAVA_HOME
    }

    # JDKs downloaded via Android Studio / IntelliJ
    $jdks = Join-Path $env:USERPROFILE ".jdks"
    if (Test-Path $jdks) {
        $candidates += Get-ChildItem $jdks -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '17|jbr-17|temurin-17|ms-17|corretto-17' } |
            ForEach-Object { $_.FullName }
    }

    $studioRoots = @(
        "$env:ProgramFiles\Android\Android Studio",
        "$env:LOCALAPPDATA\Programs\Android\Android Studio"
    )
    foreach ($root in $studioRoots) {
        foreach ($rel in @("jbr-17", "jre", "jbr")) {
            $p = Join-Path $root $rel
            if (Test-Path (Join-Path $p "bin\java.exe")) { $candidates += $p }
        }
    }

    if ($env:JAVA_HOME -and (Test-Path "$env:JAVA_HOME\bin\java.exe")) {
        $candidates += $env:JAVA_HOME
    }

    foreach ($jdkHome in $candidates) {
        $java = Join-Path $jdkHome "bin\java.exe"
        if (-not (Test-Path $java)) { continue }
        # java -version writes to stderr; with $ErrorActionPreference=Stop that becomes a terminating error
        $verLine = (& cmd /c "`"$java`" -version 2>&1") | Out-String
        if ($verLine -match 'version "(1[7-9]|2[0-1])\.') {
            return $jdkHome
        }
    }

    throw @"
No JDK 17–21 found for Gradle.
Install one in Android Studio: Settings → Build Tools → Gradle → Gradle JDK → Download JDK → 17
Or set SCROLL_LOGGER_JAVA_HOME to a JDK 17 folder.
"@
}
