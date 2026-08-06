param(
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDir = Join-Path $repoRoot "reports"
$startLog = Join-Path $logDir "web-start.out.log"
$errorLog = Join-Path $logDir "web-start.err.log"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Write-StartupLog {
    param([string]$Message)
    Add-Content -Path $startLog -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

function Write-StartupError {
    param([string]$Message)
    Add-Content -Path $errorLog -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

$python = Get-Command python -ErrorAction SilentlyContinue

try {
    if ($python) {
        $pythonExe = $python.Source
    } else {
        $bundledPython = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        if (-not (Test-Path -LiteralPath $bundledPython)) {
            throw "Python not found. Install Python 3.10+ or add it to PATH."
        }
        $pythonExe = $bundledPython
    }

    Write-StartupLog "Starting web server. repoRoot=$repoRoot python=$pythonExe port=$Port reload=$Reload"
    Push-Location $repoRoot
    $uvicornArgs = @("web/backend/run_server.py", "--host", "127.0.0.1", "--port", "$Port")
    if ($Reload) {
        $uvicornArgs += "--reload"
    }
    & $pythonExe @uvicornArgs
    Write-StartupError "uvicorn exited with code $LASTEXITCODE"
} catch {
    Write-StartupError $_.Exception.ToString()
    throw
} finally {
    try {
        Pop-Location
    } catch {
    }
}
