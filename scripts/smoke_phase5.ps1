<#
.SYNOPSIS
    Automated smoke test for MapsProveFiber v2.0 (Phase 5 deployment validation)

.DESCRIPTION
    Executes comprehensive smoke tests validating:
    - Health endpoints (/healthz, /ready, /live, /celery/status)
    - Prometheus metrics endpoint
    - Inventory API endpoints
    - Dashboard page rendering
    - Database migrations status
    - Static files serving
    - Legacy endpoint removal

.PARAMETER BaseUrl
    Base URL of the application (default: http://localhost:8000)

.PARAMETER Verbose
    Enable verbose output with detailed request/response information

.EXAMPLE
    .\smoke_phase5.ps1
    Run all smoke tests against localhost:8000

.EXAMPLE
    .\smoke_phase5.ps1 -BaseUrl "https://mapsprove.yourdomain.com" -Verbose
    Run smoke tests against production with verbose output

.NOTES
    Version: 2.0.0
    Author: MapsProveFiber Team
    Date: 2025-11-08
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:8000",
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

# Color output functions
function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Failure {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

# Test counter
$script:TestsPassed = 0
$script:TestsFailed = 0
$script:TestsWarning = 0

# Test execution wrapper
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200,
        [string]$ExpectedContent = $null,
        [hashtable]$Headers = @{}
    )
    
    Write-Info "Testing: $Name"
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -Headers $Headers -UseBasicParsing -TimeoutSec 10
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            if ($ExpectedContent -and $response.Content -notmatch $ExpectedContent) {
                Write-Failure "$Name - Status OK but content mismatch (expected: $ExpectedContent)"
                $script:TestsFailed++
                return $false
            }
            
            Write-Success "$Name - Status: $($response.StatusCode)"
            if ($Verbose) {
                Write-Host "   Response Length: $($response.Content.Length) bytes" -ForegroundColor Gray
            }
            $script:TestsPassed++
            return $true
        } else {
            Write-Failure "$Name - Unexpected status: $($response.StatusCode) (expected: $ExpectedStatus)"
            $script:TestsFailed++
            return $false
        }
    } catch {
        Write-Failure "$Name - Request failed: $($_.Exception.Message)"
        if ($Verbose) {
            Write-Host "   Error Details: $($_.Exception.ToString())" -ForegroundColor Gray
        }
        $script:TestsFailed++
        return $false
    }
}

# Header
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  MapsProveFiber v2.0 - Smoke Test Suite (Phase 5)" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""
Write-Info "Base URL: $BaseUrl"
Write-Info "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

# ═══════════════════════════════════════════════════════════════
# 1. Health Checks
# ═══════════════════════════════════════════════════════════════
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host " 1. Health Checks" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow

Test-Endpoint -Name "Health Check (/healthz)" -Url "$BaseUrl/healthz" -ExpectedContent "ok"
Test-Endpoint -Name "Readiness Check (/ready)" -Url "$BaseUrl/ready" -ExpectedContent "ready"
Test-Endpoint -Name "Liveness Check (/live)" -Url "$BaseUrl/live" -ExpectedContent "ok"

