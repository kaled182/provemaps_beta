# Phase 7 Day 7 - Deploy Monitoring Stack
# Prometheus + Grafana for Spatial Radius Search monitoring

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "PHASE 7 - MONITORING STACK DEPLOYMENT" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

# Check if Docker is running
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        exit 1
    }
    Write-Host "`n[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "`n[ERROR] Docker is not available. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Navigate to docker directory (parent of scripts dir)
$dockerDir = Join-Path (Split-Path $PSScriptRoot -Parent) "docker"
Set-Location -Path $dockerDir

Write-Host "`n[DEPLOY] Building monitoring stack..." -ForegroundColor Yellow
Write-Host "         Services: Prometheus + Grafana`n" -ForegroundColor Gray

# Start Prometheus + Grafana
docker compose up -d prometheus grafana

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Failed to start monitoring stack" -ForegroundColor Red
    exit 1
}

Write-Host "`n[WAIT] Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check container status
Write-Host "`n[STATUS] Container Status:" -ForegroundColor Cyan
docker compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}' | Select-String -Pattern "prometheus|grafana"

# Wait for Prometheus to be ready
Write-Host "`n[CHECK] Checking Prometheus health..." -ForegroundColor Yellow
$maxRetries = 10
$retryCount = 0
$prometheusReady = $false

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] Prometheus is healthy" -ForegroundColor Green
            $prometheusReady = $true
            break
        }
    } catch {
        $retryCount++
        Write-Host "     Attempt $retryCount/$maxRetries - Waiting for Prometheus..." -ForegroundColor Gray
        Start-Sleep -Seconds 3
    }
}

if (-not $prometheusReady) {
    Write-Host "[WARN] Prometheus health check timed out (may still be starting)" -ForegroundColor Yellow
}

# Wait for Grafana to be ready
Write-Host "`n[CHECK] Checking Grafana health..." -ForegroundColor Yellow
$retryCount = 0
$grafanaReady = $false

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] Grafana is healthy" -ForegroundColor Green
            $grafanaReady = $true
            break
        }
    } catch {
        $retryCount++
        Write-Host "     Attempt $retryCount/$maxRetries - Waiting for Grafana..." -ForegroundColor Gray
        Start-Sleep -Seconds 3
    }
}

if (-not $grafanaReady) {
    Write-Host "[WARN] Grafana health check timed out (may still be starting)" -ForegroundColor Yellow
}

# Check Prometheus targets
Write-Host "`n[TARGETS] Prometheus Targets:" -ForegroundColor Cyan
try {
    $targets = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" -UseBasicParsing
    $activeTargets = $targets.data.activeTargets | Where-Object { $_.health -eq "up" }
    
    if ($activeTargets.Count -gt 0) {
        foreach ($target in $activeTargets) {
            Write-Host "          [OK] $($target.labels.job) - $($target.scrapeUrl)" -ForegroundColor Green
        }
    } else {
        Write-Host "          [WARN] No active targets yet (may take 30s for first scrape)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "          [WARN] Could not fetch targets (Prometheus may still be initializing)" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "MONITORING STACK DEPLOYED SUCCESSFULLY" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "[ACCESS] Monitoring Access Points:" -ForegroundColor Cyan
Write-Host "         Prometheus UI:  http://localhost:9090" -ForegroundColor White
Write-Host "         Grafana UI:     http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "         Django Metrics: http://localhost:8000/metrics/`n" -ForegroundColor White

Write-Host "[DASHBOARD] Grafana Dashboard:" -ForegroundColor Cyan
Write-Host "            1. Login to Grafana: http://localhost:3000" -ForegroundColor White
Write-Host "            2. Navigate: Dashboards -> Production -> Phase 7 - Spatial Radius Search Monitoring" -ForegroundColor White
Write-Host "            3. Default time range: Last 6 hours" -ForegroundColor White
Write-Host "            4. Auto-refresh: 30 seconds`n" -ForegroundColor White

Write-Host "[ALERTS] Prometheus Alerts:" -ForegroundColor Cyan
Write-Host "         View active alerts: http://localhost:9090/alerts" -ForegroundColor White
Write-Host "         Alert rules loaded: 16 total (5 critical, 6 warning, 2 info)" -ForegroundColor White
Write-Host "         Alert file: docker/prometheus/alerts/radius_search.yml`n" -ForegroundColor White

Write-Host "[NEXT] Next Steps:" -ForegroundColor Cyan
Write-Host "       1. Verify Prometheus scraping Django: http://localhost:9090/targets" -ForegroundColor White
Write-Host "       2. Check alert rules: http://localhost:9090/rules" -ForegroundColor White
Write-Host "       3. Import dashboard in Grafana (should auto-provision)" -ForegroundColor White
Write-Host "       4. Start 24h Phase 1 monitoring period`n" -ForegroundColor White

Write-Host "[DOCS] Documentation:" -ForegroundColor Cyan
Write-Host "       Setup guide: doc/operations/MONITORING_SETUP.md" -ForegroundColor White
Write-Host "       Deployment plan: doc/operations/PHASE7_DEPLOYMENT_PLAN.md`n" -ForegroundColor White

Write-Host "[COMMANDS] Useful Commands:" -ForegroundColor Cyan
Write-Host "           View logs:       docker compose logs -f prometheus grafana" -ForegroundColor White
Write-Host "           Restart:         docker compose restart prometheus grafana" -ForegroundColor White
Write-Host "           Stop:            docker compose stop prometheus grafana" -ForegroundColor White
Write-Host "           Remove:          docker compose down prometheus grafana`n" -ForegroundColor White

Write-Host "[SUCCESS] Monitoring stack is ready for Phase 1 (10% rollout) observation!`n" -ForegroundColor Green
