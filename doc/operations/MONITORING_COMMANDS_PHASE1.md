# Monitoring Commands - Phase 1 Canary Rollout

**Período de Monitoring:** 12/11/2025 17:50 → 13/11/2025 17:50 (24h)  
**Frequência:** Checks a cada 4 horas

---

## 🔍 Quick Health Check (Run every 4h)

```powershell
# Copy-paste this entire block

Write-Host "`n=== HEALTH CHECK - $(Get-Date -Format 'dd/MM/yyyy HH:mm') ===`n" -ForegroundColor Cyan

# 1. Services Status
Write-Host "[1/6] Docker Services:" -ForegroundColor Yellow
docker compose -f d:\provemaps_beta\docker\docker-compose.yml ps --format "table {{.Service}}\t{{.State}}\t{{.Health}}"

# 2. Error Count (last 4h)
Write-Host "`n[2/6] Error Count (last 4h):" -ForegroundColor Yellow
$errors = docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 4h web | Select-String "error|exception" -Context 0
Write-Host "Total Errors: $($errors.Count)" -ForegroundColor $(if ($errors.Count -gt 10) { 'Red' } else { 'Green' })

# 3. WebSocket Activity
Write-Host "`n[3/6] WebSocket Status (last 10 connections):" -ForegroundColor Yellow
docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 4h web | Select-String "websocket.*connected|websocket.*failed" | Select-Object -Last 10

# 4. Resource Usage
Write-Host "`n[4/6] Resource Usage:" -ForegroundColor Yellow
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | Select-Object -First 6

# 5. Dashboard Response Time
Write-Host "`n[5/6] Dashboard Response Time:" -ForegroundColor Yellow
$time = Measure-Command { Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard -UseBasicParsing }
Write-Host "$([int]$time.TotalMilliseconds) ms" -ForegroundColor $(if ($time.TotalMilliseconds -gt 3000) { 'Red' } else { 'Green' })

# 6. Vue SPA Static Files
Write-Host "`n[6/6] Vue SPA Assets:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri http://localhost:8000/static/vue-spa/assets/main.js -Method Head -UseBasicParsing
    Write-Host "main.js: $($response.StatusCode) - $($response.Headers['Content-Length']) bytes" -ForegroundColor Green
} catch {
    Write-Host "main.js: FAILED" -ForegroundColor Red
}

Write-Host "`n=== HEALTH CHECK COMPLETE ===`n" -ForegroundColor Cyan
```

**Expected Output:**
- Services: All "Up (healthy)"
- Errors: < 10 in 4h
- WebSocket: Connections successful
- CPU: <50%, Memory: <512MB
- Response Time: <3000ms
- Static Files: 200 OK

---

## 📊 Detailed Metrics Collection

### Error Rate Analysis
```powershell
# Count errors by type (run daily)
docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 24h web | Select-String "error|exception" | Group-Object -Property Line | Sort-Object Count -Descending | Select-Object -First 10 Count, Name

# Error rate percentage
$total_requests = (docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 24h web | Select-String "GET|POST" | Measure-Object).Count
$errors = (docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 24h web | Select-String "error" | Measure-Object).Count
$error_rate = [math]::Round(($errors / $total_requests) * 100, 2)
Write-Host "Error Rate: $error_rate%" -ForegroundColor $(if ($error_rate -gt 1) { 'Red' } else { 'Green' })
```

**Target:** < 1% error rate

---

### Performance Metrics (P95 Load Time)
```powershell
# Measure 10 page loads and calculate P95
$loadTimes = @()
1..10 | ForEach-Object {
    Write-Host "Load test $_/10..." -NoNewline
    $time = Measure-Command { 
        Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard -UseBasicParsing | Out-Null
    }
    $loadTimes += [int]$time.TotalMilliseconds
    Write-Host " $([int]$time.TotalMilliseconds) ms"
    Start-Sleep -Seconds 2
}

# Calculate P95 (9th value when sorted)
$sorted = $loadTimes | Sort-Object
$p95 = $sorted[8] # 0-indexed, 9th item = P95
Write-Host "`nP95 Load Time: $p95 ms" -ForegroundColor $(if ($p95 -gt 3000) { 'Red' } else { 'Green' })
Write-Host "Target: < 3000 ms"
Write-Host "Min: $($sorted[0]) ms | Max: $($sorted[9]) ms | Avg: $([int]($loadTimes | Measure-Object -Average).Average) ms"
```

**Target:** P95 < 3000ms

---

### WebSocket Uptime
```powershell
# Count successful vs failed connections (last 24h)
$connected = (docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 24h web | Select-String "websocket.*connected" | Measure-Object).Count
$failed = (docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 24h web | Select-String "websocket.*failed|websocket.*error" | Measure-Object).Count
$total = $connected + $failed
$uptime = if ($total -gt 0) { [math]::Round(($connected / $total) * 100, 2) } else { 100 }

Write-Host "`nWebSocket Uptime: $uptime%" -ForegroundColor $(if ($uptime -lt 99) { 'Red' } else { 'Green' })
Write-Host "Connected: $connected | Failed: $failed | Total: $total"
```

**Target:** > 99% uptime

---

### Resource Trends
```powershell
# Monitor CPU/Memory every hour for 24h (background job)
$logFile = "d:\provemaps_beta\logs\resource_monitoring_$(Get-Date -Format 'yyyyMMdd').csv"
Write-Host "Starting 24h resource monitoring (logging to $logFile)"
Write-Host "Press Ctrl+C to stop"

