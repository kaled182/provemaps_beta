# Script simplificado de reorganização - Fase 6
# Executa as mudanças principais de estrutura

Write-Host "`n=== FASE 6: REORGANIZAÇÃO DE PASTAS ===" -ForegroundColor Cyan
Write-Host "Iniciando reorganização backend/frontend/database...`n" -ForegroundColor Green

$PROJECT_ROOT = "D:\provemaps_beta"
Set-Location $PROJECT_ROOT

# 1. Criar diretórios
Write-Host "1. Criando estrutura de diretórios..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "backend" -Force | Out-Null
New-Item -ItemType Directory -Path "frontend" -Force | Out-Null
New-Item -ItemType Directory -Path "frontend/static" -Force | Out-Null
New-Item -ItemType Directory -Path "database" -Force | Out-Null  
New-Item -ItemType Directory -Path "docker" -Force | Out-Null
Write-Host "   OK - Diretórios criados`n" -ForegroundColor Green

# 2. Mover Django apps para backend/
Write-Host "2. Movendo Django apps para backend/..." -ForegroundColor Yellow
$djangoApps = @("core", "inventory", "monitoring", "maps_view", "routes_builder", 
                "setup_app", "gpon", "dwdm", "integrations", "settings", 
                "templates", "tests", "service_accounts")

foreach ($app in $djangoApps) {
    if (Test-Path $app) {
        Move-Item -Path $app -Destination "backend\$app" -Force
        Write-Host "   Movido: $app/" -ForegroundColor Gray
    }
}
Write-Host "   OK - Apps Django movidos`n" -ForegroundColor Green

# 3. Mover arquivos Python raiz
Write-Host "3. Movendo arquivos Python..." -ForegroundColor Yellow
$pythonFiles = @("manage.py", "conftest.py", "pytest.ini", "pyproject.toml", 
                 "requirements.txt", "requirements_full.txt", "pyrightconfig.json")

foreach ($file in $pythonFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "backend\$file" -Force
        Write-Host "   Movido: $file" -ForegroundColor Gray
    }
}
Write-Host "   OK - Arquivos Python movidos`n" -ForegroundColor Green

# 4. Mover frontend
Write-Host "4. Movendo arquivos frontend..." -ForegroundColor Yellow
$frontendFiles = @("package.json", "package-lock.json", "babel.config.js")

foreach ($file in $frontendFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "frontend\$file" -Force
        Write-Host "   Movido: $file" -ForegroundColor Gray
    }
}

if (Test-Path "node_modules") {
    Move-Item -Path "node_modules" -Destination "frontend\node_modules" -Force
    Write-Host "   Movido: node_modules/" -ForegroundColor Gray
}
Write-Host "   OK - Frontend movido`n" -ForegroundColor Green

# 5. Mover database
Write-Host "5. Movendo arquivos database..." -ForegroundColor Yellow
$dbFiles = @("db.sqlite3", "test_db.sqlite3", "sql")

foreach ($file in $dbFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "database\$file" -Force
        Write-Host "   Movido: $file" -ForegroundColor Gray
    }
}
Write-Host "   OK - Database movido`n" -ForegroundColor Green

# 6. Mover Docker
Write-Host "6. Movendo arquivos Docker..." -ForegroundColor Yellow
$dockerFiles = @("dockerfile", "docker-compose.yml", "docker-compose.test.yml", "docker-entrypoint.sh")

foreach ($file in $dockerFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "docker\$file" -Force
        Write-Host "   Movido: $file" -ForegroundColor Gray
    }
}
Write-Host "   OK - Docker movido`n" -ForegroundColor Green

Write-Host "`n=== REORGANIZAÇÃO BÁSICA CONCLUÍDA ===" -ForegroundColor Green
Write-Host "`nPróximos passos:" -ForegroundColor Cyan
Write-Host "1. Atualizar settings/base.py (BASE_DIR)" -ForegroundColor White
Write-Host "2. Atualizar .env (PYTHONPATH)" -ForegroundColor White
Write-Host "3. Atualizar Docker files" -ForegroundColor White
Write-Host "4. Testar: cd backend; python manage.py check" -ForegroundColor White
Write-Host "`n"
