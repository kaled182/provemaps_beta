# Sprint 1 Environment Configuration
## Staging Environment Setup

**Version:** 1.0.0  
**Environment:** Staging  
**Last Updated:** November 12, 2025

---

## 🔐 Backend Environment Variables

### Required (.env)

```bash
# Django Settings
DJANGO_SETTINGS_MODULE=settings.staging
SECRET_KEY=your-secret-key-here-min-50-chars
DEBUG=False
ALLOWED_HOSTS=staging.provemaps.com,staging-api.provemaps.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/provemaps_staging
# or for MySQL:
# DATABASE_URL=mysql://user:password@localhost:3306/provemaps_staging

# Static Files
STATIC_URL=/static/
STATIC_ROOT=/var/www/provemaps/static/
MEDIA_URL=/media/
MEDIA_ROOT=/var/www/provemaps/media/

# Cache Busting (IMPORTANT for Sprint 1)
STATIC_ASSET_VERSION=1.0.0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

### Optional (Performance)

```bash
# Redis Cache (graceful degradation if missing)
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300

# Channels (WebSocket)
CHANNEL_LAYER_URL=redis://localhost:6379/1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/3
```

### Feature Flags (Sprint 1)

```bash
# Enable new features (default: True)
ENABLE_FILTERS=True
ENABLE_SEARCH=True
ENABLE_URL_PERSISTENCE=True
ENABLE_ACCESSIBILITY_FEATURES=True

# Diagnostic endpoints
ENABLE_DIAGNOSTIC_ENDPOINTS=True
HEALTHCHECK_ENABLED=True
```

### Monitoring

```bash
# Sentry Error Tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=1.0

# Performance Monitoring
PROMETHEUS_ENABLED=True
METRICS_PORT=9090
```

---

## 🎨 Frontend Environment Variables

### Required (.env.staging)

```bash
# API Configuration
VITE_API_BASE_URL=https://staging-api.provemaps.com
VITE_WS_BASE_URL=wss://staging-api.provemaps.com

# Feature Flags
VITE_ENABLE_FILTERS=true
VITE_ENABLE_SEARCH=true
VITE_ENABLE_URL_PERSISTENCE=true
VITE_ENABLE_ACCESSIBILITY=true

# Search Configuration
VITE_MAX_SEARCH_RESULTS=10
VITE_SEARCH_DEBOUNCE_MS=300
VITE_SEARCH_HISTORY_LIMIT=10
VITE_FUZZY_SEARCH_THRESHOLD=0.3

# URL Sync Configuration
VITE_URL_UPDATE_DEBOUNCE_MS=500
VITE_MAX_URL_LENGTH=2000
VITE_MAX_QUERY_LENGTH=200
```

### Optional (Development)

```bash
# Build Configuration
VITE_BUILD_SOURCEMAP=false
VITE_BUILD_MINIFY=true
VITE_BUILD_CHUNK_SIZE_WARNING_LIMIT=500

# Analytics
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Feature Toggles (A/B Testing)
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_ERROR_TRACKING=true
```

---

## 📝 Configuration Files

### Backend: settings/staging.py

```python
# settings/staging.py
from .base import *
import os

# Security
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'staging.provemaps.com').split(',')

# Static files with cache busting
STATIC_ASSET_VERSION = os.getenv('STATIC_ASSET_VERSION', '1.0.0')

# Feature flags
ENABLE_FILTERS = os.getenv('ENABLE_FILTERS', 'True') == 'True'
ENABLE_SEARCH = os.getenv('ENABLE_SEARCH', 'True') == 'True'
ENABLE_URL_PERSISTENCE = os.getenv('ENABLE_URL_PERSISTENCE', 'True') == 'True'

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'provemaps_staging',
        'TIMEOUT': int(os.getenv('CACHE_TTL', 300)),
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/provemaps/staging.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'maps_view': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}
```

### Frontend: .env.staging

```bash
# .env.staging
VITE_API_BASE_URL=https://staging-api.provemaps.com
VITE_WS_BASE_URL=wss://staging-api.provemaps.com
VITE_ENABLE_FILTERS=true
VITE_ENABLE_SEARCH=true
VITE_MAX_SEARCH_RESULTS=10
VITE_SEARCH_DEBOUNCE_MS=300
VITE_URL_UPDATE_DEBOUNCE_MS=500
```

### Frontend: vite.config.js

```javascript
// vite.config.js
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      sourcemap: env.VITE_BUILD_SOURCEMAP === 'true',
      minify: env.VITE_BUILD_MINIFY !== 'false',
      chunkSizeWarningLimit: parseInt(env.VITE_BUILD_CHUNK_SIZE_WARNING_LIMIT || '500'),
      rollupOptions: {
        output: {
          manualChunks: {
            'fuse': ['fuse.js'],
            'vueuse': ['@vueuse/core'],
          },
        },
      },
    },
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: env.VITE_WS_BASE_URL || 'ws://localhost:8000',
          ws: true,
        },
      },
    },
  };
});
```

---

## 🗃️ Database Configuration

### PostgreSQL (Recommended)

```sql
-- Create staging database
CREATE DATABASE provemaps_staging;
CREATE USER provemaps_staging WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE provemaps_staging TO provemaps_staging;

