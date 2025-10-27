#!/usr/bin/env pwsh
# ==============================================================================
# Setup Test Database - Configura permissões para testes no MariaDB
# ==============================================================================
# 
# Este script:
# 1. Verifica se o container MariaDB está rodando
# 2. Configura permissões para o usuário 'app' criar databases de teste
# 3. Valida que tudo está funcionando
#
# Uso:
#   .\scripts\setup_test_db.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "`n🔧 Configurando permissões de teste no MariaDB..." -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan

# Verificar se Docker está rodando
Write-Host "`n1️⃣  Verificando Docker..." -ForegroundColor Yellow
try {
    $dockerStatus = docker ps --format "{{.Names}}" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker não está rodando"
    }
    Write-Host "   ✅ Docker está ativo" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker não está rodando. Execute 'docker compose up -d' primeiro" -ForegroundColor Red
    exit 1
}

# Verificar se container do MariaDB está rodando
Write-Host "`n2️⃣  Verificando container MariaDB..." -ForegroundColor Yellow
$dbContainer = docker ps --filter "name=db" --format "{{.Names}}" | Select-String "db"
if (-not $dbContainer) {
    Write-Host "   ❌ Container do MariaDB não encontrado" -ForegroundColor Red
    Write-Host "   Execute: docker compose up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host "   ✅ Container encontrado: $dbContainer" -ForegroundColor Green

# Aplicar SQL de permissões
Write-Host "`n3️⃣  Configurando permissões..." -ForegroundColor Yellow
try {
    $sqlScript = Get-Content "scripts/setup_test_db_permissions.sql" -Raw
    $result = $sqlScript | docker exec -i $dbContainer mariadb -u root -padmin 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Permissões configuradas com sucesso" -ForegroundColor Green
    } else {
        throw "Erro ao aplicar permissões: $result"
    }
} catch {
    Write-Host "   ❌ Erro ao configurar permissões: $_" -ForegroundColor Red
    exit 1
}

# Validar permissões
Write-Host "`n4️⃣  Validando permissões..." -ForegroundColor Yellow
try {
    $grants = docker exec $dbContainer mariadb -u root -padmin -e "SHOW GRANTS FOR 'app'@'%';" --skip-column-names 2>&1
    
    if ($grants -match "GRANT ALL PRIVILEGES") {
        Write-Host "   ✅ Usuário 'app' tem permissões corretas" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Permissões parciais detectadas" -ForegroundColor Yellow
        Write-Host "   $grants" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ⚠️  Não foi possível validar permissões: $_" -ForegroundColor Yellow
}

# Testar criação de database de teste
Write-Host "`n5️⃣  Testando criação de database..." -ForegroundColor Yellow
try {
    $testSQL = @"
DROP DATABASE IF EXISTS test_validation_db;
CREATE DATABASE test_validation_db;
DROP DATABASE test_validation_db;
SELECT '✅ Database de teste criada e removida com sucesso' AS Status;
"@
    
    $testResult = $testSQL | docker exec -i $dbContainer mariadb -u app -papp_password --skip-column-names
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Usuário 'app' pode criar/dropar databases" -ForegroundColor Green
    } else {
        throw "Erro no teste: $testResult"
    }
} catch {
    Write-Host "   ❌ Erro ao testar criação de database: $_" -ForegroundColor Red
    Write-Host "   As permissões podem não estar corretas" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Configuração concluída com sucesso!" -ForegroundColor Green
Write-Host "`nPróximos passos:" -ForegroundColor Cyan
Write-Host "  1. Execute os testes: .\scripts\run_tests.ps1" -ForegroundColor White
Write-Host "  2. Ou dentro do container: docker exec -it mapsprovefiber-web-1 pytest tests/" -ForegroundColor White
Write-Host ""
