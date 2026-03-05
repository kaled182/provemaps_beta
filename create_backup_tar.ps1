# Script de Backup Simplificado - ProveMaps v2.1.0
# Usa TAR (disponível no Windows 10+) para criar arquivo comprimido

$ErrorActionPreference = "Continue"

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$version = "v2.1.0"
$backupName = "provemaps_beta_${version}_${timestamp}"
$backupFile = "backups\${backupName}.tar.gz"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ProveMaps Beta - Backup Creator" -ForegroundColor Cyan
Write-Host "   Version: $version" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Criar pasta de backups se não existir
if (-Not (Test-Path "backups")) {
    New-Item -ItemType Directory -Path "backups" | Out-Null
}

Write-Host "[1/2] Criando lista de arquivos..." -ForegroundColor Yellow

# Criar arquivo temporário com lista de exclusões
$excludeFile = "backups\.tarignore"
$excludeContent = @"
.git
.vscode
node_modules
__pycache__
.pytest_cache
venv
env
dist
staticfiles
media
logs
*.sqlite3
*.db
*.pyc
*.pyo
*.log
celerybeat-schedule
backups
temp_*
.DS_Store
Thumbs.db
"@

Set-Content -Path $excludeFile -Value $excludeContent

Write-Host "[2/2] Comprimindo projeto..." -ForegroundColor Yellow

# Lista de pastas/arquivos importantes a incluir
$includes = @(
    "backend",
    "frontend", 
    "docker",
    "doc",
    "database",
    "scripts",
    ".env.example",
    "README.md",
    "makefile",
    "pytest.ini",
    "DOCKER_QUICKREF.md"
)

# Usar tar para criar backup
$tarCmd = "tar"
$tarArgs = @(
    "-czf",
    $backupFile,
    "--exclude-from=$excludeFile"
)

# Adicionar cada pasta/arquivo
foreach ($item in $includes) {
    if (Test-Path $item) {
        $tarArgs += $item
    }
}

# Executar tar
& $tarCmd $tarArgs

# Remover arquivo de exclusões
Remove-Item $excludeFile -ErrorAction SilentlyContinue

# Verificar se backup foi criado
if (Test-Path $backupFile) {
    $fileSize = (Get-Item $backupFile).Length
    $fileSizeMB = [math]::Round($fileSize / 1MB, 2)
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "   Backup Criado com Sucesso!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Arquivo: $backupFile" -ForegroundColor Cyan
    Write-Host "Tamanho: ${fileSizeMB} MB" -ForegroundColor Cyan
    Write-Host "Data: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Para descompactar:" -ForegroundColor Yellow
    Write-Host "  tar -xzf $backupFile" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Pronto para distribuicao e testes!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERRO: Backup nao foi criado!" -ForegroundColor Red
    Write-Host ""
}
