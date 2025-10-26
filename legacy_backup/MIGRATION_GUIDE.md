# 🔄 Legacy to Current Code Migration Guide

Este guia ajuda desenvolvedores a encontrar o código atual correspondente aos arquivos legacy arquivados.

---

## 📊 Mapeamento Rápido

### **maps_view**

| Arquivo Legacy | Arquivo Atual | Status | Notas |
|----------------|---------------|--------|-------|
| `views_old.py` → `index()` | `maps_view/views.py` → `index()` | ✅ Migrado | Refatorado com cache SWR |
| `views_old.py` → `network_map()` | `maps_view/views.py` → `network_map()` | ✅ Migrado | Usa novo template |
| `views_old.py` → `device_map()` | `maps_view/views.py` → `device_map()` | ✅ Migrado | Otimizado com queries |
| `views_old.py` → `host_fiber_status()` | `maps_view/views.py` → `host_fiber_status()` | ✅ Migrado | Cache Redis ativo |
| `urls_old.py` | `maps_view/urls.py` | ✅ Migrado | Rotas reorganizadas |
| `models_old.py` | `inventory/models.py` | ✅ Migrado | Modelos persistentes |
| `services_old/fiber_status.py` | `zabbix_api/services/fiber_status.py` | ✅ Migrado | Arquitetura corrigida |

### **routes_builder**

| Arquivo Legacy | Arquivo Atual | Status | Notas |
|----------------|---------------|--------|-------|
| `views_old.py` → `route_map()` | `routes_builder/views.py` → `route_map()` | ✅ Migrado | UI melhorada |
| `views_old.py` → `fiber_route_builder()` | `routes_builder/views.py` → `fiber_route_builder()` | ✅ Migrado | API REST |
| `urls_old.py` | `routes_builder/urls.py` | ✅ Migrado | Endpoints RESTful |

### **zabbix_api/services**

| Código Legacy | Código Atual | Status | Notas |
|---------------|--------------|--------|-------|
| `maps_view/services_old/fiber_status.py` | `zabbix_api/services/fiber_status.py` | ✅ Migrado | Lógica centralizada |
| `zabbix_api/services/zabbix_client.py` | `zabbix_api/client.py` | ⚠️ Refatorado | Cliente resiliente |
| N/A | `zabbix_api/services/zabbix_service.py` | ✅ Ativo | Camada de serviço |

---

## 🔍 Como Encontrar Funcionalidades

### **Buscar por Nome de Função**

```powershell
# Encontrar onde uma função foi movida
grep -r "def nome_da_funcao" --include="*.py" --exclude-dir=legacy_backup

# Exemplo: Buscar função 'fetch_interface_status'
grep -r "def fetch_interface_status" --include="*.py" --exclude-dir=legacy_backup
# Resultado: zabbix_api/services/fiber_status.py
```

### **Buscar por Funcionalidade**

| Funcionalidade | Localização Atual |
|----------------|-------------------|
| **Status de fibras** | `zabbix_api/services/fiber_status.py` |
| **Integração Zabbix** | `zabbix_api/client.py` + `zabbix_api/services/zabbix_service.py` |
| **Mapa de rede** | `maps_view/views.py` → `network_map()` |
| **Dashboard principal** | `maps_view/views.py` → `index()` |
| **Construtor de rotas** | `routes_builder/views.py` → `fiber_route_builder()` |
| **API de fibras** | `routes_builder/views.py` (endpoints REST) |
| **Modelos de inventário** | `inventory/models.py` (Site, Device, Port) |
| **Cache SWR** | `maps_view/cache_swr.py` |
| **WebSocket realtime** | `maps_view/realtime/consumers.py` |

---

## 🛠️ Exemplos de Migração de Código

### **Exemplo 1: Import de Serviço Zabbix**

#### ❌ Legacy (ANTIGO - NÃO USAR)
```python
from maps_view.services_old.fiber_status import fetch_interface_status_advanced
from zabbix_api.services.zabbix_client import zabbix_request  # Legacy
```

#### ✅ Atual (USAR)
```python
from zabbix_api.services.fiber_status import fetch_interface_status_advanced
from zabbix_api.services.zabbix_service import zabbix_request
```

---

### **Exemplo 2: View de Mapa de Rede**

#### ❌ Legacy (ANTIGO)
```python
# legacy_backup/maps_view/views_old.py
from django.shortcuts import render
from zabbix_api.services.zabbix_service import zabbix_request

def network_map(request):
    # Código antigo sem cache
    hosts = zabbix_request('host.get', {...})
    return render(request, 'old_template.html', {'hosts': hosts})
```

#### ✅ Atual (USAR)
```python
# maps_view/views.py
from django.shortcuts import render
from django.core.cache import cache
from zabbix_api.services.zabbix_service import zabbix_request

def network_map(request):
    # Código novo com cache SWR
    cache_key = 'network_hosts'
    hosts = cache.get(cache_key)
    if not hosts:
        hosts = zabbix_request('host.get', {...})
        cache.set(cache_key, hosts, timeout=300)  # 5 min
    return render(request, 'maps_view/network_map.html', {'hosts': hosts})
```

---

### **Exemplo 3: Modelos de Inventário**

#### ❌ Legacy (ANTIGO)
```python
# legacy_backup/maps_view/models_old.py
class Device(models.Model):
    class Meta:
        managed = False  # ❌ Não persiste no DB
        db_table = 'legacy_device'
```

