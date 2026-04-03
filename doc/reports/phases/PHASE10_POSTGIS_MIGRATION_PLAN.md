# Phase 10: PostGIS Migration Plan

## ⚠️ AVISO IMPORTANTE

**Esta é uma mudança de infraestrutura significativa que requer:**
- Migração de banco de dados (MySQL/MariaDB → PostgreSQL + PostGIS)
- Instalação de dependências do sistema (GDAL, PostGIS)
- Conversão de dados (JSONField → LineStringField)
- Testes de compatibilidade antes do deploy em produção

**Recomendação:** Testar em ambiente staging/development primeiro.

---

## 🎯 Objetivo

Resolver o gargalo de performance do mapa permitindo **filtros espaciais nativos** no banco de dados.

### Problema Atual (MySQL + JSONField)

```python
# backend/inventory/models_routes.py
class RouteSegment(models.Model):
    path_coordinates = models.JSONField(
        blank=True,
        null=True,
        help_text='Array of {"lat": float, "lng": float} points.',
    )
```

**Limitações:**
- ❌ MySQL não pode filtrar segmentos por área visível (BBox)
- ❌ Frontend carrega TODOS os segmentos e filtra no JavaScript
- ❌ Não escala para >1000 segmentos (lentidão no navegador)
- ❌ Queries espaciais complexas (distância, interseção) impossíveis

### Solução (PostgreSQL + PostGIS + LineStringField)

```python
# backend/inventory/models_routes.py
from django.contrib.gis.db import models as gis_models

class RouteSegment(models.Model):
    path = gis_models.LineStringField(
        srid=4326,  # WGS84 (padrão GPS)
        blank=True,
        null=True,
        help_text="Trajeto geográfico do segmento.",
    )
```

**Benefícios:**
- ✅ Filtro espacial `path__bboverlaps` (BBox query nativa)
- ✅ Backend retorna apenas segmentos visíveis no mapa
- ✅ Escala para 10k+ segmentos (query <100ms)
- ✅ Suporta operações avançadas (buffer, intersection, distance)

---

## 📋 Fases de Implementação

### Phase 10.1: Ambiente Dual-Database (ATUAL)

**Objetivo:** Adicionar suporte a PostGIS SEM quebrar MySQL existente.

**Estratégia:**
1. Adicionar `django.contrib.gis` ao `INSTALLED_APPS`
2. Manter `ENGINE = "django.db.backends.mysql"` (compatibilidade)
3. Criar modelos com AMBOS os campos (`path_coordinates` JSONField + `path` LineStringField)
4. Permitir que usuário escolha quando migrar

**Arquivos modificados:**
- `backend/settings/base.py` (adicionar gis ao INSTALLED_APPS)
- `backend/inventory/models_routes.py` (adicionar campo `path` opcional)
- `backend/inventory/models.py` (adicionar campo `path` em FiberCable opcional)

**Resultado:**
- Sistema continua funcionando com MySQL
- PostGIS disponível quando usuário migrar
- Zero downtime para usuários atuais

### Phase 10.2: Docker Compose com PostgreSQL + PostGIS

**Objetivo:** Fornecer infraestrutura pronta para testes.

**Arquivos:**
- `docker/docker-compose.postgis.yml` (nova configuração)
- `docker/sql/init_postgis.sql` (scripts de inicialização)

**Comandos:**
```bash
# Subir ambiente PostGIS (paralelo ao MySQL)
docker-compose -f docker/docker-compose.postgis.yml up -d postgres

# Variáveis de ambiente para PostGIS
export DB_ENGINE=postgis
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=mapsprovefiber
export DB_USER=provemaps
export DB_PASSWORD=<senha>
```

### Phase 10.3: Migration de Dados (JSON → Geometry)

**Script:** `backend/inventory/migrations/0010_convert_json_to_linestring.py`

