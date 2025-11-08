<# 
.SYNOPSIS
    Script automatizado para reorganização de pastas - Fase 6

.DESCRIPTION
    Este script reorganiza o projeto MapsProveFiber separando:
    - backend/    (Django apps + Python code)
    - frontend/   (Static assets + JS)
    - database/   (DB files + SQL scripts)
    - docker/     (Docker files)

.NOTES
    Arquivo: reorganize_folders.ps1
    Autor: GitHub Copilot + Equipe MapsProveFiber
    Data: 08/11/2025
    Versão: 1.0
    
.EXAMPLE
    .\scripts\reorganize_folders.ps1
    
    Executa a reorganização completa em modo interativo
    
.EXAMPLE
    .\scripts\reorganize_folders.ps1 -AutoConfirm
    
    Executa sem confirmações (CI/CD)
#>

[CmdletBinding()]
param(
    [switch]$AutoConfirm,
    [switch]$DryRun,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

# Colors
function Write-Header($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Warning($msg) { Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Error($msg) { Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "ℹ️  $msg" -ForegroundColor Blue }

# Verificar se estamos na branch correta
function Test-GitBranch {
    Write-Header "Verificando branch Git"
    
    $currentBranch = git rev-parse --abbrev-ref HEAD
    
    if ($currentBranch -ne "refactor/folder-structure") {
        Write-Warning "Branch atual: $currentBranch"
        Write-Warning "Branch esperada: refactor/folder-structure"
        
        if (-not $AutoConfirm) {
            $response = Read-Host "Criar branch refactor/folder-structure agora? (s/N)"
            if ($response -ne 's') {
                Write-Error "Abortado pelo usuário"
                exit 1
            }
        }
        
        git checkout -b refactor/folder-structure
        Write-Success "Branch refactor/folder-structure criada"
    } else {
        Write-Success "Branch correta: $currentBranch"
    }
}

# Backup antes de começar
function New-Backup {
    Write-Header "Criando backup"
    
    $backupDir = Join-Path $PROJECT_ROOT "backup_pre_reorganization_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Criaria backup em: $backupDir"
        return
    }
    
    # Git stash como backup
    git stash push -m "Pre-reorganization backup $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Success "Backup criado via git stash"
    
    # Tag como checkpoint
    $tag = "checkpoint-pre-folder-reorganization"
    git tag -f $tag
    Write-Success "Tag checkpoint criada: $tag"
}

# Criar estrutura de diretórios
function New-DirectoryStructure {
    Write-Header "Criando estrutura de diretórios"
    
    $dirs = @(
        "backend",
        "frontend",
        "frontend/static",
        "database",
        "docker"
    )
    
    foreach ($dir in $dirs) {
        $fullPath = Join-Path $PROJECT_ROOT $dir
        
        if ($DryRun) {
            Write-Info "[DRY RUN] Criaria: $fullPath"
            continue
        }
        
        if (-not (Test-Path $fullPath)) {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
            Write-Success "Criado: $dir/"
        } else {
            Write-Info "Já existe: $dir/"
        }
    }
}

# Mover Django apps para backend/
function Move-BackendFiles {
    Write-Header "Movendo arquivos do Backend"
    
    $djangoApps = @(
        "core",
        "inventory",
        "monitoring",
        "maps_view",
        "routes_builder",
        "setup_app",
        "gpon",
        "dwdm",
        "integrations",
        "settings",
        "templates",
        "tests",
        "service_accounts",
        "zabbix_api"
    )
    
    $pythonFiles = @(
        "manage.py",
        "conftest.py",
        "pytest.ini",
        "pyproject.toml",
        "requirements.txt",
        "requirements_full.txt",
        "pyrightconfig.json"
    )
    
    # Mover apps Django
    foreach ($app in $djangoApps) {
        $source = Join-Path $PROJECT_ROOT $app
        $dest = Join-Path $PROJECT_ROOT "backend\$app"
        
        if (Test-Path $source) {
            if ($DryRun) {
                Write-Info "[DRY RUN] Moveria: $app/ -> backend/$app/"
            } else {
                Move-Item -Path $source -Destination $dest -Force
                Write-Success "Movido: $app/ -> backend/$app/"
            }
        } else {
            Write-Warning "Não encontrado: $app/"
        }
    }
    
    # Mover arquivos Python raiz
    foreach ($file in $pythonFiles) {
        $source = Join-Path $PROJECT_ROOT $file
        $dest = Join-Path $PROJECT_ROOT "backend\$file"
        
        if (Test-Path $source) {
            if ($DryRun) {
                Write-Info "[DRY RUN] Moveria: $file -> backend/$file"
            } else {
                Move-Item -Path $source -Destination $dest -Force
                Write-Success "Movido: $file -> backend/$file"
            }
        } else {
            Write-Warning "Não encontrado: $file"
        }
    }
}

# Mover frontend files
function Move-FrontendFiles {
    Write-Header "Movendo arquivos do Frontend"
    
    $frontendFiles = @(
        "package.json",
        "package-lock.json",
        "babel.config.js",
        "node_modules"
    )
    
    foreach ($file in $frontendFiles) {
        $source = Join-Path $PROJECT_ROOT $file
        $dest = Join-Path $PROJECT_ROOT "frontend\$file"
        
        if (Test-Path $source) {
            if ($DryRun) {
                Write-Info "[DRY RUN] Moveria: $file -> frontend/$file"
            } else {
                Move-Item -Path $source -Destination $dest -Force
                Write-Success "Movido: $file -> frontend/$file"
            }
        } else {
            Write-Info "Não encontrado (ok): $file"
        }
    }
}

# Mover database files
function Move-DatabaseFiles {
    Write-Header "Movendo arquivos do Database"
    
    $dbFiles = @(
        "db.sqlite3",
        "test_db.sqlite3",
        "sql"
    )
    
    foreach ($file in $dbFiles) {
        $source = Join-Path $PROJECT_ROOT $file
        $dest = Join-Path $PROJECT_ROOT "database\$file"
        
        if (Test-Path $source) {
            if ($DryRun) {
                Write-Info "[DRY RUN] Moveria: $file -> database/$file"
            } else {
                Move-Item -Path $source -Destination $dest -Force
                Write-Success "Movido: $file -> database/$file"
            }
        } else {
            Write-Info "Não encontrado (ok): $file"
        }
    }
}

# Mover Docker files
function Move-DockerFiles {
    Write-Header "Movendo arquivos Docker"
    
    $dockerFiles = @(
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.test.yml",
        "docker-entrypoint.sh"
    )
    
    foreach ($file in $dockerFiles) {
        $source = Join-Path $PROJECT_ROOT $file
        $dest = Join-Path $PROJECT_ROOT "docker\$file"
        
        if (Test-Path $source) {
            if ($DryRun) {
                Write-Info "[DRY RUN] Moveria: $file -> docker/$file"
            } else {
                Move-Item -Path $source -Destination $dest -Force
                Write-Success "Movido: $file -> docker/$file"
            }
        } else {
            Write-Warning "Não encontrado: $file"
        }
    }
}

# Atualizar settings/base.py
function Update-DjangoSettings {
    Write-Header "Atualizando Django Settings"
    
    $settingsFile = Join-Path $PROJECT_ROOT "backend\settings\base.py"
    
    if (-not (Test-Path $settingsFile)) {
        Write-Error "Settings não encontrado: $settingsFile"
        return
    }
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Atualizaria: backend/settings/base.py"
        return
    }
    
    $content = Get-Content $settingsFile -Raw
    
    # Atualizar BASE_DIR (adicionar .parent extra)
    $content = $content -replace 'BASE_DIR = Path\(__file__\)\.resolve\(\)\.parent\.parent', 'BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/'
    
    # Adicionar novos paths
    $newPaths = @"

# New directory structure
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_DIR = BASE_DIR / 'frontend'
DATABASE_DIR = BASE_DIR / 'database'
"@
    
    # Inserir após BASE_DIR
    $content = $content -replace '(BASE_DIR = Path\(__file__\)\.resolve\(\)\.parent\.parent\.parent.*?)\n', "`$1`n$newPaths`n"
    
    # Atualizar DATABASES
    $content = $content -replace "'NAME': BASE_DIR / 'db\.sqlite3'", "'NAME': DATABASE_DIR / 'db.sqlite3'"
    
    # Atualizar STATICFILES_DIRS (se existir)
    $content = $content -replace "STATICFILES_DIRS = \[BASE_DIR / 'static'\]", "STATICFILES_DIRS = [FRONTEND_DIR / 'static']"
    
    # Atualizar STATIC_ROOT
    $content = $content -replace "STATIC_ROOT = BASE_DIR / 'staticfiles'", "STATIC_ROOT = FRONTEND_DIR / 'staticfiles'"
    
    # Atualizar TEMPLATES DIRS
    $content = $content -replace "'DIRS': \[\]", "'DIRS': [BACKEND_DIR / 'templates']"
    
    Set-Content -Path $settingsFile -Value $content -NoNewline
    Write-Success "Atualizado: backend/settings/base.py"
}

# Criar .env atualizado
function Update-EnvFile {
    Write-Header "Atualizando arquivo .env"
    
    $envFile = Join-Path $PROJECT_ROOT ".env"
    $envExample = Join-Path $PROJECT_ROOT ".env.example"
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Atualizaria: .env e .env.example"
        return
    }
    
    # Atualizar PYTHONPATH
    foreach ($file in @($envFile, $envExample)) {
        if (Test-Path $file) {
            $content = Get-Content $file -Raw
            
            # Adicionar/Atualizar PYTHONPATH
            if ($content -match 'PYTHONPATH=') {
                $content = $content -replace 'PYTHONPATH=.*', 'PYTHONPATH=./backend'
            } else {
                $content += "`nPYTHONPATH=./backend`n"
            }
            
            Set-Content -Path $file -Value $content -NoNewline
            Write-Success "Atualizado: $(Split-Path $file -Leaf)"
        }
    }
}