#### ✅ Atual (USAR)
```python
# inventory/models.py
class Device(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    device_type = models.CharField(max_length=50)
    # ... campos completos com managed=True
    
    class Meta:
        managed = True  # ✅ Persiste no DB
        db_table = 'inventory_device'
```

---

### **Exemplo 4: URLconf**

#### ❌ Legacy (ANTIGO)
```python
# legacy_backup/maps_view/urls_old.py
urlpatterns = [
    path('', views_old.index, name='index'),
    path('map/', views_old.network_map, name='network_map'),
]
```

#### ✅ Atual (USAR)
```python
# maps_view/urls.py
from . import views

urlpatterns = [
    path('', views.index, name='maps_view_index'),
    path('network/', views.network_map, name='network_map'),
    path('device/<int:device_id>/', views.device_map, name='device_map'),
    # ... rotas organizadas com namespaces
]
```

---

## 📦 Dependências Mudadas

### **Imports que Mudaram**

| Legacy Import | Novo Import | Motivo |
|---------------|-------------|--------|
| `from maps_view.services_old import *` | `from zabbix_api.services import *` | Arquitetura reorganizada |
| `from zabbix_api.services.zabbix_client import zabbix_request` | `from zabbix_api.services.zabbix_service import zabbix_request` | Wrapper seguro |
| `from maps_view.models_old import Device` | `from inventory.models import Device` | Modelos persistentes |

---

## 🧪 Testes de Migração

### **Checklist para Validar Migração**

```bash
# 1. Buscar imports de código legacy
grep -r "from.*_old" --include="*.py" --exclude-dir=legacy_backup
grep -r "import.*legacy" --include="*.py" --exclude-dir=legacy_backup

# 2. Verificar se não há referências a services_old
grep -r "services_old" --include="*.py" --exclude-dir=legacy_backup

# 3. Testar imports atuais
docker exec mapsprovefiber-web-1 python manage.py shell -c "
from zabbix_api.services.fiber_status import fetch_interface_status_advanced
from zabbix_api.services.zabbix_service import zabbix_request
from maps_view.views import index, network_map
from routes_builder.views import fiber_route_builder
print('✅ Todos os imports funcionam!')
"

# 4. Executar suite de testes
pytest -v
```

---

## 📚 Recursos para Migração

### **Arquitetura Atual**

```
mapsprovefiber/
├── core/                       # Settings e configuração raiz
├── maps_view/                  # Dashboard e mapas de rede
│   ├── views.py               # ✅ Views principais (usar)
│   ├── urls.py                # ✅ Rotas atuais (usar)
│   ├── templates/             # ✅ Templates atualizados
│   └── cache_swr.py           # Cache com Stale-While-Revalidate
├── routes_builder/             # Construtor de rotas de fibra
│   ├── views.py               # ✅ API REST e UI (usar)
│   ├── urls.py                # ✅ Endpoints RESTful (usar)
│   └── models.py              # FiberCable, FiberEvent
├── inventory/                  # Modelos persistentes
│   └── models.py              # ✅ Site, Device, Port (usar)
├── zabbix_api/                 # Integração Zabbix
│   ├── client.py              # ✅ Cliente resiliente (usar)
│   ├── services/              # ✅ Camada de serviço (usar)
│   │   ├── zabbix_service.py # Wrapper com cache
│   │   └── fiber_status.py   # Lógica de status
│   └── usecases/              # Casos de uso de negócio
└── legacy_backup/              # ⚠️ NÃO USAR (apenas referência)
```

### **Documentação Relacionada**

- **AGENTS.md** - Guia completo de desenvolvimento
- **API_DOCUMENTATION.md** - Documentação de APIs
- **docs/refactor_fibers.md** - Histórico de refatoração
- **CHANGELOG_*.md** - Mudanças por versão

---

## ❓ FAQ - Perguntas Frequentes

### **P: Posso usar código de `legacy_backup/` em produção?**
**R:** ❌ **NÃO!** Código legacy não é testado, pode conter bugs e não segue a arquitetura atual.

### **P: Onde está a lógica de status de fibra?**
**R:** ✅ `zabbix_api/services/fiber_status.py` (código ativo e testado)

### **P: Preciso de uma função que estava em `views_old.py`, onde encontro?**
**R:** 
1. Verifique este guia (tabela de mapeamento)
2. Busque por nome: `grep -r "def nome_funcao" --include="*.py"`
3. Consulte `maps_view/views.py` (provavelmente foi refatorada)

### **P: Os testes estão falhando após migração, o que fazer?**
**R:**
1. Verifique imports: não use `*_old.py`
2. Atualize paths: `maps_view.services_old` → `zabbix_api.services`
3. Execute: `pytest -v` para ver erros detalhados
4. Consulte logs: `docker compose logs web`

### **P: Posso deletar `legacy_backup/`?**
**R:** ⚠️ Aguardar 60 dias (até 25/12/2025) para validação completa.

---

## 🆘 Suporte

Se você encontrou código que não está documentado aqui:

1. **Abra uma issue** descrevendo o código procurado
2. **Consulte Git history** antes do arquivamento: `git log --all --full-history -- path/to/file`
3. **Pergunte no canal de desenvolvimento** da equipe

---

**Última Atualização:** 26 de Outubro de 2025  
**Versão do Guia:** 1.0  
**Status:** ✅ Completo e validado
