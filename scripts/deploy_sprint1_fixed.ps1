# Sprint 1 Deployment Script (Windows PowerShell)
# Automates deployment steps from SPRINT1_DEPLOYMENT_EXECUTION.md

param(
    [switch]$SkipTests = $false,
    [switch]$SkipBackup = $false,
    [switch]$DryRun = $false,
    [string]$Environment = "staging"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

# Colors for output
function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n[STEP] $Message" -ForegroundColor Magenta
}

# Configuration
$ProjectRoot = "D:\provemaps_beta"
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackupDir = Join-Path $ProjectRoot "backups"
$LogsDir = Join-Path $ProjectRoot "logs"
$DeploymentLog = Join-Path $LogsDir "deployment_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Ensure logs directory exists
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

# Start logging
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Out-File -Append -FilePath $DeploymentLog
    Write-Host $Message
}

Write-Step "Sprint 1 Deployment Script"
Write-Info "Environment: $Environment"
Write-Info "Dry Run: $DryRun"
Write-Info "Log File: $DeploymentLog"
Write-Log "Deployment started"

# Step 0: Pre-flight checks
Write-Step "Step 0: Pre-flight Checks"

if (-not (Test-Path $BackendDir)) {
    Write-Err "Backend directory not found: $BackendDir"
    exit 1
}

if (-not (Test-Path $FrontendDir)) {
    Write-Err "Frontend directory not found: $FrontendDir"
    exit 1
}

Write-Success "Project directories found"

# Step 1: Run Tests
if (-not $SkipTests) {
    Write-Step "Step 1: Running Tests"
    
    # Backend tests
    Write-Info "Running backend tests..."
    Push-Location $BackendDir
    try {
        if (-not $DryRun) {
            $testResult = python -m pytest -q --tb=line 2>&1 | Out-String
            Write-Log "Backend tests output: $testResult"
            
            if ($LASTEXITCODE -ne 0) {
                Write-Err "Backend tests failed! Aborting deployment."
                Pop-Location
                exit 1
            }
            Write-Success "Backend tests passed"
        } else {
            Write-Info "[DRY-RUN] Would run backend tests"
        }
    } finally {
        Pop-Location
    }
    
    # Frontend tests
    Write-Info "Running frontend tests..."
    Push-Location $FrontendDir
    try {
        if (-not $DryRun) {
            $testResult = npm run test:unit 2>&1 | Out-String
            Write-Log "Frontend tests output: $testResult"
            
            if ($LASTEXITCODE -ne 0) {
                Write-Err "Frontend tests failed! Aborting deployment."
                Pop-Location
                exit 1
            }
            Write-Success "Frontend tests passed"
        } else {
            Write-Info "[DRY-RUN] Would run frontend tests"
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Warn "Skipping tests (-SkipTests flag)"
}

# Step 2: Create Backups
if (-not $SkipBackup) {
    Write-Step "Step 2: Creating Backups"
    
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir | Out-Null
        Write-Info "Created backup directory: $BackupDir"
    }
    
    $BackupTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    
    # Database backup (SQLite)
    $DbPath = Join-Path $ProjectRoot "database\db.sqlite3"
    if (Test-Path $DbPath) {
        $DbBackup = Join-Path $BackupDir "db_$BackupTimestamp.sqlite3"
        if (-not $DryRun) {
            Copy-Item $DbPath $DbBackup
            Write-Success "Database backed up: $DbBackup"
            Write-Log "Database backup: $DbBackup"
        } else {
            Write-Info "[DRY-RUN] Would backup database to $DbBackup"
        }
    } else {
        Write-Warn "Database not found at $DbPath (skipping)"
    }
    
    # Static files backup
    $StaticDir = Join-Path $BackendDir "staticfiles"
    if (Test-Path $StaticDir) {
        $StaticBackup = Join-Path $BackupDir "static_$BackupTimestamp.zip"
        if (-not $DryRun) {
            Compress-Archive -Path $StaticDir -DestinationPath $StaticBackup -Force
            Write-Success "Static files backed up: $StaticBackup"
            Write-Log "Static files backup: $StaticBackup"
        } else {
            Write-Info "[DRY-RUN] Would backup static files to $StaticBackup"
        }
    }
    
    # Frontend build backup
    $FrontendBuildDir = Join-Path $BackendDir "staticfiles\vue-spa"
    if (Test-Path $FrontendBuildDir) {
        $FrontendBackup = Join-Path $BackupDir "frontend_$BackupTimestamp.zip"
        if (-not $DryRun) {
            Compress-Archive -Path $FrontendBuildDir -DestinationPath $FrontendBackup -Force
            Write-Success "Frontend build backed up: $FrontendBackup"
            Write-Log "Frontend build backup: $FrontendBackup"
        } else {
            Write-Info "[DRY-RUN] Would backup frontend build to $FrontendBackup"
        }
    }
} else {
    Write-Warn "Skipping backups (-SkipBackup flag)"
}

# Step 3: Frontend Build
Write-Step "Step 3: Building Frontend"

Push-Location $FrontendDir
try {
    # Install dependencies
    Write-Info "Installing frontend dependencies..."
    if (-not $DryRun) {
        $npmOutput = npm ci 2>&1 | Out-String
        Write-Log "npm ci output: $npmOutput"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Err "npm ci failed!"
            Pop-Location
            exit 1
        }
        Write-Success "Dependencies installed"
    } else {
        Write-Info "[DRY-RUN] Would run npm ci"
    }
    
    # Build
    Write-Info "Building frontend for production..."
    if (-not $DryRun) {
        $buildOutput = npm run build 2>&1 | Out-String
        Write-Log "Frontend build output: $buildOutput"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Frontend build failed!"
            Pop-Location
            exit 1
        }
        
        # Check bundle size
        $mainJs = Join-Path $BackendDir "staticfiles\vue-spa\assets\main.js"
        if (Test-Path $mainJs) {
            $size = (Get-Item $mainJs).Length / 1KB
            $sizeRounded = [math]::Round($size, 2)
            Write-Info "main.js size: $sizeRounded KB"
            
            if ($size -gt 150) {  # ~150KB uncompressed (~50KB gzipped)
                Write-Warn "Bundle size larger than expected: $sizeRounded KB"
            } else {
                Write-Success "Bundle size OK: $sizeRounded KB"
            }
        }
        
        Write-Success "Frontend built successfully"
    } else {
        Write-Info "[DRY-RUN] Would run npm run build"
    }
} finally {
    Pop-Location
}

