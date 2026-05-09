param(
    [switch]$BuildApk,
    [switch]$BuildAab,
    [switch]$RunBotsDryRun
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$FlutterDir = Join-Path $Root "fullet_flutter"
$ScraperDir = Join-Path $Root "scraper"
$PubspecPath = Join-Path $FlutterDir "pubspec.yaml"

$PubspecVersionLine = Select-String -Path $PubspecPath -Pattern '^\s*version:\s*([0-9A-Za-z\.\-\+]+)\s*$' | Select-Object -First 1
if (-not $PubspecVersionLine -or $PubspecVersionLine.Matches.Count -eq 0) {
    throw "pubspec.yaml version is missing"
}

$PubspecVersion = $PubspecVersionLine.Matches[0].Groups[1].Value
$VersionParts = $PubspecVersion.Split("+")
if ($VersionParts.Count -ne 2 -or -not ($VersionParts[1] -match '^\d+$')) {
    throw "pubspec.yaml version must use semantic build format, for example 1.0.1+2"
}

$BuildName = $VersionParts[0]
$BuildNumber = $VersionParts[1]

function Invoke-Step {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Push-Location $Root
try {
    Invoke-Step "Backend health check" {
        Push-Location $ScraperDir
        try { python backend_health_check.py } finally { Pop-Location }
    }

    Invoke-Step "Backend operations report" {
        Push-Location $ScraperDir
        try { python ops_report.py } finally { Pop-Location }
    }

    Invoke-Step "Backend unit tests" {
        Push-Location $ScraperDir
        try { python -m unittest test_backend_utils test_aytemiz_bot } finally { Pop-Location }
    }

    if ($RunBotsDryRun) {
        Invoke-Step "Bot dry run" {
            Push-Location $ScraperDir
            try {
                $env:FULLET_DRY_RUN = "1"
                $env:FULLET_ALLOW_DB_WRITE = "0"
                python run_all_bots.py
            } finally {
                Remove-Item Env:\FULLET_DRY_RUN -ErrorAction SilentlyContinue
                Remove-Item Env:\FULLET_ALLOW_DB_WRITE -ErrorAction SilentlyContinue
                Pop-Location
            }
        }
    }

    Invoke-Step "Flutter analyze" {
        Push-Location $FlutterDir
        try { flutter analyze } finally { Pop-Location }
    }

    Invoke-Step "Flutter tests" {
        Push-Location $FlutterDir
        try { flutter test } finally { Pop-Location }
    }

    if ($BuildApk) {
        Invoke-Step "Flutter release APK" {
            Push-Location $FlutterDir
            try { flutter build apk --release --build-name $BuildName --build-number $BuildNumber } finally { Pop-Location }
        }
    }

    if ($BuildAab) {
        Invoke-Step "Flutter release App Bundle" {
            Push-Location $FlutterDir
            try { flutter build appbundle --release --build-name $BuildName --build-number $BuildNumber } finally { Pop-Location }
        }
    }

    Write-Host ""
    Write-Host "[OK] Fullet release check passed." -ForegroundColor Green
}
finally {
    Pop-Location
}
