Param(
    [string]$OutputDirectory = "dist",
    [string]$ArchiveName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $ArchiveName -or [string]::IsNullOrWhiteSpace($ArchiveName)) {
    $ArchiveName = "django-maps-release-$timestamp.zip"
}

if (-not (Test-Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
}

$destination = Join-Path $OutputDirectory $ArchiveName

$excludeNames = @(
    ".git", "dist", "logs", "node_modules", "venv", ".venv",
    "__pycache__", "media", "oracleJdk-25"
)
$excludeExtensions = @(".pyc", ".pyo", ".log", ".sqlite3")

$items = Get-ChildItem -Force | Where-Object {
    $name = $_.Name
    ($excludeNames -notcontains $name) -and
    ($excludeExtensions -notcontains $_.Extension)
}

if (-not $items) {
    throw "No eligible files found for packaging."
}

Write-Host "Creating package at $destination ..."
Compress-Archive -Path $items.FullName -DestinationPath $destination -CompressionLevel Optimal -Force

Write-Host "Package created successfully:"
Write-Host "  $destination"
Write-Host ""
Write-Host "Reminder: Back up the database (mysqldump) and sensitive variables (.env, FERNET_KEY) separately."