# Step 4: Backend Deployment
Write-Step "Step 4: Backend Deployment"

Push-Location $BackendDir
try {
    # Check for virtual environment
    $VenvPath = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
    if (-not (Test-Path $VenvPath)) {
        Write-Warn "Virtual environment not found at $VenvPath"
        Write-Info "Creating virtual environment..."
        if (-not $DryRun) {
            python -m venv venv
            Write-Success "Virtual environment created"
        }
    }
    
    # Install backend dependencies
    Write-Info "Installing backend dependencies..."
    if (-not $DryRun) {
        $pipOutput = python -m pip install -r requirements.txt 2>&1 | Out-String
        Write-Log "pip install output: $pipOutput"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Err "pip install failed!"
            Pop-Location
            exit 1
        }
        Write-Success "Dependencies installed"
    } else {
        Write-Info "[DRY-RUN] Would run pip install"
    }
    
    # Collect static files
    Write-Info "Collecting static files..."
    if (-not $DryRun) {
        $collectOutput = python manage.py collectstatic --noinput --clear 2>&1 | Out-String
        Write-Log "collectstatic output: $collectOutput"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Err "collectstatic failed!"
            Pop-Location
            exit 1
        }
        Write-Success "Static files collected (with STATIC_ASSET_VERSION)"
        Write-Log "Static files collected successfully"
    } else {
        Write-Info "[DRY-RUN] Would run collectstatic"
    }
} finally {
    Pop-Location
}

# Step 5: Health Checks
Write-Step "Step 5: Health Checks Required"

Write-Info "Automated health checks complete. Manual verification required:"
Write-Info "  1. Start development server: python manage.py runserver"
Write-Info "  2. Open browser: http://localhost:8000"
Write-Info "  3. Check browser console for errors"
Write-Info "  4. Verify filters and search work"
Write-Info "  5. See SPRINT1_DEPLOYMENT_EXECUTION.md Step 5 for details"

# Step 6: Deployment Summary
Write-Step "Deployment Summary"

Write-Success "Local deployment preparation completed successfully!"
Write-Info ""
Write-Info "Files deployed to:"
Write-Info "  - Backend: $BackendDir"
Write-Info "  - Frontend build: $BackendDir\staticfiles\vue-spa"
Write-Info "  - Static files: $BackendDir\staticfiles"
Write-Info ""
Write-Info "Next Steps:"
Write-Info "  1. Start server: cd backend; python manage.py runserver"
Write-Info "  2. Run health checks (see Step 5 above)"
Write-Info "  3. Run smoke tests (see SPRINT1_DEPLOYMENT_EXECUTION.md Step 6)"
Write-Info "  4. Execute full QA (see SPRINT1_QA_CHECKLIST.md)"
Write-Info ""

if (-not $SkipBackup) {
    Write-Info "Rollback Information:"
    Write-Info "  - Backup location: $BackupDir"
    Write-Info "  - Database: db_$BackupTimestamp.sqlite3"
    Write-Info "  - Static files: static_$BackupTimestamp.zip"
    Write-Info "  - Frontend: frontend_$BackupTimestamp.zip"
    Write-Info "  - Rollback guide: doc\operations\SPRINT1_ROLLBACK_PLAN.md"
    Write-Info ""
}

Write-Log "Deployment preparation completed successfully"
Write-Success "Deployment script finished!"

exit 0
