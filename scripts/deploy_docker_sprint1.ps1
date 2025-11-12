# Sprint 1 Docker Deployment Script
# Builds and deploys Sprint 1 with frontend included

param(
    [switch]$NoBuild = $false,
    [switch]$NoCache = $false,
    [string]$Environment = "development"
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { param([string]$msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Info { param([string]$msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn { param([string]$msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param([string]$msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Step { param([string]$msg) Write-Host "`n[STEP] $msg" -ForegroundColor Magenta }

$ProjectRoot = "D:\provemaps_beta"
$DockerComposeFile = Join-Path $ProjectRoot "docker\docker-compose.yml"
$LogFile = Join-Path $ProjectRoot "logs\docker_deployment_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Ensure logs directory
$LogsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Out-File -Append -FilePath $LogFile
}

Write-Step "Sprint 1 Docker Deployment"
Write-Info "Environment: $Environment"
Write-Info "Log: $LogFile"
Write-Log "Docker deployment started"

# Check Docker is running
Write-Step "Checking Docker"
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Success "Docker version: $dockerVersion"
    Write-Log "Docker version: $dockerVersion"
} catch {
    Write-Err "Docker is not running. Please start Docker Desktop."
    exit 1
}

# Check docker-compose file exists
if (-not (Test-Path $DockerComposeFile)) {
    Write-Err "docker-compose.yml not found at $DockerComposeFile"
    exit 1
}

# Stop existing containers
Write-Step "Stopping existing containers"
Push-Location $ProjectRoot
try {
    docker compose -f docker/docker-compose.yml down 2>&1 | Out-String | Write-Log
    Write-Success "Containers stopped"
} catch {
    Write-Warn "Error stopping containers (may not be running): $_"
}
Pop-Location

# Build images
if (-not $NoBuild) {
    Write-Step "Building Docker images (with frontend)"
    
    $buildArgs = @(
        "compose",
        "-f", "docker/docker-compose.yml",
        "build"
    )
    
    if ($NoCache) {
        $buildArgs += "--no-cache"
        Write-Info "Building without cache"
    }
    
    Push-Location $ProjectRoot
    try {
        Write-Info "This may take 5-10 minutes (includes npm install and build)..."
        $buildOutput = & docker $buildArgs 2>&1 | Out-String
        Write-Log "Build output: $buildOutput"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Docker build failed!"
            Write-Err $buildOutput
            Pop-Location
            exit 1
        }
        
        Write-Success "Docker images built successfully"
    } finally {
        Pop-Location
    }
} else {
    Write-Warn "Skipping build (-NoBuild flag)"
}

# Start containers
Write-Step "Starting containers"
Push-Location $ProjectRoot
try {
    $upOutput = docker compose -f docker/docker-compose.yml up -d 2>&1 | Out-String
    Write-Log "Up output: $upOutput"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to start containers!"
        Write-Err $upOutput
        Pop-Location
        exit 1
    }
    
    Write-Success "Containers started"
} finally {
    Pop-Location
}

# Wait for services to be healthy
Write-Step "Waiting for services to become healthy"
Write-Info "Waiting 30 seconds for initialization..."
Start-Sleep -Seconds 30

# Check container status
Write-Info "Checking container status..."
Push-Location $ProjectRoot
try {
    $psOutput = docker compose -f docker/docker-compose.yml ps
    Write-Log "Container status: $psOutput"
    Write-Host $psOutput
} finally {
    Pop-Location
}

# Health checks
Write-Step "Running health checks"

Start-Sleep -Seconds 5

try {
    Write-Info "Checking web service health..."
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/healthz" -TimeoutSec 10 -UseBasicParsing
    $healthJson = $healthResponse.Content | ConvertFrom-Json
    
    if ($healthJson.status -eq "healthy" -or $healthJson.status -eq "degraded") {
        Write-Success "Web service is $($healthJson.status)"
        Write-Info "Django version: $($healthJson.django)"
        Write-Info "Python version: $($healthJson.python)"
    } else {
        Write-Warn "Health check returned status: $($healthJson.status)"
    }
} catch {
    Write-Warn "Health check failed (service may still be starting): $_"
    Write-Info "Check logs with: docker compose -f docker/docker-compose.yml logs web"
}

# Check frontend assets
Write-Step "Verifying frontend deployment"
try {
    Write-Info "Checking dashboard endpoint..."
    $dashboardResponse = Invoke-WebRequest -Uri "http://localhost:8000/maps_view/dashboard/" -TimeoutSec 10 -UseBasicParsing -MaximumRedirection 0
    Write-Success "Dashboard endpoint responding (HTTP $($dashboardResponse.StatusCode))"
} catch {
    if ($_.Exception.Response.StatusCode -eq 302) {
        Write-Success "Dashboard redirects (login required - expected)"
    } else {
        Write-Warn "Dashboard check: $_"
    }
}

# Show logs
Write-Step "Recent container logs"
Write-Info "Web service logs (last 20 lines):"
Push-Location $ProjectRoot
try {
    docker compose -f docker/docker-compose.yml logs --tail=20 web
} finally {
    Pop-Location
}

# Summary
Write-Step "Deployment Summary"
Write-Success "Docker deployment completed!"
Write-Info ""
Write-Info "Services:"
Write-Info "  - Web:      http://localhost:8000"
Write-Info "  - Dashboard: http://localhost:8000/maps_view/dashboard/"
Write-Info "  - Health:   http://localhost:8000/healthz"
Write-Info "  - Admin:    http://localhost:8000/admin/"
Write-Info ""
Write-Info "Useful commands:"
Write-Info "  View logs:      docker compose -f docker/docker-compose.yml logs -f web"
Write-Info "  View all logs:  docker compose -f docker/docker-compose.yml logs -f"
Write-Info "  Restart:        docker compose -f docker/docker-compose.yml restart"
Write-Info "  Stop:           docker compose -f docker/docker-compose.yml down"
Write-Info "  Shell into web: docker compose -f docker/docker-compose.yml exec web bash"
Write-Info ""
Write-Info "Sprint 1 Features:"
Write-Info "  ✅ Multi-select filters (Status, Type, Location)"
Write-Info "  ✅ Fuzzy search with autocomplete"
Write-Info "  ✅ Search history (localStorage)"
Write-Info "  ✅ URL persistence (shareable links)"
Write-Info "  ✅ WCAG 2.1 Level AA accessibility"
Write-Info "  ✅ Error & loading states"
Write-Info ""
Write-Info "Next steps:"
Write-Info "  1. Create superuser: docker compose -f docker/docker-compose.yml exec web python manage.py createsuperuser"
Write-Info "  2. Open browser: http://localhost:8000/maps_view/dashboard/"
Write-Info "  3. Execute smoke tests (see SPRINT1_DEPLOYMENT_READY.md)"
Write-Info ""

Write-Log "Docker deployment completed successfully"
Write-Success "Deployment finished!"

exit 0
