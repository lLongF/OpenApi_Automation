param(
    [string]$Marker = "",
    [string]$EnvName = $env:TEST_ENV,
    [switch]$Live
)

$ErrorActionPreference = "Stop"
$env:ALLURE_NO_ANALYTICS = "1"

if (-not $EnvName) {
    $EnvName = "dev"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Get-Command python -ErrorAction SilentlyContinue

if ($python) {
    $pythonExe = $python.Source
} else {
    $bundledPython = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (-not (Test-Path -LiteralPath $bundledPython)) {
        throw "Python not found. Install Python 3.10+ or add it to PATH."
    }
    $pythonExe = $bundledPython
}

New-Item -ItemType Directory -Path (Join-Path $repoRoot "reports/allure-results") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $repoRoot "reports/allure-report") -Force | Out-Null

$pytestArgs = @("-m", "pytest", "--env", $EnvName, "--clean-alluredir")

if ($Live) {
    $pytestArgs += "--live"
}

if ($Marker) {
    $pytestArgs += @("-m", $Marker)
}

Push-Location $repoRoot
try {
    & $pythonExe @pytestArgs
    powershell -ExecutionPolicy Bypass -File "scripts/generate_allure_report.ps1"
    Write-Host "Pytest HTML report: file:///$((Join-Path $repoRoot "reports/report.html") -replace '\\','/')"
} finally {
    Pop-Location
}