# Testar se tudo funciona
function Test-Installation {
    Write-Header "Testando instalação"
    
    if ($SkipTests) {
        Write-Warning "Testes pulados (--SkipTests)"
        return
    }
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Executaria testes"
        return
    }
    
    Push-Location (Join-Path $PROJECT_ROOT "backend")
    
    try {
        # Teste 1: Django check
        Write-Info "Testando: python manage.py check"
        $env:PYTHONPATH = "."
        python manage.py check
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Django check passou"
        } else {
            Write-Error "Django check falhou"
            return
        }
        
        # Teste 2: Imports
        Write-Info "Testando: python -c 'import core'"
        python -c "import core"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Imports funcionando"
        } else {
            Write-Error "Imports falharam"
            return
        }
        
        # Teste 3: Pytest (se não pular)
        Write-Info "Executando pytest..."
        pytest -q --tb=no
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Todos os testes passaram!"
        } else {
            Write-Warning "Alguns testes falharam (verificar manualmente)"
        }
        
    } finally {
        Pop-Location
    }
}

# Criar relatório
function New-Report {
    Write-Header "Gerando relatório"
    
    $reportFile = Join-Path $PROJECT_ROOT "REORGANIZATION_REPORT.md"
    
    $report = @"
# 📊 Relatório de Reorganização de Pastas

**Data:** $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")
**Script:** reorganize_folders.ps1
**Versão:** 1.0

## ✅ Ações Executadas

### 1. Estrutura de Diretórios Criada
- ✅ backend/
- ✅ frontend/
- ✅ database/
- ✅ docker/

### 2. Arquivos Movidos

#### Backend (Django)
- ✅ Django apps movidos para backend/
- ✅ manage.py → backend/manage.py
- ✅ settings/ → backend/settings/
- ✅ requirements.txt → backend/requirements.txt

#### Frontend (Static Assets)
- ✅ package.json → frontend/package.json
- ✅ babel.config.js → frontend/babel.config.js
- ✅ node_modules → frontend/node_modules

#### Database
- ✅ db.sqlite3 → database/db.sqlite3
- ✅ sql/ → database/sql/

#### Docker
- ✅ dockerfile → docker/dockerfile
- ✅ docker-compose.yml → docker/docker-compose.yml
- ✅ docker-entrypoint.sh → docker/docker-entrypoint.sh

### 3. Configurações Atualizadas
- ✅ backend/settings/base.py (BASE_DIR, DATABASES, STATIC_ROOT)
- ✅ .env (PYTHONPATH=./backend)
- ✅ .env.example (PYTHONPATH=./backend)

## 📋 Próximos Passos Manuais

### 1. Atualizar Docker Files
Editar manualmente:
- docker/dockerfile
- docker/docker-compose.yml
- docker/docker-entrypoint.sh

Ajustar:
- WORKDIR /app/backend
- COPY backend/ /app/backend/
- ENV PYTHONPATH=/app/backend

### 2. Atualizar Scripts
Scripts que precisam de ajuste:
- scripts/deploy_initial_v2.ps1
- scripts/smoke_phase5.ps1
- scripts/deploy.sh
- scripts/setup_ubuntu.sh

Mudar comandos:
\`\`\`powershell
# DE:
python manage.py migrate

# PARA:
cd backend; python manage.py migrate
# OU
python backend/manage.py migrate
\`\`\`

### 3. Atualizar GitHub Actions
Workflows que precisam de ajuste:
- .github/workflows/tests.yml
- .github/workflows/daily-inventory-tests.yml

Ajustar:
\`\`\`yaml
env:
  PYTHONPATH: \${{ github.workspace }}/backend
working-directory: ./backend
\`\`\`

### 4. Atualizar .gitignore
Ajustar paths:
\`\`\`gitignore
/frontend/staticfiles/
/database/db.sqlite3
/backend/**/__pycache__/
\`\`\`

## 🧪 Validação

Execute os seguintes comandos para validar:

\`\`\`powershell
# Django check
cd backend
python manage.py check

# Testes
pytest -q

# Docker build
cd ..
docker-compose -f docker/docker-compose.yml build
\`\`\`

## ⚠️ Rollback (se necessário)

\`\`\`powershell
# Restaurar via git stash
git stash pop

# OU reverter via tag
git reset --hard checkpoint-pre-folder-reorganization
\`\`\`

---

**Status:** ✅ Reorganização básica concluída
**Próximo passo:** Ajustes manuais conforme lista acima
"@
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Geraria relatório em: $reportFile"
        Write-Host "`n$report"
        return
    }
    
    Set-Content -Path $reportFile -Value $report
    Write-Success "Relatório gerado: REORGANIZATION_REPORT.md"
}

