param(
    [string]$JavaHome = $env:JAVA_HOME,
    [string]$AndroidSdk = "$env:LOCALAPPDATA\Android\Sdk",
    [string]$FlutterRoot = '',
    [string]$ApiBaseUrl = 'http://127.0.0.1:8010',
    [switch]$BuildOnly
)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
if (!$FlutterRoot) { $FlutterRoot = Split-Path (Split-Path (Get-Command flutter).Source -Parent) -Parent }
if (!$JavaHome -or !(Test-Path "$JavaHome\bin\java.exe")) { throw 'Pass -JavaHome with a Java 17 or 21 JDK folder.' }
$env:JAVA_HOME=$JavaHome
$env:ANDROID_HOME=$AndroidSdk
$env:FLUTTER_ROOT=$FlutterRoot
$env:SLSL_FLUTTER_LAUNCHER=Join-Path $PSScriptRoot 'flutter-direct.cmd'
$dart=Join-Path $FlutterRoot 'bin\cache\dart-sdk\bin\dart.exe'
$snapshot=Join-Path $FlutterRoot 'bin\cache\flutter_tools.snapshot'
Push-Location (Join-Path $appRoot 'mobile')
try {
    & $dart "--packages=$FlutterRoot\packages\flutter_tools\.dart_tool\package_config.json" $snapshot pub get
    if ($LASTEXITCODE) { throw 'Flutter dependency resolution failed.' }
    $taskLocalProperties="sdk.dir=$($AndroidSdk.Replace('\','/'))`nflutter.sdk=$($FlutterRoot.Replace('\','/'))`nflutter.buildMode=debug`n"
    [IO.File]::WriteAllText((Join-Path $appRoot 'mobile\android\local.properties'),$taskLocalProperties,[Text.UTF8Encoding]::new($false))
    $taskApiDefine=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("API_BASE_URL=$ApiBaseUrl"))
    Push-Location android
    try {
        & .\gradlew.bat "-Dorg.gradle.java.home=$JavaHome" -I (Join-Path $PSScriptRoot 'flutter-launcher.gradle') "-Pdart-defines=$taskApiDefine" assembleDebug --console=plain
        if ($LASTEXITCODE) { throw 'Android build failed.' }
    } finally { Pop-Location }
    if (!$BuildOnly) {
        $adb=Join-Path $AndroidSdk 'platform-tools\adb.exe'
        & $adb install -r 'build\app\outputs\flutter-apk\app-debug.apk'
        if ($LASTEXITCODE) { throw 'Start an Android emulator or connect a phone first.' }
        # Device loopback reaches this PC through USB/ADB, without opening LAN ports.
        & $adb reverse tcp:8010 tcp:8010
        & $adb shell am start -n 'lk.slsl.slsl_connect/.MainActivity'
    }
} finally { Pop-Location }