# Celery status may return 503 if workers are down (warning, not failure)
Write-Info "Testing: Celery Status (/celery/status)"
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/celery/status" -Method GET -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Success "Celery Status - Workers active"
        $script:TestsPassed++
    } else {
        Write-Warning "Celery Status - Unexpected status: $($response.StatusCode)"
        $script:TestsWarning++
    }
} catch {
    if ($_.Exception.Response.StatusCode.Value__ -eq 503) {
        Write-Warning "Celery Status - No workers detected (503) - This is OK for environments without Celery"
        $script:TestsWarning++
    } else {
        Write-Failure "Celery Status - Request failed: $($_.Exception.Message)"
        $script:TestsFailed++
    }
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# 2. Prometheus Metrics
# ═══════════════════════════════════════════════════════════════
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host " 2. Prometheus Metrics" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow

Test-Endpoint -Name "Metrics Endpoint (/metrics/)" -Url "$BaseUrl/metrics/" -ExpectedContent "django_http_requests"

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# 3. Inventory API (v2.0 endpoints)
# ═══════════════════════════════════════════════════════════════
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host " 3. Inventory API Endpoints" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow

Test-Endpoint -Name "Sites API" -Url "$BaseUrl/api/v1/inventory/sites/"
Test-Endpoint -Name "Devices API" -Url "$BaseUrl/api/v1/inventory/devices/"
Test-Endpoint -Name "Ports API" -Url "$BaseUrl/api/v1/inventory/ports/"
Test-Endpoint -Name "Fibers API" -Url "$BaseUrl/api/v1/inventory/fibers/"
Test-Endpoint -Name "Fiber Oper Status (Cached)" -Url "$BaseUrl/api/v1/inventory/fibers/oper-status/"

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# 4. Dashboard Pages
# ═══════════════════════════════════════════════════════════════
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host " 4. Dashboard Pages" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow

Test-Endpoint -Name "Maps Dashboard" -Url "$BaseUrl/maps_view/dashboard/" -ExpectedContent "dashboard"
Test-Endpoint -Name "Route Builder" -Url "$BaseUrl/routes_builder/fiber-route-builder/" -ExpectedContent "route"

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# 5. Legacy Endpoints Removed Check
# ═══════════════════════════════════════════════════════════════
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host " 5. Legacy Endpoints (Should Return 404)" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow

# These should return 404 in v2.0
Write-Info "Testing: Legacy /zabbix_api/devices/ (should be 404)"
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/zabbix_api/devices/" -Method GET -UseBasicParsing -TimeoutSec 10
    Write-Failure "Legacy endpoint still accessible - MIGRATION INCOMPLETE!"
    $script:TestsFailed++
} catch {
    if ($_.Exception.Response.StatusCode.Value__ -eq 404) {
        Write-Success "Legacy /zabbix_api/devices/ correctly removed (404)"
        $script:TestsPassed++
    } else {
        Write-Warning "Legacy endpoint returned unexpected status: $($_.Exception.Response.StatusCode.Value__)"
        $script:TestsWarning++
    }
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# 6. Database Migrations Status
# ═══════════════════════════════════════════════════════════════
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host " 6. Database Migrations" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow

Write-Info "Checking migration status..."
try {
    $migrationOutput = python manage.py showmigrations --plan 2>&1
    if ($LASTEXITCODE -eq 0) {
        $unapplied = $migrationOutput | Select-String -Pattern "\[ \]" -CaseSensitive
        if ($unapplied) {
            Write-Warning "Unapplied migrations detected:"
            $unapplied | ForEach-Object { Write-Host "   $_" -ForegroundColor Yellow }
            $script:TestsWarning++
        } else {
            Write-Success "All migrations applied"
            $script:TestsPassed++
        }
    } else {
        Write-Failure "Migration check failed: $migrationOutput"
        $script:TestsFailed++
    }
} catch {
    Write-Failure "Migration check error: $($_.Exception.Message)"
    $script:TestsFailed++
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# 7. Static Files Serving
# ═══════════════════════════════════════════════════════════════
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host " 7. Static Files" -ForegroundColor Yellow
Write-Host "───────────────────────────────────────────────────────────────" -ForegroundColor Yellow

Test-Endpoint -Name "Admin CSS" -Url "$BaseUrl/static/admin/css/base.css"
Test-Endpoint -Name "Django Admin" -Url "$BaseUrl/admin/login/" -ExpectedContent "Django"

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# Summary Report
# ═══════════════════════════════════════════════════════════════
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  Test Summary" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

$totalTests = $script:TestsPassed + $script:TestsFailed + $script:TestsWarning

Write-Host "Total Tests:   $totalTests" -ForegroundColor White
Write-Host "✅ Passed:      $($script:TestsPassed)" -ForegroundColor Green
Write-Host "❌ Failed:      $($script:TestsFailed)" -ForegroundColor Red
Write-Host "⚠️  Warnings:    $($script:TestsWarning)" -ForegroundColor Yellow

Write-Host ""

if ($script:TestsFailed -eq 0) {
    if ($script:TestsWarning -gt 0) {
        Write-Warning "Smoke tests passed with warnings. Review warnings before production deployment."
        exit 0
    } else {
        Write-Success "All smoke tests passed! ✨ Deployment validated."
        exit 0
    }
} else {
    Write-Failure "Smoke tests failed! ❌ Fix issues before deployment."
    exit 1
}