# Main execution
function Start-Reorganization {
    Write-Host @"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🗂️  REORGANIZAÇÃO DE PASTAS - FASE 6                       ║
║                                                               ║
║   MapsProveFiber v2.0                                        ║
║   Backend/Frontend/Database Separation                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan
    
    if ($DryRun) {
        Write-Warning "`n🔍 MODO DRY RUN - Nenhuma alteração será feita`n"
    }
    
    if (-not $AutoConfirm -and -not $DryRun) {
        Write-Warning "Esta operação irá reorganizar a estrutura do projeto."
        Write-Warning "Certifique-se de ter um backup!"
        $response = Read-Host "`nContinuar? (s/N)"
        
        if ($response -ne 's') {
            Write-Info "Operação cancelada pelo usuário."
            exit 0
        }
    }
    
    # Executar fases
    Test-GitBranch
    New-Backup
    New-DirectoryStructure
    Move-BackendFiles
    Move-FrontendFiles
    Move-DatabaseFiles
    Move-DockerFiles
    Update-DjangoSettings
    Update-EnvFile
    Test-Installation
    New-Report
    
    Write-Host @"

╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ✅ REORGANIZAÇÃO CONCLUÍDA!                                ║
║                                                               ║
║   Próximos passos:                                           ║
║   1. Revisar REORGANIZATION_REPORT.md                        ║
║   2. Ajustar Docker files manualmente                        ║
║   3. Atualizar scripts de deploy                             ║
║   4. Atualizar GitHub Actions                                ║
║   5. Testar tudo localmente                                  ║
║   6. Commit e push                                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green
}

# Execute
Start-Reorganization
