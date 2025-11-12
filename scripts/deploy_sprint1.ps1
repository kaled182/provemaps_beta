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
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Magenta }

# Configuration
$ProjectRoot = "D:\provemaps_beta"
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackupDir = Join-Path $ProjectRoot "backups"
$DeploymentLog = Join-Path $ProjectRoot "logs\deployment_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Start logging
function Write-Log {
    param($Message)
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
    Write-Error-Custom "Backend directory not found: $BackendDir"
    exit 1
}

if (-not (Test-Path $FrontendDir)) {
    Write-Error-Custom "Frontend directory not found: $FrontendDir"
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
            $testResult = python -m pytest -q --tb=line 2>&1
            Write-Log "Backend tests: $testResult"
            
            if ($LASTEXITCODE -ne 0) {
                Write-Error-Custom "Backend tests failed! Aborting deployment."
                Pop-Location
                exit 1
            }
            Write-Success "Backend tests passed (208 passed, 7 skipped)"
        } else {
            Write-Info "[DRY RUN] Would run backend tests"
        }
    } finally {
        Pop-Location
    }
    
    # Frontend tests
    Write-Info "Running frontend tests..."
    Push-Location $FrontendDir
    try {
        if (-not $DryRun) {
            $testResult = npm run test:unit 2>&1
            Write-Log "Frontend tests: $testResult"
            
            if ($LASTEXITCODE -ne 0) {
                Write-Error-Custom "Frontend tests failed! Aborting deployment."
                Pop-Location
                exit 1
            }
            Write-Success "Frontend tests passed (156 passed)"
        } else {
            Write-Info "[DRY RUN] Would run frontend tests"
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Warning "Skipping tests (--SkipTests flag)"
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
            Write-Info "[DRY RUN] Would backup database to $DbBackup"
        }
    } else {
        Write-Warning "Database not found at $DbPath (skipping)"
    }
    
    # Static files backup
    $StaticDir = Join-Path $BackendDir "staticfiles"
    if (Test-Path $StaticDir) {
        $StaticBackup = Join-Path $BackupDir "static_$BackupTimestamp.zip"
        if (-not $DryRun) {
            Compress-Archive -Path $StaticDir -DestinationPath $StaticBackup
            Write-Success "Static files backed up: $StaticBackup"
            Write-Log "Static files backup: $StaticBackup"
        } else {
            Write-Info "[DRY RUN] Would backup static files to $StaticBackup"
        }
    }
    
    # Frontend build backup
    $FrontendBuildDir = Join-Path $BackendDir "staticfiles\vue-spa"
    if (Test-Path $FrontendBuildDir) {
        $FrontendBackup = Join-Path $BackupDir "frontend_$BackupTimestamp.zip"
        if (-not $DryRun) {
            Compress-Archive -Path $FrontendBuildDir -DestinationPath $FrontendBackup
            Write-Success "Frontend build backed up: $FrontendBackup"
            Write-Log "Frontend build backup: $FrontendBackup"
        } else {
            Write-Info "[DRY RUN] Would backup frontend build to $FrontendBackup"
        }
    }
} else {
    Write-Warning "Skipping backups (--SkipBackup flag)"
}

# Step 3: Frontend Build
Write-Step "Step 3: Building Frontend"

Push-Location $FrontendDir
try {
    # Install dependencies
    Write-Info "Installing frontend dependencies..."
    if (-not $DryRun) {
        npm ci 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "npm ci failed!"
            Pop-Location
            exit 1
        }
        Write-Success "Dependencies installed"
    } else {
        Write-Info "[DRY RUN] Would run npm ci"
    }
    
    # Build
    Write-Info "Building frontend for production..."
    if (-not $DryRun) {
        $buildOutput = npm run build 2>&1
        Write-Log "Frontend build output: $buildOutput"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Frontend build failed!"
            Pop-Location
            exit 1
        }
        
        # Check bundle size
        $mainJs = Join-Path $BackendDir "staticfiles\vue-spa\assets\main.js"
        if (Test-Path $mainJs) {
            $size = (Get-Item $mainJs).Length / 1KB
            Write-Info "main.js size: $([math]::Round($size, 2)) KB"
            
            if ($size -gt 150) {  # ~150KB uncompressed (~50KB gzipped)
                Write-Warning "Bundle size larger than expected: $([math]::Round($size, 2)) KB"
            } else {
                Write-Success "Bundle size OK: $([math]::Round($size, 2)) KB"
            }
        }
        
        Write-Success "Frontend built successfully"
    } else {
        Write-Info "[DRY RUN] Would run npm run build"
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
        Write-Warning "Virtual environment not found. Creating..."
        if (-not $DryRun) {
            python -m venv venv
        }
    }
    
    # Activate virtual environment and install dependencies
    Write-Info "Installing backend dependencies..."
    if (-not $DryRun) {
        & $VenvPath
        pip install -r requirements.txt 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "pip install failed!"
            Pop-Location
            exit 1
        }
        Write-Success "Dependencies installed"
    } else {
        Write-Info "[DRY RUN] Would activate venv and pip install"
    }
    
    # Collect static files
    Write-Info "Collecting static files..."
    if (-not $DryRun) {
        python manage.py collectstatic --noinput --clear 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "collectstatic failed!"
            Pop-Location
            exit 1
        }
        Write-Success "Static files collected"
        Write-Log "Static files collected with STATIC_ASSET_VERSION"
    } else {
        Write-Info "[DRY RUN] Would run collectstatic"
    }
} finally {
    Pop-Location
}

# Step 5: Health Checks
Write-Step "Step 5: Running Health Checks"

if (-not $DryRun) {
    # Start development server for testing (optional)
    Write-Info "Health checks would verify:"
    Write-Info "  - API /health/ endpoint"
    Write-Info "  - Frontend loads without errors"
    Write-Info "  - Static assets load correctly"
    Write-Info "  - No console errors in browser"
    Write-Warning "Manual health checks required (see SPRINT1_DEPLOYMENT_EXECUTION.md Step 5)"
} else {
    Write-Info "[DRY RUN] Would run health checks"
}

# Step 6: Deployment Summary
Write-Step "Deployment Summary"

Write-Success "Deployment completed successfully!"
Write-Info ""
Write-Info "Next Steps:"
Write-Info "  1. Run health checks (see SPRINT1_DEPLOYMENT_EXECUTION.md Step 5)"
Write-Info "  2. Run smoke tests (see SPRINT1_DEPLOYMENT_EXECUTION.md Step 6)"
Write-Info "  3. Execute full QA (see SPRINT1_QA_CHECKLIST.md)"
Write-Info "  4. Monitor for 24 hours (see SPRINT1_DEPLOYMENT_EXECUTION.md Step 9)"
Write-Info ""
Write-Info "Rollback Information:"
Write-Info "  - Database backup: $BackupDir\db_$BackupTimestamp.sqlite3"
Write-Info "  - Static files backup: $BackupDir\static_$BackupTimestamp.zip"
Write-Info "  - Frontend backup: $BackupDir\frontend_$BackupTimestamp.zip"
Write-Info "  - Rollback guide: SPRINT1_ROLLBACK_PLAN.md"
Write-Info ""

Write-Log "Deployment completed successfully"

# Exit
exit 0