```python
from django.contrib.gis.geos import LineString
from django.db import migrations

def convert_paths_to_geometry(apps, schema_editor):
    """Converte path_coordinates (JSON) para path (LineString)"""
    RouteSegment = apps.get_model("inventory", "RouteSegment")
    FiberCable = apps.get_model("inventory", "FiberCable")
    
    # RouteSegment
    for segment in RouteSegment.objects.all():
        coords = segment.path_coordinates
        if coords and isinstance(coords, list):
            try:
                # JSON: [{"lat": -16.6, "lng": -49.2}, ...]
                # LineString: [(lng, lat), (lng, lat), ...]
                points = [(pt["lng"], pt["lat"]) for pt in coords]
                segment.path = LineString(points, srid=4326)
                segment.save(update_fields=["path"])
            except (KeyError, TypeError, ValueError) as e:
                print(f"⚠️  Segment {segment.id}: conversão falhou ({e})")
    
    # FiberCable
    for cable in FiberCable.objects.all():
        coords = cable.path_coordinates
        if coords and isinstance(coords, list):
            try:
                points = [(pt["lng"], pt["lat"]) for pt in coords]
                cable.path = LineString(points, srid=4326)
                cable.save(update_fields=["path"])
            except (KeyError, TypeError, ValueError) as e:
                print(f"⚠️  Cable {cable.id}: conversão falhou ({e})")

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0009_fibercable_last_live_check_and_more'),
    ]
    
    operations = [
        migrations.RunPython(
            convert_paths_to_geometry,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
```

### Phase 10.4: API com Filtro BBox

**Arquivo:** `backend/inventory/viewsets.py` (novo)

```python
from django.contrib.gis.geos import Polygon
from rest_framework import viewsets
from rest_framework.decorators import action
from inventory.models_routes import RouteSegment
from inventory.serializers import RouteSegmentSerializer

class RouteSegmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset para segmentos de rota com filtro espacial (PostGIS).
    
    Endpoints:
    - GET /api/segments/          -> Todos os segmentos
    - GET /api/segments/?bbox=... -> Segmentos na área visível
    """
    queryset = RouteSegment.objects.all()
    serializer_class = RouteSegmentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro espacial: /api/segments/?bbox=-49.2,-16.6,-49.1,-16.5
        # Formato: lng_min,lat_min,lng_max,lat_max
        bbox_param = self.request.query_params.get('bbox')
        
        if bbox_param:
            try:
                coords = [float(x) for x in bbox_param.split(',')]
                if len(coords) != 4:
                    return queryset
                
                xmin, ymin, xmax, ymax = coords
                bbox_polygon = Polygon.from_bbox((xmin, ymin, xmax, ymax))
                
                # MÁGICA DO POSTGIS: filtro espacial no banco!
                # Retorna apenas segmentos que intersectam o BBox
                queryset = queryset.filter(path__bboverlaps=bbox_polygon)
                
            except (ValueError, TypeError):
                pass  # BBox inválido, retorna todos
        
        return queryset
```

**Serializer:**
```python
# backend/inventory/serializers.py
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from inventory.models_routes import RouteSegment

class RouteSegmentSerializer(GeoFeatureModelSerializer):
    """Serializer GeoJSON para RouteSegment"""
    
    class Meta:
        model = RouteSegment
        geo_field = "path"
        fields = ["id", "route", "order", "length_km", "estimated_loss_db"]
```

**URLs:**
```python
# backend/core/urls.py
from rest_framework.routers import DefaultRouter
from inventory.viewsets import RouteSegmentViewSet

router = DefaultRouter()
router.register(r'segments', RouteSegmentViewSet, basename='segment')

urlpatterns = [
    # ... rotas existentes
    path('api/', include(router.urls)),
]
```

---

## 📦 Dependências do Sistema

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    postgis \
    postgresql-14-postgis-3
```

### macOS
```bash
brew install gdal postgis
```

### Windows
```powershell
# Via OSGeo4W (https://trac.osgeo.org/osgeo4w/)
# Ou usar Docker (recomendado)
```

### Python Packages
```bash
pip install \
    psycopg2-binary \
    djangorestframework-gis \
    GDAL
```

---

## 🧪 Testes de Validação

### 1. Teste de Spatial Query

```python
# backend/inventory/tests/test_spatial_queries.py
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from inventory.models_routes import RouteSegment

