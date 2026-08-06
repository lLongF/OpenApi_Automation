param(
    [string]$ResultsDir = "reports/allure-results",
    [string]$ReportDir = "reports/allure-report"
)

$ErrorActionPreference = "Stop"
$env:ALLURE_NO_ANALYTICS = "1"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$localAllure = Join-Path $repoRoot "tools/allure/bin/allure.bat"

if (Test-Path -LiteralPath $localAllure) {
    $allure = $localAllure
} else {
    $allureCommand = Get-Command allure -ErrorAction SilentlyContinue
    if (-not $allureCommand) {
        throw "Allure CLI not found. Run: powershell -ExecutionPolicy Bypass -File scripts/install_allure.ps1"
    }
    $allure = $allureCommand.Source
}

$resultsPath = Join-Path $repoRoot $ResultsDir
$reportPath = Join-Path $repoRoot $ReportDir

& $allure generate $resultsPath -o $reportPath --clean
Write-Host "Allure report: file:///$($reportPath -replace '\\','/')/index.html"
