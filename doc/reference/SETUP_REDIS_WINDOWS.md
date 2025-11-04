# 🚀 Setting Up Redis + Services on Windows

## 📋 Prerequisites

- Windows 10/11
- Python 3.13 already installed ✅
- Django running ✅

---

## 🔴 Option 1: Redis via Docker (Recommended)

### Advantages
- ✅ Fastest install path
- ✅ Isolated from the host OS
- ✅ Easy to remove
- ✅ Matches the production version

### Installation

#### 1. Install Docker Desktop
```powershell
# Download and install from the official site:
# https://www.docker.com/products/docker-desktop/

# Or use winget (Windows Package Manager)
winget install Docker.DockerDesktop
```

#### 2. Launch Docker Desktop
- Open Docker Desktop after installation
- Wait for it to finish initializing (icon turns green)

#### 3. Run Redis
```powershell
# Inside the project folder
cd D:\provemaps_beta

# Start only the Redis service using docker compose
docker compose up -d redis

# Check status
docker compose ps redis

# Logs
docker compose logs redis --tail 50

# Stop
docker compose stop redis

# Start again
docker compose start redis

# Remove (if needed)
docker compose rm -f redis
```

---

## 🔴 Option 2: Native Redis on Windows

### Advantages
- ✅ No Docker requirement
- ✅ Can configure automatic startup

### Disadvantages
- ⚠️ Redis does not officially support Windows
- ⚠️ Relies on Microsoft's unofficial port (now discontinued)

### Installation

#### Via Chocolatey
```powershell
# Install Chocolatey (if you do not have it yet)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Redis
choco install redis-64 -y

# Start the service
redis-server --service-start

# Check status
redis-cli ping
# Should return: PONG
```

#### Via manual download
```powershell
# 1. Download from: https://github.com/tporadowski/redis/releases
# 2. Extract to C:\Redis
# 3. Add it to the PATH

# Start Redis
cd C:\Redis
redis-server.exe

# In another terminal, test
redis-cli ping
```

---

## 🔴 Option 3: Redis via WSL2 (Windows Subsystem for Linux)

### Advantages
- ✅ Official Linux Redis
- ✅ Better performance than Docker Desktop
- ✅ Lighter footprint

### Installation

```powershell
# 1. Install WSL2
wsl --install

# 2. Reboot the computer

# 3. Open Ubuntu WSL
wsl

# 4. Inside WSL, install Redis
sudo apt update
sudo apt install redis-server -y

# 5. Start Redis
sudo service redis-server start

# 6. Verify
redis-cli ping
# Should return: PONG

# 7. Return to Windows
exit
```

---

## ✅ Verify Installation

### Python connection test
```powershell
# Inside the project directory
python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('✅ Redis conectado!', r.ping())"
```

Expected output:
```
✅ Redis conectado! True
```

### Django cache test
```powershell
python manage.py shell
```

```python
from django.core.cache import cache

# Set
cache.set('test_key', 'Hello Redis!', 30)

# Get
print(cache.get('test_key'))  # Should print: Hello Redis!

# Clean up
cache.delete('test_key')
exit()
```

---

## 🔧 Project Configuration

### 1. Update `.env`
```bash
# Add or uncomment:
REDIS_URL=redis://localhost:6379/0

# For WSL2 or Docker with a specific network, use the proper IP
# REDIS_URL=redis://172.x.x.x:6379/0
```

### 2. Restart the Django server
```powershell
# CTRL+C in the server terminal
python manage.py runserver 0.0.0.0:8000
```

### 3. Check logs
You should **no longer** see:
```
[DEBUG] Cache offline (Redis unavailable)
```

Instead, caching should work normally (no debug messages when healthy).

---

## 🎯 Additional Services

### Celery worker (asynchronous tasks)

```powershell
# Separate terminal – worker
celery -A core worker -l info --pool=solo

# pool=solo is required on Windows (threads are unreliable)
```

### Celery Beat (scheduled tasks)

```powershell
# Separate terminal – beat
celery -A core beat -l info
```

### All services together

**Terminal 1 – Django:**
```powershell
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 – Celery worker:**
```powershell
celery -A core worker -l info --pool=solo
```

**Terminal 3 – Celery Beat:**
```powershell
celery -A core beat -l info
```

**Terminal 4 – Redis (if not already running):**
```powershell
docker compose up -d redis
```

---

## 🐛 Troubleshooting

### Redis will not connect

**Error:** `ConnectionRefusedError: [WinError 10061]`

**Fix:**
```powershell
# Check that Redis is running
redis-cli ping

# If it does not respond:
# Docker compose: docker compose start redis
# Native: redis-server --service-start
# WSL2: wsl -d Ubuntu -e sudo service redis-server start
```

### Celery refuses to start on Windows

**Error:** `AttributeError: 'module' object has no attribute 'Poll'`

**Fix:**
```powershell
# ALWAYS use --pool=solo on Windows
celery -A core worker -l info --pool=solo
```

### Port 6379 already in use

```powershell
# Discover which process is using the port
netstat -ano | findstr :6379

# Kill the process (replace PID)
taskkill /PID <number> /F

# Or use another port in `.env`
# REDIS_URL=redis://localhost:6380/0
```

### Redis loses data after restart

```powershell
# Enable persistence (Docker Compose)
# Create a docker-compose.override.yml with:
# services:
#   redis:
#     command: redis-server --appendonly yes
#     volumes:
#       - redis_data:/data
# Then apply:
docker compose up -d --force-recreate redis

# Native: edit redis.conf
# appendonly yes
# save 900 1
```

---

## 📊 Monitoring

### Redis CLI
```powershell
# Connect
redis-cli

# Useful commands:
INFO                  # General statistics
DBSIZE                # Number of keys
KEYS *                # List all keys (do NOT use in production!)
MONITOR               # Observe commands in real time
CLIENT LIST           # See active connections
CONFIG GET maxmemory  # View memory configuration
```

### Django Admin
```powershell
# Inspect cache metrics
curl http://localhost:8000/metrics/metrics | findstr cache
```

---

## 🚀 Quickstart (Docker – Fastest Path)

```powershell
# 1. Install Docker Desktop (if missing)
winget install Docker.DockerDesktop

# 2. Open Docker Desktop and wait for it to initialize

# 3. Run Redis
cd D:\provemaps_beta
docker compose up -d redis

# 4. Validate
docker compose ps redis
python -c "import redis; print(redis.Redis().ping())"

# 5. Update `.env`
# REDIS_URL=redis://localhost:6379/0

# 6. Restart Django
python manage.py runserver 0.0.0.0:8000

# ✅ Done!
```

---

## 🔗 Helpful Links

- **Redis Official:** https://redis.io/
- **Redis Docker Hub:** https://hub.docker.com/_/redis
- **Redis Windows (Tporadowski):** https://github.com/tporadowski/redis
- **Celery Windows Issues:** https://docs.celeryq.dev/en/stable/faq.html#does-celery-support-windows

---

**Which option fits you best?** 

- 🐳 **Option 1 (Docker)** – simplest, recommended
- 💻 **Option 2 (Native)** – if you want to avoid Docker
- 🐧 **Option 3 (WSL2)** – if you already use Linux on Windows
