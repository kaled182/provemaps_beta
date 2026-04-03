# Script de Backup do ProveMaps
# Versão: 2.1.0 - Map Provider Pattern
# Data: 2026-03-05

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$version = "v2.1.0"
$backupName = "provemaps_beta_${version}_${timestamp}"
$backupDir = "backups\$backupName"
$zipFile = "backups\${backupName}.zip"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ProveMaps Beta - Backup Creator" -ForegroundColor Cyan
Write-Host "   Version: $version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Criar diretório temporário
Write-Host "[1/5] Criando diretório de backup..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Lista de pastas/arquivos a EXCLUIR
$excludeDirs = @(
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "venv",
    "env",
    ".git",
    ".vscode",
    "dist",
    "staticfiles",
    "media",
    "logs",
    "*.sqlite3",
    "celerybeat-schedule",
    "backups",
    "temp_*",
    "*.pyc",
    "*.pyo",
    "*.log"
)

# Lista de pastas/arquivos a INCLUIR
$includeDirs = @(
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

Write-Host "[2/5] Copiando arquivos essenciais..." -ForegroundColor Yellow

# Copiar backend (excluindo cache e logs)
Write-Host "  - Copiando backend..." -ForegroundColor Gray
robocopy backend "$backupDir\backend" /E /XD __pycache__ .pytest_cache logs staticfiles media /XF *.pyc *.pyo *.log celerybeat-schedule *.sqlite3 /NFL /NDL /NJH /NJS | Out-Null

# Copiar frontend (excluindo node_modules e dist)
Write-Host "  - Copiando frontend..." -ForegroundColor Gray
robocopy frontend "$backupDir\frontend" /E /XD node_modules dist /XF *.log /NFL /NDL /NJH /NJS | Out-Null

# Copiar docker
Write-Host "  - Copiando configurações Docker..." -ForegroundColor Gray
robocopy docker "$backupDir\docker" /E /XF temp_cache.json *.log /NFL /NDL /NJH /NJS | Out-Null

# Copiar documentação
Write-Host "  - Copiando documentação..." -ForegroundColor Gray
robocopy doc "$backupDir\doc" /E /NFL /NDL /NJH /NJS | Out-Null

# Copiar database (apenas scripts SQL, não dados)
Write-Host "  - Copiando scripts de banco..." -ForegroundColor Gray
robocopy database "$backupDir\database" /E /XF *.sqlite3 /NFL /NDL /NJH /NJS | Out-Null

# Copiar scripts
Write-Host "  - Copiando scripts..." -ForegroundColor Gray
if (Test-Path "scripts") {
    robocopy scripts "$backupDir\scripts" /E /NFL /NDL /NJH /NJS | Out-Null
}

# Copiar arquivos raiz
Write-Host "  - Copiando arquivos raiz..." -ForegroundColor Gray
Copy-Item -Path ".env.example" -Destination "$backupDir\.env.example" -ErrorAction SilentlyContinue
Copy-Item -Path "README.md" -Destination "$backupDir\README.md" -ErrorAction SilentlyContinue
Copy-Item -Path "makefile" -Destination "$backupDir\makefile" -ErrorAction SilentlyContinue
Copy-Item -Path "pytest.ini" -Destination "$backupDir\pytest.ini" -ErrorAction SilentlyContinue
Copy-Item -Path "DOCKER_QUICKREF.md" -Destination "$backupDir\DOCKER_QUICKREF.md" -ErrorAction SilentlyContinue

# Criar arquivo de informações do backup
Write-Host "[3/5] Criando arquivo de informações..." -ForegroundColor Yellow
$infoContent = @"
# ProveMaps Beta - Backup Information

**Versão**: $version
**Data do Backup**: $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")
**Branch**: refactor/lazy-load-map-providers
**Commit**: $(git rev-parse --short HEAD 2>$null)

## Conteúdo desta Versão

### ✅ Implementado
- Provider Pattern completo para suporte multi-provider de mapas
- Mapbox GL JS v3.8.0 (provider padrão)
- Google Maps API (backward compatibility)
- Factory Pattern para seleção de provider via configuração
- Backward compatibility com código legado
- CSRF token handling corrigido
- API /api/config/ com configurações de mapas
- NetworkDesign totalmente funcional

### 📁 Estrutura do Backup

\`\`\`
provemaps_beta/
├── backend/           # Django application
├── frontend/          # Vue 3 application
├── docker/            # Docker Compose configs
├── doc/               # Documentation
├── database/          # SQL scripts
├── scripts/           # Utility scripts
├── .env.example       # Environment variables template
└── README.md          # Project documentation
\`\`\`

### 🚀 Como Usar Este Backup

#### 1. Extrair o arquivo
\`\`\`bash
unzip provemaps_beta_${version}_${timestamp}.zip
cd provemaps_beta_${version}_${timestamp}
\`\`\`

#### 2. Configurar ambiente
\`\`\`bash
# Copiar .env.example para .env
cp .env.example .env

# Editar .env com suas credenciais
# - ZABBIX_URL
# - ZABBIX_USER
# - ZABBIX_PASSWORD
# - MAPBOX_TOKEN (se usar Mapbox)
# - GOOGLE_MAPS_API_KEY (se usar Google Maps)
\`\`\`

#### 3. Iniciar com Docker
\`\`\`bash
# Subir todos os serviços
docker compose -f docker/docker-compose.yml up -d

# Aguardar inicialização (30-60 segundos)
docker compose -f docker/docker-compose.yml logs -f web
\`\`\`

#### 4. Acessar aplicação
- **URL**: http://localhost:8100
- **Login padrão**: admin / admin (alterar após primeiro acesso)
- **NetworkDesign**: http://localhost:8100/Network/NetworkDesign/

### 🔧 Configurar Provider de Mapas

1. Acessar: **Sistema > Configuração > Mapas**
2. Selecionar provider:
   - **Mapbox**: Requer token (https://mapbox.com)
   - **Google Maps**: Requer API key (https://console.cloud.google.com)
3. Salvar configuração
4. Recarregar página NetworkDesign

### 📝 Testes Recomendados

- [ ] Login no sistema
- [ ] Configurar provider de mapas
- [ ] Acessar NetworkDesign (/Network/NetworkDesign/)
- [ ] Verificar carregamento do mapa
- [ ] Criar novo cabo manualmente
- [ ] Editar cabo existente
- [ ] Importar cabo via KML
- [ ] Verificar visualização de cabos

### 🐛 Problemas Conhecidos

Nenhum problema crítico conhecido nesta versão.

### 📞 Suporte

Para problemas, consultar:
- **Documentação**: doc/features/MAP_PROVIDER_PATTERN.md
- **Roadmap**: doc/roadmap/network-design-improvements.md
- **Issues**: https://github.com/kaled182/provemaps_beta/issues

### 📊 Arquivos Excluídos do Backup

- node_modules/ (frontend dependencies - executar \`npm install\`)
- venv/ (Python virtual env - criar novo)
- __pycache__/ (Python cache)
- staticfiles/ (gerado por collectstatic)
- media/ (uploads de usuários)
- logs/ (arquivos de log)
- *.sqlite3 (bancos de dados SQLite temporários)
- .git/ (histórico Git - disponível no GitHub)

---

**Hash do Commit**: $(git rev-parse HEAD 2>$null)
**Gerado por**: create_backup.ps1
"@

Set-Content -Path "$backupDir\BACKUP_INFO.md" -Value $infoContent -Encoding UTF8

# Criar requirements.txt consolidado
Write-Host "[4/5] Gerando lista de dependências..." -ForegroundColor Yellow
if (Test-Path "backend\requirements.txt") {
    Copy-Item "backend\requirements.txt" "$backupDir\REQUIREMENTS_BACKEND.txt"
}
if (Test-Path "frontend\package.json") {
    Copy-Item "frontend\package.json" "$backupDir\REQUIREMENTS_FRONTEND.json"
}

# Comprimir em ZIP
Write-Host "[5/5] Comprimindo backup..." -ForegroundColor Yellow
Compress-Archive -Path $backupDir -DestinationPath $zipFile -Force

# Remover diretório temporário
Remove-Item -Path $backupDir -Recurse -Force

# Calcular tamanho do arquivo
$fileSize = (Get-Item $zipFile).Length
$fileSizeMB = [math]::Round($fileSize / 1MB, 2)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Backup Criado com Sucesso!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Arquivo: $zipFile" -ForegroundColor Cyan
Write-Host "Tamanho: ${fileSizeMB} MB" -ForegroundColor Cyan
$currentDate = Get-Date -Format "dd/MM/yyyy HH:mm:ss"
Write-Host "Data: $currentDate" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pronto para distribuicao e testes!" -ForegroundColor Green
Write-Host ""
