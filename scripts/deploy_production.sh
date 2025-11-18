#!/bin/bash
#
# Production Deployment Script with Security Lockdown
# 
# This script:
# 1. Deploys the application to production
# 2. Creates SETUP_LOCKED file to prevent configuration changes
# 3. Runs migrations and collects static files
#
# Usage:
#   ./deploy_production.sh
#
# IMPORTANT: After running this script, the /setup_app/ routes will be
# blocked for security. To unlock, manually remove SETUP_LOCKED file.

set -e  # Exit on error

echo "🚀 Starting production deployment..."

# Change to project root
cd "$(dirname "$0")/.."

# Pull latest code
echo "📦 Pulling latest code from Git..."
git pull

# Build frontend
echo "🎨 Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Collect static files
echo "📁 Collecting static files..."
cd backend
python manage.py collectstatic --noinput --clear
cd ..

# Run migrations
echo "🗄️  Running database migrations..."
docker compose exec web python manage.py migrate

# Restart services
echo "🔄 Restarting services..."
docker compose restart web celery_worker celery_beat

# CRITICAL SECURITY: Lock the setup interface
echo "🔒 LOCKING SETUP INTERFACE..."
touch SETUP_LOCKED
touch backend/SETUP_LOCKED

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "⚠️  SECURITY NOTICE:"
echo "   The setup interface has been LOCKED."
echo "   Routes like /setup_app/ will now return 403 Forbidden."
echo ""
echo "   To unlock (DANGEROUS in production):"
echo "   rm SETUP_LOCKED backend/SETUP_LOCKED"
echo ""
echo "🎉 Application is now running in PRODUCTION MODE"
