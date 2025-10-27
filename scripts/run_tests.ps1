#!/usr/bin/env pwsh
# ==============================================================================
# Run Tests - Executa testes com MariaDB no Docker
# ==============================================================================
# 
# Este script executa os testes usando MariaDB (Docker) como banco de dados,
# garantindo que o ambiente de teste seja próximo à produção.
#
# Uso:
#   .\scripts\run_tests.ps1                    # Todos os testes
#   .\scripts\run_tests.ps1 -Path tests/test_metrics.py  # Testes específicos
#   .\scripts\run_tests.ps1 -Coverage          # Com relatório de coverage
# ==============================================================================

param(
    [string]$Path = "tests/",
    [switch]$Coverage = $false,
    [switch]$Verbose = $false,
    [switch]$KeepDb = $false
)

$ErrorActionPreference = "Stop"

Write-Host "`n🧪 Executando testes com MariaDB (Docker)..." -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

# Verificar se Docker está rodando
Write-Host "`n📦 Verificando Docker..." -ForegroundColor Yellow
try {
    docker ps --format "{{.Names}}" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker não está rodando"
    }
    Write-Host "   ✅ Docker está ativo" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker não está rodando" -ForegroundColor Red
    Write-Host "   Execute: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

# Verificar containers necessários
Write-Host "`n🔍 Verificando containers..." -ForegroundColor Yellow
$dbContainer = docker ps --filter "name=db" --format "{{.Names}}" | Select-String "db"
$webContainer = docker ps --filter "name=web" --format "{{.Names}}" | Select-String "web"

if (-not $dbContainer) {
    Write-Host "   ❌ Container do MariaDB não encontrado" -ForegroundColor Red
    Write-Host "   Execute: docker compose up -d" -ForegroundColor Yellow
    exit 1
}
if (-not $webContainer) {
    Write-Host "   ❌ Container web não encontrado" -ForegroundColor Red
    Write-Host "   Execute: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "   ✅ MariaDB: $dbContainer" -ForegroundColor Green
Write-Host "   ✅ Web: $webContainer" -ForegroundColor Green

# Construir comando pytest
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

# Adicionar flags úteis
$pytestCmd += " --tb=short"
$pytestCmd += " --strict-markers"

# Executar testes dentro do container
Write-Host "`n🔬 Executando testes..." -ForegroundColor Yellow
Write-Host "   Comando: $pytestCmd" -ForegroundColor Gray
Write-Host ""

try {
    docker exec -it $webContainer bash -c "DJANGO_SETTINGS_MODULE=settings.test $pytestCmd"
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "✅ Todos os testes passaram!" -ForegroundColor Green
        
        if ($Coverage) {
            Write-Host "`n📊 Relatório de coverage disponível em:" -ForegroundColor Cyan
            Write-Host "   htmlcov/index.html" -ForegroundColor White
        }
        
        Write-Host ""
    } else {
        Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "❌ Alguns testes falharam (exit code: $exitCode)" -ForegroundColor Red
        Write-Host ""
        exit $exitCode
    }
} catch {
    Write-Host "`n❌ Erro ao executar testes: $_" -ForegroundColor Red
    exit 1
}
