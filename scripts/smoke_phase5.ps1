# Smoke Test Script — Fase 5
# Executa validações automáticas dos principais endpoints e tarefas pós-migração
# Uso: powershell -ExecutionPolicy Bypass -File scripts/smoke_phase5.ps1

Write-Host "[Smoke] Iniciando validação pós-migração..."

function Test-Endpoint {
    param(
        [string]$Url,
        [string]$Description
    )
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        if ($resp.StatusCode -eq 200) {
            Write-Host "[OK] $Description ($Url)"
        } else {
            Write-Host "[FAIL] $Description ($Url) — Status: $($resp.StatusCode)"
        }
    } catch {
        Write-Host "[FAIL] $Description ($Url) — Erro: $_"
    }
}

# 1. Health
Test-Endpoint "http://localhost:8000/health/" "Health endpoint"

# 2. Metrics
Test-Endpoint "http://localhost:8000/metrics/" "Metrics endpoint"

# 3. Dashboard (GET)
Test-Endpoint "http://localhost:8000/dashboard/" "Dashboard view"

# 4. WebSocket (basic connectivity)
try {
    $ws = New-Object System.Net.WebSockets.ClientWebSocket
    $uri = [Uri] "ws://localhost:8000/ws/dashboard/status/"
    $ws.ConnectAsync($uri, [Threading.CancellationToken]::None).Wait(3000)
    if ($ws.State -eq 'Open') {
        Write-Host "[OK] WebSocket conectado"
        $ws.Dispose()
    } else {
        Write-Host "[FAIL] WebSocket não conectou"
    }
} catch {
    Write-Host "[FAIL] WebSocket erro: $_"
}

# 5. Celery worker status (via health)
Test-Endpoint "http://localhost:8000/health/?check=celery" "Celery worker health"

# 6. Migration/table verification
Write-Host "[Smoke] Verificando tabelas..."
python scripts/migration_phase5_verify.py --phase post
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Tabelas migradas e contagem consistente"
} else {
    Write-Host "[FAIL] Problema na verificação de tabelas"
}

# 7. Zabbix integration (basic)
Test-Endpoint "http://localhost:8000/api/zabbix/status/" "Zabbix status API"

Write-Host "[Smoke] Finalizado. Revise os resultados acima."
