Param(
    [ValidateSet("staging","production")][string]$Environment = "production",
    [string]$Version = "v2.0.0",
    [string]$BaseUrl = "http://localhost:8000",
    [switch]$SkipBackup,
    [switch]$SkipTests,
    [switch]$DryRun,
    [string]$LatencyReportFile = "deploy_latency_${Version}.json",
    [string]$SlackWebhook
)

$ErrorActionPreference = "Stop"

function Invoke-Step($Label, [scriptblock]$Action) {
    Write-Host "[deploy] $Label" -ForegroundColor Cyan
    if ($DryRun) { Write-Host "[deploy] (dry-run) skipping execution" -ForegroundColor Yellow; return }
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Label" }
}

Write-Host "=== Deploy Script (MapsProveFiber $Version) — $Environment ===" -ForegroundColor Magenta

# 1. Pre-flight checks
Invoke-Step "Validar dependências (git/python)" {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git não encontrado" }
    if (-not (Test-Path "D:/provemaps_beta/venv/Scripts/python.exe")) { throw "Python venv não encontrado" }
}

# 2. Optional backup
if (-not $SkipBackup) {
    $timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
    $backupFile = "backup_pre_${Version}_$timestamp.sql"
    Invoke-Step "Backup do banco (mysqldump)" {
        # Ajuste credenciais/DB conforme ambiente
        if ($Environment -eq "production") {
            # Exemplo placeholder — substitua pelo nome real do DB/usuário
            mysqldump -u root -p mapsprovefiber > $backupFile
        } else {
            Write-Host "[deploy] Staging: usando dump simplificado (placeholder)" -ForegroundColor Yellow
            mysqldump -u root -p mapsprovefiber_staging > $backupFile
        }
    }
    Write-Host "[deploy] Backup gerado: $backupFile" -ForegroundColor Green
} else {
    Write-Host "[deploy] Backup ignorado (-SkipBackup)" -ForegroundColor Yellow
}

# 3. Fetch + checkout tag/branch
Invoke-Step "Atualizar código (fetch + checkout)" {
    git fetch --all --prune
    git checkout inicial
    git pull origin inicial
}

# 4. Ensure tag exists (if release)
Invoke-Step "Verificar existência da tag $Version" {
    $tag = (git tag --list $Version).Trim()
    if (-not $tag) { throw "Tag $Version não encontrada. Crie com scripts/tag_release_v2.ps1 antes." }
    git checkout $Version
}

# 5. Install dependencies
Invoke-Step "Instalar dependências" {
    D:/provemaps_beta/venv/Scripts/python.exe -m pip install -r requirements.txt
}

# 6. Run tests (optional)
if (-not $SkipTests) {
    Invoke-Step "Executar testes" {
        D:/provemaps_beta/venv/Scripts/python.exe -m pytest -q
    }
} else {
    Write-Host "[deploy] Testes ignorados (-SkipTests)" -ForegroundColor Yellow
}

# 7. Migrations
Invoke-Step "Aplicar migrations" {
    D:/provemaps_beta/venv/Scripts/python.exe manage.py migrate --noinput
}

# 8. Migration verify script (if exists)
if (Test-Path "scripts/migration_phase5_verify.py") {
    Invoke-Step "Verificação de migração (fase5)" {
        D:/provemaps_beta/venv/Scripts/python.exe scripts/migration_phase5_verify.py --phase post --compare pre.json
    }
} else {
    Write-Host "[deploy] Script de verificação não encontrado (scripts/migration_phase5_verify.py)" -ForegroundColor Yellow
}

# 9. Collect static
Invoke-Step "Collectstatic" {
    D:/provemaps_beta/venv/Scripts/python.exe manage.py collectstatic --noinput
}

# 10. Health checks
Invoke-Step "Health checks (manage.py check)" {
    D:/provemaps_beta/venv/Scripts/python.exe manage.py check --deploy
}

# 10.1 Endpoint latency measurement
Invoke-Step "Medir latência endpoints" {
    $endpoints = @(
        "/healthz/",
        "/ready/",
        "/live/",
        "/api/v1/inventory/sites/",
        "/api/v1/inventory/fibers/oper-status/",
        "/metrics/"
    )
    $results = @()
    foreach ($ep in $endpoints) {
        $url = ($BaseUrl.TrimEnd('/')) + $ep
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $resp = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 15
            $status = $resp.StatusCode
        } catch {
            $status = "ERROR"
        }
        $sw.Stop()
        $ms = [math]::Round($sw.Elapsed.TotalMilliseconds,2)
        $results += [pscustomobject]@{endpoint=$ep; url=$url; status=$status; latency_ms=$ms}
        Write-Host "[latency] $ep -> $ms ms (status=$status)" -ForegroundColor DarkCyan
    }
    $json = $results | ConvertTo-Json -Depth 4
    if ($LatencyReportFile) { $json | Out-File -FilePath $LatencyReportFile -Encoding utf8 }
    $Global:__deployLatency = $results
}

# 11. Optional smoke script
if (Test-Path "scripts/smoke_phase5.ps1") {
    Invoke-Step "Smoke script (fase5)" {
        powershell -ExecutionPolicy Bypass -File scripts/smoke_phase5.ps1
    }
} else {
    Write-Host "[deploy] Smoke script não encontrado (scripts/smoke_phase5.ps1)" -ForegroundColor Yellow
}

# 12. Restart services (Docker example)
Invoke-Step "Restart containers (docker compose)" {
    if (Test-Path "docker-compose.yml") {
        docker compose up -d --build
    } else {
        Write-Host "[deploy] docker-compose.yml não encontrado, pule restart manual" -ForegroundColor Yellow
    }
}

Write-Host "=== Deploy concluído sem erros. ===" -ForegroundColor Green

# 13. Rollback helper message
Write-Host "[deploy] Para rollback: git checkout <tag_anterior>; restore backup SQL; migrate se necessário; restart services." -ForegroundColor Yellow

# 14. Optional Slack notification
if ($SlackWebhook) {
    try {
        $summary = [pscustomobject]@{
            version = $Version
            environment = $Environment
            base_url = $BaseUrl
            timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
            latency = $Global:__deployLatency
            message = "Deploy $Version concluído"
        }
        $payload = @{ text = "Deploy $Version ($Environment) concluído. Latências: " + ($Global:__deployLatency | ForEach-Object { "`n$($_.endpoint): $($_.latency_ms) ms ($($_.status))" }) } | ConvertTo-Json -Depth 6
        Invoke-RestMethod -Uri $SlackWebhook -Method POST -Body $payload -ContentType 'application/json'
        Write-Host "[deploy] Notificação Slack enviada." -ForegroundColor Green
    } catch {
        Write-Host "[deploy] Falha ao enviar Slack: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "[deploy] SlackWebhook não informado – notificação ignorada" -ForegroundColor Yellow
}
