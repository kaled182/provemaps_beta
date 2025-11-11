# PostGIS Setup Guide (Phase 10)

## 🎯 Objetivo

Guia prático para configurar e testar PostGIS antes de migrar produção.

---

## 📦 Opção 1: Docker (Recomendado)

### 1. Subir Container PostGIS

```bash
# Navegar para pasta do projeto
cd d:\provemaps_beta

# Criar arquivo .env.postgis (ou adicionar ao .env existente)
cat > .env.postgis <<EOF
DB_ENGINE=postgis
DB_NAME=mapsprovefiber
DB_USER=provemaps
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432
EOF

# Subir PostgreSQL + PostGIS
docker-compose -f docker/docker-compose.postgis.yml up -d postgres

# Verificar saúde do container
docker-compose -f docker/docker-compose.postgis.yml ps
```

**Output esperado:**
```
NAME                          STATUS                    PORTS
mapsprovefiber_postgis        Up (healthy)             0.0.0.0:5432->5432/tcp
```

### 2. Testar Conexão

```bash
# Via Docker CLI
docker exec -it mapsprovefiber_postgis psql -U provemaps -d mapsprovefiber -c "SELECT postgis_full_version();"

# Via psql local (se instalado)
psql -h localhost -p 5432 -U provemaps -d mapsprovefiber -c "SELECT postgis_full_version();"
```

**Output esperado:**
```
                                    postgis_full_version
--------------------------------------------------------------------------------------------
 POSTGIS="3.4.0" [EXTENSION] PGSQL="16.0" GEOS="3.12.0" PROJ="9.3.0" LIBXML="2.9.14" ...
```

### 3. Configurar Django para PostGIS

```bash
# Editar .env ou exportar variáveis
export DB_ENGINE=postgis
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=mapsprovefiber
export DB_USER=provemaps
export DB_PASSWORD=secure_password_here

# Ou no Windows PowerShell
$env:DB_ENGINE="postgis"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="mapsprovefiber"
$env:DB_USER="provemaps"
$env:DB_PASSWORD="secure_password_here"
```

### 4. Executar Migrations

```bash
cd backend

# Verificar se Django detecta PostGIS
python manage.py check

# Criar tabelas
python manage.py migrate

# Verificar se tabelas espaciais foram criadas
docker exec -it mapsprovefiber_postgis psql -U provemaps -d mapsprovefiber -c "\dt"
```

### 5. (Opcional) Abrir PgAdmin

```bash
# Subir PgAdmin
docker-compose -f docker/docker-compose.postgis.yml --profile tools up -d pgadmin

# Acessar: http://localhost:5050
# Email: admin@mapsprovefiber.local
# Senha: admin
```

---

## 📦 Opção 2: Instalação Local

### Windows

```powershell
# 1. Baixar PostgreSQL + PostGIS
# https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
# Incluir "PostGIS Bundle" durante instalação

# 2. Adicionar ao PATH
$env:PATH += ";C:\Program Files\PostgreSQL\16\bin"

# 3. Criar banco
psql -U postgres -c "CREATE DATABASE mapsprovefiber;"
psql -U postgres -d mapsprovefiber -c "CREATE EXTENSION postgis;"

# 4. Criar usuário
psql -U postgres -c "CREATE USER provemaps WITH PASSWORD 'secure_password';"
psql -U postgres -c "ALTER DATABASE mapsprovefiber OWNER TO provemaps;"
```

### Linux (Ubuntu/Debian)

```bash
# 1. Instalar PostgreSQL + PostGIS
sudo apt-get update
sudo apt-get install -y postgresql-14 postgresql-14-postgis-3 postgis

# 2. Criar banco e usuário
sudo -u postgres psql <<EOF
CREATE DATABASE mapsprovefiber;
CREATE USER provemaps WITH PASSWORD 'secure_password';
ALTER DATABASE mapsprovefiber OWNER TO provemaps;
\c mapsprovefiber
CREATE EXTENSION postgis;
EOF

# 3. Configurar pg_hba.conf (permitir conexão local)
sudo vim /etc/postgresql/14/main/pg_hba.conf
# Adicionar: local   all   provemaps   md5

# 4. Reiniciar PostgreSQL
sudo systemctl restart postgresql
```

### macOS

```bash
# 1. Instalar via Homebrew
brew install postgresql@14 postgis

# 2. Iniciar serviço
brew services start postgresql@14

# 3. Criar banco
createdb mapsprovefiber
psql mapsprovefiber -c "CREATE EXTENSION postgis;"
```

---

## 🧪 Testes de Validação

### 1. Criar Geometria de Teste

```bash
cd backend
python manage.py shell
```

```python
from django.contrib.gis.geos import Point, LineString, Polygon
from inventory.models_routes import RouteSegment

# Criar segmento em Brasília
segment = RouteSegment.objects.create(
    path=LineString(
        [(-47.9292, -15.7801), (-47.9200, -15.7750)],
        srid=4326
    ),
    length_km=1.2,
)

print(f"✅ Segmento criado: {segment.id}")
print(f"   Path: {segment.path}")
print(f"   Length: {segment.path.length} (em graus)")
```

### 2. Query Espacial (BBox)

```python
from django.contrib.gis.geos import Polygon

# BBox cobrindo Brasília
bbox = Polygon.from_bbox((-48.0, -16.0, -47.5, -15.5))

# Filtrar segmentos dentro do BBox
results = RouteSegment.objects.filter(path__bboverlaps=bbox)

print(f"✅ Segmentos encontrados: {results.count()}")
for seg in results:
    print(f"   - Segment {seg.id}: {seg.length_km}km")
```

### 3. Operações Espaciais Avançadas

