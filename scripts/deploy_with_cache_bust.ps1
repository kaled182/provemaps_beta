# Deploy com cache busting automático
# Gera novo STATIC_ASSET_VERSION, rebuild frontend, copia assets, restart server

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== DEPLOY COM CACHE BUSTING ===" -ForegroundColor Cyan

# 1. Gerar novo timestamp
$timestamp = Get-Date -Format "yyyyMMddHHmmss" -AsUTC
$gitSha = try {
    (git -C "D:\provemaps_beta" rev-parse --short HEAD 2>$null) -replace "`n|`r",""
} catch {
    "nosha"
}
$version = "$gitSha-$timestamp"

Write-Host "`n[1] Nova versão gerada:" -ForegroundColor Yellow
Write-Host "    STATIC_ASSET_VERSION=$version" -ForegroundColor Green

# 2. Build frontend (opcional)
if (-not $SkipBuild) {
    Write-Host "`n[2] Building frontend..." -ForegroundColor Yellow
    Push-Location "D:\provemaps_beta\frontend"
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "Build falhou!"
    }
    Pop-Location
    Write-Host "    Build concluído!" -ForegroundColor Green
} else {
    Write-Host "`n[2] Build pulado (--SkipBuild)" -ForegroundColor Gray
}

# 3. Copiar assets para container
Write-Host "`n[3] Copiando assets para container..." -ForegroundColor Yellow
Push-Location "D:\provemaps_beta\docker"

# Verificar se container está rodando
$webRunning = docker compose ps web --format json | ConvertFrom-Json | Where-Object { $_.State -eq "running" }
if (-not $webRunning) {
    Write-Host "    Container web não está rodando, iniciando..." -ForegroundColor Yellow
    docker compose up -d web
    Start-Sleep -Seconds 5
}

docker compose cp ../backend/staticfiles/vue-spa web:/app/backend/staticfiles/
Write-Host "    Assets copiados!" -ForegroundColor Green

# 4. Setar variável de ambiente e restart
Write-Host "`n[4] Aplicando nova versão..." -ForegroundColor Yellow

# Escrever versão em arquivo .env no container
$envContent = "STATIC_ASSET_VERSION=$version"
$envContent | Out-File -FilePath "D:\provemaps_beta\docker\.env.deploy" -Encoding ASCII -NoNewline

docker compose cp .env.deploy web:/tmp/.env.deploy
docker compose exec web sh -c "cat /tmp/.env.deploy > /app/.env.deploy && pkill -HUP gunicorn"
Start-Sleep -Seconds 2

Remove-Item "D:\provemaps_beta\docker\.env.deploy" -ErrorAction SilentlyContinue

Pop-Location

# 5. Validar
Write-Host "`n[5] Validando..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$html = (Invoke-WebRequest -Uri "http://localhost:8000/NetworkDesign/" -UseBasicParsing).Content
if ($html -match 'src="/static/vue-spa/assets/main\.js\?v=([^"]+)"') {
    $deployedVersion = $matches[1]
    Write-Host "    Versão no HTML: $deployedVersion" -ForegroundColor Cyan
    
    if ($deployedVersion -eq $version) {
        Write-Host "`n✅ DEPLOY BEM-SUCEDIDO!" -ForegroundColor Green
        Write-Host "   Cache busting ativo com versão: $version" -ForegroundColor Green
    } else {
        Write-Host "`n⚠️  VERSÃO DIFERENTE!" -ForegroundColor Yellow
        Write-Host "   Esperado: $version" -ForegroundColor Red
        Write-Host "   Atual:    $deployedVersion" -ForegroundColor Red
        Write-Host "`n   Isso pode ser cache do Gunicorn. Tentando restart completo..." -ForegroundColor Yellow
        
        Push-Location "D:\provemaps_beta\docker"
        docker compose restart web
        Start-Sleep -Seconds 5
        Pop-Location
        
        $htmlRetry = (Invoke-WebRequest -Uri "http://localhost:8000/NetworkDesign/" -UseBasicParsing).Content
        if ($htmlRetry -match 'src="/static/vue-spa/assets/main\.js\?v=([^"]+)"') {
            $retryVersion = $matches[1]
            if ($retryVersion -ne $deployedVersion) {
                Write-Host "   Nova versão após restart: $retryVersion" -ForegroundColor Cyan
            }
        }
    }
} else {
    Write-Host "`n❌ FALHA: não encontrou asset no HTML!" -ForegroundColor Red
}

Write-Host "`n=== CONCLUÍDO ===" -ForegroundColor Cyan
Write-Host "`nPróximo passo: Abra o navegador e pressione Ctrl+Shift+R (hard refresh)`n" -ForegroundColor Yellow
