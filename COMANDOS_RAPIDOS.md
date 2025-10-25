# ⚡ Comandos Rápidos - MapsProveFiber Dev

## 🚀 Startup Diário

```powershell
# 1. Navegar para o projeto
cd D:\Gemini\Provemaps_GPT-Tier2\mapsprovefiber

# 2. Iniciar Redis (se parado)
docker start redis-mapspro

# 3. Iniciar Django
python manage.py runserver 0.0.0.0:8000

# 4. Abrir navegador
start http://localhost:8000
```

---

## 🔴 Redis

```powershell
# Status
docker ps | findstr redis

# Iniciar
docker start redis-mapspro

# Parar
docker stop redis-mapspro

# Logs
docker logs redis-mapspro --tail 50

# CLI interativo
docker exec -it redis-mapspro redis-cli

# Ver chaves
docker exec redis-mapspro redis-cli KEYS "*"

# Limpar cache
docker exec redis-mapspro redis-cli FLUSHDB
```

---

## 🐍 Django

```powershell
# Servidor desenvolvimento
python manage.py runserver 0.0.0.0:8000

# Migrações
python manage.py makemigrations
python manage.py migrate

# Shell interativo
python manage.py shell

# Criar superuser
python manage.py createsuperuser

# Coletar static files
python manage.py collectstatic --noinput

# Ver rotas
python manage.py show_urls
```

---

## ✅ Verificações Rápidas

```powershell
# Redis online?
python -c "import redis; print('✅ OK' if redis.Redis().ping() else '❌ Offline')"

# Django respondendo?
Invoke-WebRequest http://localhost:8000/healthz

# Cache funcionando?
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok'); print('✅ Cache OK' if cache.get('test') == 'ok' else '❌ Cache falhou')"

# Ver versões
python --version
docker --version
python -c "import django; print('Django:', django.get_version())"
```

---

## 🧪 Testes

```powershell
# Todos os testes
python -m pytest tests/ -v

# Teste específico
python -m pytest tests/test_smoke.py -v

# Com cobertura
python -m pytest --cov --cov-report=html
```

---

## 🗄️ Banco de Dados

```powershell
# Shell do banco
python manage.py dbshell

# Dump do banco
python manage.py dumpdata > backup.json

# Carregar dump
python manage.py loaddata backup.json

# Resetar banco (cuidado!)
Remove-Item db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## 🐳 Docker

```powershell
# Ver containers ativos
docker ps

# Ver todos (incluindo parados)
docker ps -a

# Parar todos
docker stop $(docker ps -q)

# Remover todos parados
docker container prune -f

# Ver imagens
docker images

# Limpar tudo (cuidado!)
docker system prune -a
```

---

## 📊 Monitoramento

```powershell
# Métricas Prometheus
Invoke-WebRequest http://localhost:8000/metrics/metrics

# Health checks
Invoke-WebRequest http://localhost:8000/healthz        # Completo
Invoke-WebRequest http://localhost:8000/ready          # Readiness
Invoke-WebRequest http://localhost:8000/live           # Liveness

# Redis stats
docker exec redis-mapspro redis-cli INFO stats
docker exec redis-mapspro redis-cli INFO memory
docker exec redis-mapspro redis-cli DBSIZE
```

---

## 🔧 Manutenção

```powershell
# Limpar cache Python
Remove-Item -Recurse -Force __pycache__
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# Limpar logs
Remove-Item logs\*.log

# Atualizar dependências
pip install -r requirements.txt --upgrade

# Ver pacotes desatualizados
pip list --outdated
```

---

## 🚨 Emergência

```powershell
# Parar Django (CTRL+C no terminal ou)
Get-Process python | Stop-Process -Force

# Parar Redis
docker stop redis-mapspro

# Reiniciar tudo
docker restart redis-mapspro
python manage.py runserver 0.0.0.0:8000

# Porta 8000 ocupada? Ver o que está usando
netstat -ano | findstr :8000

# Matar processo (substitua PID)
taskkill /PID <número> /F
```

---

## 📝 Logs

```powershell
# Django logs (ver terminal rodando)

# Redis logs
docker logs redis-mapspro --tail 100

# Filtrar logs Django
Get-Content logs\application.log | Select-String "ERROR"
Get-Content logs\application.log | Select-String "cache"
Get-Content logs\application.log | Select-String "zabbix"
```

---

## 🔍 Debug

```powershell
# Shell Django interativo
python manage.py shell

# Dentro do shell:
from django.core.cache import cache
from zabbix_api.services.zabbix_service import *
from django.contrib.auth.models import User

# Ver configurações
python manage.py diffsettings

# Ver SQL gerado
python manage.py sqlmigrate zabbix_api 0009
```

---

## 🌐 URLs Importantes

- **Dashboard:** http://localhost:8000/maps_view/dashboard/
- **Admin:** http://localhost:8000/admin/
- **Docs:** http://localhost:8000/setup_app/docs/
- **Zabbix Lookup:** http://localhost:8000/zabbix/lookup/
- **Route Builder:** http://localhost:8000/routes_builder/fiber-route-builder/
- **Metrics:** http://localhost:8000/metrics/metrics
- **Health:** http://localhost:8000/healthz

---

## 💡 Dicas

### Alias úteis (adicionar no $PROFILE)
```powershell
function Start-MapsProDev {
    cd D:\Gemini\Provemaps_GPT-Tier2\mapsprovefiber
    docker start redis-mapspro
    python manage.py runserver 0.0.0.0:8000
}

function Test-MapsProHealth {
    python -c "import redis; print('Redis:', 'OK' if redis.Redis().ping() else 'Offline')"
    Invoke-WebRequest http://localhost:8000/healthz -UseBasicParsing | Select-Object StatusCode
}
```

### Variáveis de ambiente
```powershell
# Ver .env atual
Get-Content .env

# Setar temporariamente (sessão atual)
$env:DEBUG = "True"
$env:REDIS_URL = "redis://localhost:6379/0"
```

### Performance
```powershell
# Medir tempo de request
Measure-Command { Invoke-WebRequest http://localhost:8000/zabbix_api/api/sites/ }

# Ver conexões ativas
netstat -ano | findstr :8000
netstat -ano | findstr :6379
```

---

**Salve este arquivo para referência rápida!** 📌
