#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Script de Rollout Gradual do Vue 3 Dashboard
    
.PARAMETER Percentage
    Percentual de usuarios que verao Vue (0-100)
    
.PARAMETER MonitorTime
    Tempo em segundos para monitorar logs apos rollout (padrao: 30s)

.EXAMPLE
    .\rollout_vue.ps1 -Percentage 10
    .\rollout_vue.ps1 -Percentage 100
    .\rollout_vue.ps1 -Percentage 0  # Rollback
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateRange(0,100)]
    [int]$Percentage,
    
    [int]$MonitorTime = 30
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
$ProjectRoot = Split-Path -Parent $ScriptDir
$DockerDir = Join-Path $ProjectRoot "docker"
$EnvFile = Join-Path $ProjectRoot ".env"
$ComposeFile = Join-Path $DockerDir "docker-compose.yml"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Vue Dashboard Rollout - $Percentage%" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Validar ambiente Docker
Write-Host "[1/6] Validando ambiente Docker..." -ForegroundColor Cyan

if (-not (Test-Path $ComposeFile)) {
    Write-Host "ERROR: docker-compose.yml nao encontrado" -ForegroundColor Red
    exit 1
}

Push-Location $DockerDir

$containers = docker compose ps --quiet 2>$null
if (-not $containers) {
    Write-Host "ERROR: Containers nao estao rodando" -ForegroundColor Red
    Write-Host "Execute: docker compose up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK: Docker Compose rodando" -ForegroundColor Green

# 2. Atualizar variavel de ambiente
Write-Host "[2/6] Atualizando .env..." -ForegroundColor Cyan

if (-not (Test-Path $EnvFile)) {
    "" | Out-File -FilePath $EnvFile -Encoding utf8
}

$envContent = Get-Content $EnvFile -ErrorAction SilentlyContinue
$newEnvContent = @()
$foundRollout = $false
$foundUseVue = $false

foreach ($line in $envContent) {
    if ($line -match '^VUE_DASHBOARD_ROLLOUT_PERCENTAGE=') {
        $newEnvContent += "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$Percentage"
        $foundRollout = $true
    }
    elseif ($line -match '^USE_VUE_DASHBOARD=') {
        $useVueValue = if ($Percentage -gt 0) { "true" } else { "false" }
        $newEnvContent += "USE_VUE_DASHBOARD=$useVueValue"
        $foundUseVue = $true
    }
    else {
        $newEnvContent += $line
    }
}

if (-not $foundRollout) {
    $newEnvContent += "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$Percentage"
}

if (-not $foundUseVue) {
    $useVueValue = if ($Percentage -gt 0) { "true" } else { "false" }
    $newEnvContent += "USE_VUE_DASHBOARD=$useVueValue"
}

$newEnvContent | Out-File -FilePath $EnvFile -Encoding utf8 -Force
Write-Host "OK: .env atualizado" -ForegroundColor Green

# 3. Reiniciar servico web COM recarga de .env
Write-Host "[3/6] Reiniciando servico web com novas variaveis..." -ForegroundColor Cyan

try {
    # Parar web
    $output = docker compose stop web 2>&1
    Start-Sleep -Seconds 2
    
    # Subir web novamente (vai ler o .env atualizado)
    $output = docker compose up -d web 2>&1
    Write-Host "OK: Web reiniciado com novas variaveis" -ForegroundColor Green
} catch {
    Write-Host "Falha ao reiniciar" -ForegroundColor Yellow
}

Write-Host "Aguardando 20s para web inicializar..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

# 4. Health Check
Write-Host "[4/6] Verificando health check..." -ForegroundColor Cyan

$maxAttempts = 6
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts -and -not $healthy) {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/ready" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $healthy = $true
            Write-Host "OK: Servico saudavel (HTTP 200)" -ForegroundColor Green
        }
    } catch {
        Write-Host "Tentativa $attempt/$maxAttempts..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}

if (-not $healthy) {
    Write-Host "ERROR: Health check falhou" -ForegroundColor Red
    Write-Host "Verifique: docker compose logs web" -ForegroundColor Yellow
    exit 1
}

# 5. Validar configuracao aplicada
Write-Host "[5/6] Validando configuracao..." -ForegroundColor Cyan

$rolloutValue = (docker compose exec -T web sh -c "env | grep VUE_DASHBOARD_ROLLOUT_PERCENTAGE" 2>$null).Split("=")[1].Trim()
$useVueValue = (docker compose exec -T web sh -c "env | grep '^USE_VUE_DASHBOARD='" 2>$null).Split("=")[1].Trim()

Write-Host "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$rolloutValue" -ForegroundColor Cyan
Write-Host "USE_VUE_DASHBOARD=$useVueValue" -ForegroundColor Cyan

# 6. Monitorar logs
Write-Host "[6/6] Monitorando logs por ${MonitorTime}s..." -ForegroundColor Cyan
Write-Host "Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray

$job = Start-Job -ScriptBlock {
    param($DockerDir)
    Set-Location $DockerDir
    docker compose logs --tail=20 -f web 2>&1
} -ArgumentList $DockerDir

Wait-Job $job -Timeout $MonitorTime | Out-Null
Receive-Job $job
Stop-Job $job -ErrorAction SilentlyContinue
Remove-Job $job -ErrorAction SilentlyContinue

# Resumo
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Rollout concluido com sucesso!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Configuracao: VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$Percentage%" -ForegroundColor Cyan
Write-Host ""

if ($Percentage -eq 0) {
    Write-Host "WARN: Dashboard Vue DESABILITADO (100% legacy)" -ForegroundColor Yellow
}
elseif ($Percentage -eq 100) {
    Write-Host "SUCCESS: Dashboard Vue 100% ATIVO!" -ForegroundColor Green
}
else {
    Write-Host "INFO: Rollout canary ~$Percentage% (Vue) + ~$($100-$Percentage)% (legacy)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor Cyan
Write-Host "  1. Monitorar logs: docker compose logs -f web" -ForegroundColor Gray
Write-Host "  2. Testar: http://localhost:8000/monitoring/backbone/" -ForegroundColor Gray

if ($Percentage -gt 0 -and $Percentage -lt 100) {
    if ($Percentage -lt 10) {
        Write-Host "  3. Avancar: .\scripts\rollout_vue.ps1 -Percentage 10" -ForegroundColor Green
    } elseif ($Percentage -lt 25) {
        Write-Host "  3. Avancar: .\scripts\rollout_vue.ps1 -Percentage 25" -ForegroundColor Green
    } elseif ($Percentage -lt 50) {
        Write-Host "  3. Avancar: .\scripts\rollout_vue.ps1 -Percentage 50" -ForegroundColor Green
    } else {
        Write-Host "  3. Avancar: .\scripts\rollout_vue.ps1 -Percentage 100" -ForegroundColor Green
    }
}

Pop-Location
Write-Host ""
