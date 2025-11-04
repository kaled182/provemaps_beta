#!/usr/bin/env pwsh
# ============================================================================
# Run Tests - Execute pytest suite with MariaDB via Docker Compose
# ============================================================================
#
# This script runs the Django/pytest test suite using the MariaDB container
# defined in docker-compose.yml, mirroring the production stack.
#
# Usage:
#   .\scripts\run_tests.ps1                                # run all tests
#   .\scripts\run_tests.ps1 -Path tests/test_metrics.py    # specific tests
#   .\scripts\run_tests.ps1 -Coverage                      # enable coverage
# ==============================================================================

param(
    [string]$Path = "tests/",
    [switch]$Coverage = $false,
    [switch]$Verbose = $false,
    [switch]$KeepDb = $false
)

$ErrorActionPreference = "Stop"

Write-Host ""  # blank line for readability
Write-Host "[INFO] Running pytest against MariaDB (Docker Compose)..." -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

# Step 1 - Docker daemon
Write-Host "`n[STEP 1] Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running"
    }
    Write-Host "   [OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] Docker is not running" -ForegroundColor Red
    Write-Host "   Run: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

# Step 2 - Ensure Compose services are up
Write-Host "`n[STEP 2] Checking Docker Compose services..." -ForegroundColor Yellow
try {
    $servicesRaw = docker compose ps --services 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw $servicesRaw
    }
    $runningServices = $servicesRaw -split "`n" | Where-Object { $_ }
} catch {
    Write-Host "   [ERROR] Could not list services: $_" -ForegroundColor Red
    Write-Host "   Run: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

if ($runningServices -notcontains "db") {
    Write-Host "   [ERROR] Service 'db' is not running" -ForegroundColor Red
    Write-Host "   Run: docker compose up -d db" -ForegroundColor Yellow
    exit 1
}

if ($runningServices -notcontains "web") {
    Write-Host "   [ERROR] Service 'web' is not running" -ForegroundColor Red
    Write-Host "   Run: docker compose up -d web" -ForegroundColor Yellow
    exit 1
}

Write-Host "   [OK] Running services: $($runningServices -join ', ')" -ForegroundColor Green

# Step 3 - Build pytest command
$pytestCmd = "pytest $Path"

if ($Verbose) {
    $pytestCmd += " -vvs"
} else {
    $pytestCmd += " -v"
}

if ($Coverage) {
    $pytestCmd += " --cov=core --cov=maps_view --cov=routes_builder --cov=inventory"
    $pytestCmd += " --cov-report=term-missing --cov-report=html"
}

if ($KeepDb) {
    $pytestCmd += " --reuse-db"
}

# Additional useful flags
$pytestCmd += " --tb=short"
$pytestCmd += " --strict-markers"

# Step 4 - Execute tests within the web container
Write-Host "`n[STEP 4] Executing tests inside container..." -ForegroundColor Yellow
Write-Host "   Command: $pytestCmd" -ForegroundColor Gray
Write-Host ""

try {
    docker compose exec -T web bash -lc "DJANGO_SETTINGS_MODULE=settings.test $pytestCmd"
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "`n==============================================================" -ForegroundColor Cyan
        Write-Host "[SUCCESS] All tests passed." -ForegroundColor Green
        
        if ($Coverage) {
            Write-Host "`n[INFO] Coverage report at htmlcov/index.html" -ForegroundColor Cyan
        }
        
        Write-Host ""
    } else {
        Write-Host "`n==============================================================" -ForegroundColor Cyan
        Write-Host "[ERROR] Tests failed (exit code: $exitCode)" -ForegroundColor Red
        Write-Host ""
        exit $exitCode
    }
} catch {
    Write-Host "`n[ERROR] Failed to execute tests: $_" -ForegroundColor Red
    exit 1
}
