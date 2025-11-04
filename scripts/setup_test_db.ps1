#!/usr/bin/env pwsh
# ============================================================================
# Setup Test Database - Configure test permissions for MariaDB
# ============================================================================
#
# This script:
# 1. Verifies Docker/Compose prerequisites
# 2. Configures permissions for user 'app'
# 3. Validates creation of test databases
#
# Usage:
#   .\scripts\setup_test_db.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

$separator = "=============================================================="

Write-Host ""  # blank line for readability
Write-Host "[INFO] Setting up MariaDB test permissions..." -ForegroundColor Cyan
Write-Host $separator -ForegroundColor Cyan

# Step 1 - Docker
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

# Step 2 - Compose services
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

# Step 3 - Permissions
Write-Host "`n[STEP 3] Configuring permissions..." -ForegroundColor Yellow
try {
    $sqlScript = Get-Content "scripts/setup_test_db_permissions.sql" -Raw
    $result = $sqlScript | docker compose exec -T db mariadb -u root -proot 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [OK] Permissions configured successfully" -ForegroundColor Green
    } else {
        throw "Error applying permissions: $result"
    }
} catch {
    Write-Host "   [ERROR] Failed to configure permissions: $_" -ForegroundColor Red
    exit 1
}

# Step 4 - Grant validation
Write-Host "`n[STEP 4] Validating permissions..." -ForegroundColor Yellow
try {
    $grants = docker compose exec db mariadb --skip-column-names -u root -proot -e 'SHOW GRANTS FOR ''app''@''%'';' 2>&1

    if ($grants -match "GRANT ALL PRIVILEGES") {
        Write-Host "   [OK] User 'app' has the expected grants" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] Grants returned:" -ForegroundColor Yellow
        Write-Host "   $grants" -ForegroundColor Gray
    }
} catch {
    Write-Host "   [WARN] Could not validate grants: $_" -ForegroundColor Yellow
}

# Step 5 - Functional test
Write-Host "`n[STEP 5] Testing database creation..." -ForegroundColor Yellow
try {
    $testSQL = @'
DROP DATABASE IF EXISTS test_validation_db;
CREATE DATABASE test_validation_db;
DROP DATABASE test_validation_db;
SELECT "Test database created and dropped successfully" AS Status;
'@

    $testResult = $testSQL | docker compose exec -T db mariadb -u app -papp --skip-column-names

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [OK] User 'app' creates and drops test databases" -ForegroundColor Green
    } else {
        throw "Test failure: $testResult"
    }
} catch {
    Write-Host "   [ERROR] Failed to test database creation: $_" -ForegroundColor Red
    Write-Host "   Check permissions granted to user 'app'" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n$separator" -ForegroundColor Cyan
Write-Host "[SUCCESS] Setup complete." -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Run tests: .\scripts\run_tests.ps1" -ForegroundColor White
Write-Host "  2. Alternative: docker compose exec web pytest tests/ -v" -ForegroundColor White
Write-Host ""