-- Enable PostGIS (if using spatial features)
\c provemaps_staging
CREATE EXTENSION IF NOT EXISTS postgis;
```

### MySQL (Alternative)

```sql
-- Create staging database
CREATE DATABASE provemaps_staging CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'provemaps_staging'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON provemaps_staging.* TO 'provemaps_staging'@'localhost';
FLUSH PRIVILEGES;
```

---

## 🔧 Web Server Configuration

### Nginx

```nginx
# /etc/nginx/sites-available/provemaps-staging

# Frontend
server {
    listen 80;
    server_name staging.provemaps.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name staging.provemaps.com;

    ssl_certificate /etc/letsencrypt/live/staging.provemaps.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging.provemaps.com/privkey.pem;

    root /var/www/provemaps/frontend;
    index index.html;

    # Static assets with cache busting
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # HTML files no cache (for version updates)
    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}

# Backend API
server {
    listen 80;
    server_name staging-api.provemaps.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name staging-api.provemaps.com;

    ssl_certificate /etc/letsencrypt/live/staging-api.provemaps.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging-api.provemaps.com/privkey.pem;

    location /static/ {
        alias /var/www/provemaps/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/provemaps/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 🐳 Docker Configuration (Optional)

### docker-compose.staging.yml

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: docker/dockerfile
    environment:
      - DJANGO_SETTINGS_MODULE=settings.staging
      - DATABASE_URL=postgresql://postgres:password@db:5432/provemaps
      - REDIS_URL=redis://redis:6379/0
      - STATIC_ASSET_VERSION=1.0.0
    volumes:
      - ./backend:/app
      - static_volume:/var/www/static
      - media_volume:/var/www/media
    depends_on:
      - db
      - redis

  db:
    image: postgis/postgis:15-3.3
    environment:
      - POSTGRES_DB=provemaps
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  celery:
    build:
      context: .
      dockerfile: docker/dockerfile
    command: celery -A core worker -l info
    environment:
      - DJANGO_SETTINGS_MODULE=settings.staging
      - CELERY_BROKER_URL=redis://redis:6379/2
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

---

## ✅ Validation Checklist

Before deployment, verify all configurations:

### Backend
- [ ] .env file exists with all required variables
- [ ] SECRET_KEY is set (min 50 chars)
- [ ] DATABASE_URL is correct
- [ ] STATIC_ASSET_VERSION is set
- [ ] ALLOWED_HOSTS includes staging domain
- [ ] Feature flags set correctly

### Frontend
- [ ] .env.staging file exists
- [ ] VITE_API_BASE_URL points to staging API
- [ ] Feature flags match backend
- [ ] Debounce values reasonable
- [ ] Build config optimized for production

### Database
- [ ] Database created
- [ ] User has correct permissions
- [ ] Migrations run successfully
- [ ] Test data loaded (if needed)

### Web Server
- [ ] Nginx config symlinked
- [ ] SSL certificates valid
- [ ] Static file paths correct
- [ ] WebSocket proxying enabled

### Services
- [ ] Gunicorn running
- [ ] Celery worker running
- [ ] Celery beat running (if needed)
- [ ] Redis running
- [ ] Nginx running

---

## 📊 Environment-Specific Settings

### Development vs Staging vs Production

| Setting | Development | Staging | Production |
|---------|------------|---------|-----------|
| DEBUG | True | False | False |
| ALLOWED_HOSTS | * | staging.provemaps.com | provemaps.com |
| STATIC_ASSET_VERSION | dev | 1.0.0 | 1.0.0 |
| CACHE_TTL | 10 | 300 | 600 |
| SENTRY_TRACES_SAMPLE_RATE | 0.0 | 1.0 | 0.1 |
| LOG_LEVEL | DEBUG | INFO | WARNING |

---

**Configuration Prepared By:** AI Assistant  
**Reviewed By:** _____________  
**Last Updated:** November 12, 2025  
**Next Review:** _____________
