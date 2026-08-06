param(
    [string]$Version = "latest",
    [string]$InstallDir = "tools/allure"
)

$ErrorActionPreference = "Stop"
$env:ALLURE_NO_ANALYTICS = "1"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$targetPath = Join-Path $repoRoot $InstallDir
$targetFullPath = [System.IO.Path]::GetFullPath($targetPath)
$toolsRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "tools"))

if (-not $targetFullPath.StartsWith($toolsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "InstallDir must resolve under $toolsRoot"
}

if ($Version -eq "latest") {
    $metadataUrl = "https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/maven-metadata.xml"
    [xml]$metadata = Invoke-RestMethod -Uri $metadataUrl
    $Version = $metadata.metadata.versioning.release
}

$downloadUrl = "https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/$Version/allure-commandline-$Version.zip"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) "openapi-allure-$([System.Guid]::NewGuid())"
$zipPath = Join-Path $tmpRoot "allure-commandline.zip"
$extractPath = Join-Path $tmpRoot "extract"

New-Item -ItemType Directory -Path $tmpRoot, $extractPath -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $targetFullPath -Parent) -Force | Out-Null

Write-Host "Downloading Allure CLI $Version..."
Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $zipPath

Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force
$extractedAllure = Get-ChildItem -LiteralPath $extractPath -Directory |
    Where-Object { $_.Name -like "allure-*" } |
    Select-Object -First 1

if (-not $extractedAllure) {
    throw "Could not find extracted Allure directory."
}

if (Test-Path -LiteralPath $targetFullPath) {
    Remove-Item -LiteralPath $targetFullPath -Recurse -Force
}

Move-Item -LiteralPath $extractedAllure.FullName -Destination $targetFullPath
Remove-Item -LiteralPath $tmpRoot -Recurse -Force

$allureCmd = Join-Path $targetFullPath "bin/allure.bat"
Write-Host "Allure CLI installed: $allureCmd"
& $allureCmd --version