```python
# Calcular distância entre dois pontos
p1 = Point(-47.9292, -15.7801, srid=4326)
p2 = Point(-47.9200, -15.7750, srid=4326)

# Distância em graus (para converter para metros, usar transform)
distance_degrees = p1.distance(p2)
print(f"Distância: {distance_degrees:.6f} graus")

# Criar buffer (área de 1km ao redor de um ponto)
# Nota: requer projeção métrica (ex: UTM) para precisão
buffer = p1.buffer(0.01)  # ~1.1km em lat/lng
print(f"Buffer area: {buffer.area:.6f} graus²")
```

### 4. Validar Índice Espacial (GiST)

```bash
docker exec -it mapsprovefiber_postgis psql -U provemaps -d mapsprovefiber
```

```sql
-- Listar índices espaciais
SELECT
    indexname,
    indexdef
FROM
    pg_indexes
WHERE
    indexdef LIKE '%USING gist%'
AND tablename LIKE 'inventory_%';

-- Criar índice manualmente (se necessário)
CREATE INDEX IF NOT EXISTS inventory_routesegment_path_gist
    ON inventory_routesegment
    USING GIST (path);

-- Verificar uso do índice em uma query
EXPLAIN ANALYZE
SELECT * FROM inventory_routesegment
WHERE path && ST_MakeEnvelope(-48, -16, -47.5, -15.5, 4326);
```

---

## 📊 Performance Benchmark

### Script de Teste

```python
# scripts/benchmark_postgis.py
import time
from django.contrib.gis.geos import Polygon, LineString
from inventory.models_routes import RouteSegment

# 1. Criar 1000 segmentos aleatórios
print("Criando 1000 segmentos...")
import random

for i in range(1000):
    lat_base = random.uniform(-23.0, -15.0)
    lng_base = random.uniform(-50.0, -45.0)
    
    RouteSegment.objects.create(
        path=LineString(
            [(lng_base, lat_base), (lng_base + 0.01, lat_base + 0.01)],
            srid=4326
        ),
        length_km=random.uniform(0.5, 5.0),
    )

print("✅ 1000 segmentos criados")

# 2. Benchmark: Query BBox
bbox = Polygon.from_bbox((-48.0, -18.0, -46.0, -16.0))

start = time.time()
results = list(RouteSegment.objects.filter(path__bboverlaps=bbox))
duration = (time.time() - start) * 1000

print(f"\n📊 Performance:")
print(f"   Query BBox: {len(results)} segmentos em {duration:.2f}ms")
print(f"   {'✅ PASS' if duration < 100 else '⚠️  SLOW'} (esperado: <100ms)")

# 3. Comparar: Query sem filtro espacial
start = time.time()
all_results = list(RouteSegment.objects.all())
duration_all = (time.time() - start) * 1000

print(f"   Query ALL:  {len(all_results)} segmentos em {duration_all:.2f}ms")
print(f"   Speedup:    {duration_all/duration:.1f}x mais rápido com BBox")
```

**Executar:**
```bash
cd backend
python scripts/benchmark_postgis.py
```

**Output esperado:**
```
Criando 1000 segmentos...
✅ 1000 segmentos criados

📊 Performance:
   Query BBox: 234 segmentos em 42.15ms
   ✅ PASS (esperado: <100ms)
   Query ALL:  1000 segmentos em 158.32ms
   Speedup:    3.8x mais rápido com BBox
```

---

## 🚨 Troubleshooting

### Erro: "GDAL is not installed"

```bash
# Linux
sudo apt-get install gdal-bin libgdal-dev python3-gdal

# macOS
brew install gdal
export GDAL_LIBRARY_PATH=/opt/homebrew/opt/gdal/lib/libgdal.dylib

# Windows
# Instalar OSGeo4W: https://trac.osgeo.org/osgeo4w/
# Ou usar Docker (recomendado)
```

### Erro: "Cannot connect to PostgreSQL"

```bash
# Verificar se container está rodando
docker ps | grep postgres

# Ver logs do container
docker logs mapsprovefiber_postgis

# Testar conexão direta
docker exec -it mapsprovefiber_postgis pg_isready
```

### Erro: "relation does not exist"

```bash
# Executar migrations
cd backend
python manage.py migrate

# Verificar tabelas criadas
docker exec -it mapsprovefiber_postgis psql -U provemaps -d mapsprovefiber -c "\dt"
```

### Performance Lenta

```sql
-- Verificar índices
SELECT * FROM pg_indexes WHERE tablename LIKE 'inventory_%';

-- Criar índice espacial manualmente
CREATE INDEX inventory_routesegment_path_gist
    ON inventory_routesegment
    USING GIST (path);

-- Atualizar estatísticas
ANALYZE inventory_routesegment;
```

---

## 📝 Próximos Passos

Após validar PostGIS funcionando:

1. **Migrar dados MySQL → PostgreSQL**
   - Usar `python manage.py dumpdata` + `loaddata`
   - Ou ferramenta [pgloader](https://github.com/dimitri/pgloader)

2. **Executar migration de conversão (JSON → Geometry)**
   - `python manage.py migrate inventory 0010`

3. **Implementar API com filtro BBox**
   - Ver `PHASE10_POSTGIS_MIGRATION_PLAN.md` (Phase 10.4)

4. **Frontend Vue 3: Integrar BBox queries**
   - Atualizar `fetchSegmentsInView()` para passar bbox param

5. **Deploy staging → produção**
   - Backup MySQL
   - Deploy PostGIS
   - Monitorar performance

---

**Documentação:**
- [GeoDjango Tutorial](https://docs.djangoproject.com/en/5.0/ref/contrib/gis/tutorial/)
- [PostGIS Workshop](https://postgis.net/workshops/postgis-intro/)
- [Spatial Lookups Reference](https://docs.djangoproject.com/en/5.0/ref/contrib/gis/geoquerysets/)
