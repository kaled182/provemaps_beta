# Comandos Rápidos — MapsProveFiber

## Startup Diário
```powershell
cd D:\Gemini\Provemaps_GPT-Tier2\mapsprovefiber
docker start redis-mapspro
python manage.py runserver 0.0.0.0:8000
start http://localhost:8000
```

## Redis
```powershell
docker ps | findstr redis
docker start redis-mapspro
docker stop redis-mapspro
docker logs redis-mapspro --tail 50
docker exec -it redis-mapspro redis-cli
docker exec redis-mapspro redis-cli KEYS "*"
docker exec redis-mapspro redis-cli FLUSHDB
```

## Django
```powershell
python manage.py runserver 0.0.0.0:8000
python manage.py makemigrations
python manage.py migrate
python manage.py shell
```
