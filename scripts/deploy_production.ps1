# Production Deployment Script with Security Lockdown
#
# This script:
# 1. Deploys the application to production
# 2. Creates SETUP_LOCKED file to prevent configuration changes
# 3. Runs migrations and collects static files
#
# Usage (PowerShell):
#   .\deploy_production.ps1
#
# IMPORTANT: After running this script, the /setup_app/ routes will be
# blocked for security. To unlock, manually remove SETUP_LOCKED file.

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting production deployment..." -ForegroundColor Green

# Pull latest code
Write-Host "📦 Pulling latest code from Git..." -ForegroundColor Cyan
git pull

# Build frontend
Write-Host "🎨 Building frontend..." -ForegroundColor Cyan
Set-Location frontend
npm install
npm run build
Set-Location ..

# Collect static files
Write-Host "📁 Collecting static files..." -ForegroundColor Cyan
Set-Location backend
python manage.py collectstatic --noinput --clear
Set-Location ..

# Run migrations
Write-Host "🗄️  Running database migrations..." -ForegroundColor Cyan
docker compose exec web python manage.py migrate

# Restart services
Write-Host "🔄 Restarting services..." -ForegroundColor Cyan
docker compose restart web celery_worker celery_beat

# CRITICAL SECURITY: Lock the setup interface
Write-Host "🔒 LOCKING SETUP INTERFACE..." -ForegroundColor Yellow
New-Item -Path "SETUP_LOCKED" -ItemType File -Force | Out-Null
New-Item -Path "backend\SETUP_LOCKED" -ItemType File -Force | Out-Null

Write-Host ""
Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  SECURITY NOTICE:" -ForegroundColor Yellow
Write-Host "   The setup interface has been LOCKED."
Write-Host "   Routes like /setup_app/ will now return 403 Forbidden."
Write-Host ""
Write-Host "   To unlock (DANGEROUS in production):"
Write-Host "   Remove-Item SETUP_LOCKED, backend\SETUP_LOCKED"
Write-Host ""
Write-Host "🎉 Application is now running in PRODUCTION MODE" -ForegroundColor Green
