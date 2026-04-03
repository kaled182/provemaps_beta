# Quick Commands - MapsProveFiber

## Daily startup
```powershell
cd D:\provemaps_beta
docker compose up -d redis
python manage.py runserver 0.0.0.0:8000
start http://localhost:8000
```

## Redis
```powershell
docker compose ps redis
docker compose up -d redis
docker compose stop redis
docker compose logs redis --tail 50
docker compose exec redis redis-cli
docker compose exec redis redis-cli KEYS "*"
docker compose exec redis redis-cli FLUSHDB
```

## Django
```powershell
python manage.py runserver 0.0.0.0:8000
python manage.py makemigrations
python manage.py migrate
python manage.py shell
```
