Param(
  [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "[E2E] Iniciando pipeline de testes end-to-end..." -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

# 1. Build frontend
Write-Host "[E2E] Build frontend" -ForegroundColor Yellow
Push-Location "$PSScriptRoot\..\frontend"
if (!(Test-Path package.json)) { throw "package.json não encontrado em frontend" }
npm run build | Write-Host

# 2. Restart web container (assume docker compose já ativo)
Write-Host "[E2E] Reiniciando container web" -ForegroundColor Yellow
Push-Location "$PSScriptRoot\..\docker"
docker compose restart web | Write-Host
Pop-Location

# 3. Instalar browsers Playwright se faltando
Write-Host "[E2E] Instalando browsers Playwright (se necessário)" -ForegroundColor Yellow
Push-Location "$PSScriptRoot\..\frontend"
npx playwright install chromium --with-deps | Write-Host

# 4. Exporta variável base URL
$env:E2E_BASE_URL = $BaseUrl
Write-Host "[E2E] Base URL definida: $env:E2E_BASE_URL" -ForegroundColor Green

# 5. Executar teste específico nav menu
Write-Host "[E2E] Executando testes nav_menu" -ForegroundColor Yellow
npx playwright test tests/nav_menu.spec.ts --reporter=line || exit 1

Write-Host "[E2E] Testes concluídos" -ForegroundColor Green
Pop-Location