# CSV Header
"Timestamp,Service,CPU,Memory" | Out-File $logFile

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # Get stats for web, celery, redis
    $stats = docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" | Select-String "web|celery|redis"
    
    foreach ($line in $stats) {
        $parts = $line -split ','
        $service = $parts[0] -replace 'docker-', '' -replace '-1', ''
        $cpu = $parts[1] -replace '%', ''
        $mem = $parts[2] -replace ' / .*', '' -replace 'MiB', ''
        
        "$timestamp,$service,$cpu,$mem" | Out-File $logFile -Append
    }
    
    Write-Host "[$timestamp] Logged stats for web, celery, redis"
    Start-Sleep -Seconds 3600 # 1 hour
}
```

**Target:** CPU <50%, Memory <512MB (sustained)

---

## 🧪 Canary Rollout Validation

### Test User Distribution
```powershell
# Simulate 100 sessions to verify ~10% get Vue
$vueCount = 0
$legacyCount = 0

Write-Host "Testing canary distribution (100 requests)..."

1..100 | ForEach-Object {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $response = Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard -WebSession $session -UseBasicParsing
    
    if ($response.Content -match 'vue-spa|MapsProve Dashboard') {
        $vueCount++
    } else {
        $legacyCount++
    }
    
    if ($_ % 20 -eq 0) {
        Write-Host "Progress: $_/100 - Vue: $vueCount, Legacy: $legacyCount"
    }
}

$vuePercent = [math]::Round(($vueCount / 100) * 100, 1)
Write-Host "`nResults:" -ForegroundColor Cyan
Write-Host "Vue Dashboard: $vueCount ($vuePercent%)" -ForegroundColor Green
Write-Host "Legacy: $legacyCount ($($100 - $vuePercent)%)" -ForegroundColor Yellow
Write-Host "Expected: ~10% Vue, ~90% Legacy"
```

**Expected:** 8-12% Vue, 88-92% Legacy (statistical variance acceptable)

---

### Manual Session Test
```powershell
# Test if same session gets consistent version
Write-Host "Testing session consistency..."

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$firstResponse = Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard -WebSession $session -UseBasicParsing
$secondResponse = Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard -WebSession $session -UseBasicParsing

$firstVersion = if ($firstResponse.Content -match 'vue-spa') { 'Vue' } else { 'Legacy' }
$secondVersion = if ($secondResponse.Content -match 'vue-spa') { 'Vue' } else { 'Legacy' }

Write-Host "First request: $firstVersion"
Write-Host "Second request: $secondVersion"

if ($firstVersion -eq $secondVersion) {
    Write-Host "✅ Session consistency: PASS" -ForegroundColor Green
} else {
    Write-Host "❌ Session consistency: FAIL (user would see version flip-flop)" -ForegroundColor Red
}
```

**Expected:** Same version on both requests (session hash deterministic)

---

## 🚨 Alert Triggers

### Automatic Alert Script
```powershell
# Run this in background to alert on critical issues
Write-Host "Starting alert monitoring (Ctrl+C to stop)..."

while ($true) {
    # Check 1: Error rate
    $errors = (docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 1h web | Select-String "error" | Measure-Object).Count
    if ($errors -gt 50) {
        Write-Host "[ALERT] High error rate: $errors errors in last hour!" -ForegroundColor Red -BackgroundColor Yellow
    }
    
    # Check 2: WebSocket failures
    $wsFails = (docker compose -f d:\provemaps_beta\docker\docker-compose.yml logs --since 1h web | Select-String "websocket.*failed" | Measure-Object).Count
    if ($wsFails -gt 10) {
        Write-Host "[ALERT] WebSocket failures: $wsFails in last hour!" -ForegroundColor Red -BackgroundColor Yellow
    }
    
    # Check 3: Service health
    $unhealthy = docker compose -f d:\provemaps_beta\docker\docker-compose.yml ps --format "{{.State}}" | Select-String "unhealthy|restarting"
    if ($unhealthy) {
        Write-Host "[ALERT] Unhealthy services detected!" -ForegroundColor Red -BackgroundColor Yellow
        docker compose -f d:\provemaps_beta\docker\docker-compose.yml ps
    }
    
    # Check 4: High CPU
    $webCpu = docker stats --no-stream --format "{{.CPUPerc}}" docker-web-1 | ForEach-Object { $_ -replace '%', '' }
    if ([float]$webCpu -gt 80) {
        Write-Host "[ALERT] High CPU usage: $webCpu%" -ForegroundColor Red -BackgroundColor Yellow
    }
    
    Start-Sleep -Seconds 300 # Check every 5 minutes
}
```

**Alert Thresholds:**
- Errors: >50/hour
- WebSocket fails: >10/hour
- Unhealthy services: Any
- CPU: >80%

---

## 📝 Monitoring Log Template

**Copy and update every 4 hours:**

```
=== MONITORING LOG - 12/11/2025 18:00 ===

Services Status: [OK/WARN/FAIL]
- web: [UP/DOWN] (healthy/unhealthy)
- celery: [UP/DOWN]
- beat: [UP/DOWN]
- redis: [UP/DOWN]
- postgres: [UP/DOWN]

Metrics (last 4h):
- Error Count: _____
- WebSocket Success Rate: _____%
- Avg Response Time: _____ ms
- CPU Usage (web): _____%
- Memory Usage (web): _____ MB

Canary Distribution:
- Vue Dashboard: _____%
- Legacy: _____%

Issues Found:
- [None / List issues]

Actions Taken:
- [None / List actions]

Next Check: 12/11/2025 22:00
```

---

**Boa prática:** Mantenha este terminal aberto e execute os health checks a cada 4h durante as próximas 24h.

**Última atualização:** 12/11/2025 — 17:55