class SpatialQueryTests(TestCase):
    def setUp(self):
        from django.contrib.gis.geos import LineString
        
        # Criar segmento em Brasília
        self.segment = RouteSegment.objects.create(
            path=LineString(
                [(-47.9292, -15.7801), (-47.9200, -15.7750)],
                srid=4326
            ),
            length_km=1.2,
        )
    
    def test_bbox_filter(self):
        """Testa filtro BBox sobre Brasília"""
        # BBox cobrindo Brasília
        bbox = Polygon.from_bbox((-48.0, -16.0, -47.5, -15.5))
        
        results = RouteSegment.objects.filter(path__bboverlaps=bbox)
        
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().id, self.segment.id)
    
    def test_bbox_filter_outside(self):
        """Testa BBox fora da área do segmento"""
        # BBox sobre São Paulo
        bbox = Polygon.from_bbox((-46.8, -23.7, -46.3, -23.4))
        
        results = RouteSegment.objects.filter(path__bboverlaps=bbox)
        
        self.assertEqual(results.count(), 0)
```

### 2. Performance Benchmark

```python
# scripts/benchmark_spatial_queries.py
import time
from django.contrib.gis.geos import Polygon
from inventory.models_routes import RouteSegment

# Criar 10k segmentos de teste
print("Criando 10000 segmentos...")
# ... (código de criação)

# Benchmark: Query sem índice espacial
bbox = Polygon.from_bbox((-50.0, -17.0, -47.0, -15.0))

start = time.time()
results = list(RouteSegment.objects.filter(path__bboverlaps=bbox))
duration = time.time() - start

print(f"✅ Query BBox: {len(results)} segmentos em {duration*1000:.2f}ms")
# Esperado: <100ms com índice GiST
```

---

## 🚀 Deployment Checklist

### Pré-Deploy

- [ ] Backup completo do banco MySQL
- [ ] Provisionar PostgreSQL + PostGIS em staging
- [ ] Testar migration de dados em staging
- [ ] Validar queries espaciais funcionando
- [ ] Performance benchmark (query <100ms)

### Deploy

- [ ] Criar banco PostgreSQL + PostGIS em produção
- [ ] Dump dados MySQL → PostgreSQL (via Django dumpdata/loaddata)
- [ ] Executar migration 0010 (JSON → LineString)
- [ ] Criar índice espacial: `CREATE INDEX ON inventory_routesegment USING GIST (path);`
- [ ] Atualizar variáveis de ambiente (DB_ENGINE, DB_HOST, DB_PORT)
- [ ] Reiniciar workers Django/Celery
- [ ] Validar APIs respondendo

### Pós-Deploy

- [ ] Monitorar logs de erro
- [ ] Validar mapa carregando segmentos corretamente
- [ ] Performance: medir tempo de query BBox
- [ ] Rollback plan: restaurar backup MySQL se necessário

---

## 🔄 Estratégia de Rollback

### Opção 1: Manter Ambos os Campos (Recomendado)

```python
class RouteSegment(models.Model):
    # Campo antigo (mantido por compatibilidade)
    path_coordinates = models.JSONField(...)
    
    # Campo novo (PostGIS)
    path = gis_models.LineStringField(...)
```

**Vantagens:**
- Zero downtime
- Rollback instantâneo (mudar ENGINE de volta para MySQL)
- Ambos os campos sincronizados via signal

**Desvantagens:**
- Duplicação de dados (~20% aumento de espaço)

### Opção 2: Migration Irreversível

Remover `path_coordinates` após confirmar PostGIS estável (Phase 10.5).

---

## 📚 Referências

- [GeoDjango Documentation](https://docs.djangoproject.com/en/5.0/ref/contrib/gis/)
- [PostGIS Documentation](https://postgis.net/documentation/)
- [DRF-GIS (djangorestframework-gis)](https://github.com/openwisp/djangorestframework-gis)
- [Spatial Queries Cheat Sheet](https://postgis.net/workshops/postgis-intro/spatial_relationships.html)

---

**Última atualização:** 2025-11-11  
**Status:** Phase 10.1 pronto para implementação  
**Próximo:** Adicionar suporte GIS ao settings.py
