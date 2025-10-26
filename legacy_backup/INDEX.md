# 📑 Legacy Files Index

Índice rápido de todos os arquivos arquivados com status e localização atual.

---

## 🗂️ Índice por Categoria

### **Views (Lógica de Apresentação)**

| # | Arquivo Legacy | Linhas | Localização Atual | Status |
|---|----------------|--------|-------------------|--------|
| 1 | `maps_view/views_old.py` | ~800 | `maps_view/views.py` | ✅ Substituído |
| 2 | `routes_builder/views_old.py` | ~600 | `routes_builder/views.py` | ✅ Substituído |

**Total:** 2 arquivos, ~1400 linhas de código

---

### **URLs (Roteamento)**

| # | Arquivo Legacy | Linhas | Localização Atual | Status |
|---|----------------|--------|-------------------|--------|
| 1 | `maps_view/urls_old.py` | ~50 | `maps_view/urls.py` | ✅ Substituído |
| 2 | `routes_builder/urls_old.py` | ~30 | `routes_builder/urls.py` | ✅ Substituído |

**Total:** 2 arquivos, ~80 linhas de código

---

### **Models (Estruturas de Dados)**

| # | Arquivo Legacy | Linhas | Localização Atual | Status |
|---|----------------|--------|-------------------|--------|
| 1 | `maps_view/models_old.py` | ~200 | `inventory/models.py` | ✅ Substituído |

**Total:** 1 arquivo, ~200 linhas de código

---

### **Services (Lógica de Negócio)**

| # | Arquivo Legacy | Linhas | Localização Atual | Status |
|---|----------------|--------|-------------------|--------|
| 1 | `maps_view/services_old/fiber_status.py` | ~325 | `zabbix_api/services/fiber_status.py` | ✅ Substituído |

**Total:** 1 arquivo, ~325 linhas de código

---

## 📊 Estatísticas Gerais

```
Total de arquivos arquivados: 6
Total estimado de linhas: ~2,005
Apps afetadas: 2 (maps_view, routes_builder)
Data do arquivamento: 26/10/2025
```

---

## 🔍 Localização Rápida

### **Por App**

#### **maps_view**
```
legacy_backup/maps_view/
├── views_old.py          → maps_view/views.py
├── urls_old.py           → maps_view/urls.py
├── models_old.py         → inventory/models.py
└── services_old/
    └── fiber_status.py   → zabbix_api/services/fiber_status.py
```

#### **routes_builder**
```
legacy_backup/routes_builder/
├── views_old.py          → routes_builder/views.py
└── urls_old.py           → routes_builder/urls.py
```

---

## 🔎 Busca Rápida por Funcionalidade

| Procurando por... | Estava em... | Agora está em... |
|-------------------|--------------|------------------|
| Status de fibras | `services_old/fiber_status.py` | `zabbix_api/services/fiber_status.py` |
| Dashboard principal | `maps_view/views_old.py` | `maps_view/views.py` |
| Mapa de rede | `maps_view/views_old.py` | `maps_view/views.py` |
| Construtor de rotas | `routes_builder/views_old.py` | `routes_builder/views.py` |
| API de fibras | `routes_builder/views_old.py` | `routes_builder/views.py` |
| Modelos Device/Site | `maps_view/models_old.py` | `inventory/models.py` |
| URLs do dashboard | `maps_view/urls_old.py` | `maps_view/urls.py` |
| URLs de rotas | `routes_builder/urls_old.py` | `routes_builder/urls.py` |

---

## 📝 Detalhes dos Arquivos

### **1. maps_view/views_old.py**
```
Funções principais:
- index()                    → maps_view/views.py::index()
- network_map()              → maps_view/views.py::network_map()
- device_map()               → maps_view/views.py::device_map()
- host_fiber_status()        → maps_view/views.py::host_fiber_status()
- cable_events()             → maps_view/views.py::cable_events()
- sites_list()               → maps_view/views.py::sites_list()
- devices_list()             → maps_view/views.py::devices_list()

Dependências legacy:
- zabbix_api.services.fiber_status (legacy)
- zabbix_api.services.zabbix_service

Status: ⚠️ Contém lógica desatualizada, não usar
```

### **2. routes_builder/views_old.py**
```
Funções principais:
- route_map()                → routes_builder/views.py::route_map()
- fiber_route_builder()      → routes_builder/views.py::fiber_route_builder()
- get_fibers()               → routes_builder/views.py::get_fibers()
- create_fiber()             → routes_builder/views.py::create_fiber()
- update_fiber()             → routes_builder/views.py::update_fiber()
- delete_fiber()             → routes_builder/views.py::delete_fiber()

Status: ⚠️ API desatualizada, usar versão RESTful
```

### **3. maps_view/urls_old.py**
```
Rotas antigas:
- '' (index)
- 'network/' (network_map)
- 'device/<int:id>/' (device_map)

Status: ⚠️ Padrões de URL mudaram
```

### **4. routes_builder/urls_old.py**
```
Rotas antigas:
- '' (route_map)
- 'builder/' (fiber_route_builder)
- 'api/fibers/' (get_fibers)

Status: ⚠️ Endpoints RESTful na versão atual
```

### **5. maps_view/models_old.py**
```
Modelos antigos:
- Device (managed=False)
- Site (managed=False)
- Port (managed=False)

Problemas:
- Não persistia no banco (managed=False)
- Estrutura desatualizada
- Sem relacionamentos FK corretos

Status: ⚠️ Usar inventory/models.py (managed=True)
```

### **6. maps_view/services_old/fiber_status.py**
```
Funções principais:
- fetch_interface_status_advanced()
- combine_cable_status()
- evaluate_cable_status_for_cable()

Movido para: zabbix_api/services/fiber_status.py
Motivo: Arquitetura - services de Zabbix devem estar em zabbix_api/

Status: ✅ Código duplicado - usar versão em zabbix_api/
```

---

## 🚦 Status dos Arquivos

### ✅ **Seguros para Ignorar** (não são usados)
- Todos os 6 arquivos arquivados
- Nenhum import ativo encontrado

### ⚠️ **Mantidos por Referência** (não usar em produção)
- Todos os arquivos em `legacy_backup/`
- Consultar apenas para entender mudanças históricas

### ❌ **Não Restaurar** (causarão problemas)
- Qualquer arquivo `*_old.py`
- Qualquer código em `services_old/`

---

## 🔗 Links Rápidos

- [README Principal](./README.md) - Visão geral do arquivamento
- [Guia de Migração](./MIGRATION_GUIDE.md) - Como migrar código
- [Estrutura Atual](#) - Ver AGENTS.md no diretório raiz
- [Documentação API](#) - Ver API_DOCUMENTATION.md

---

## 📅 Histórico de Modificações

| Data | Evento | Responsável |
|------|--------|-------------|
| 26/10/2025 | Arquivos movidos para legacy_backup | Copilot Assistant |
| 26/10/2025 | Documentação criada | Copilot Assistant |
| 26/10/2025 | Validação de imports | Copilot Assistant |

---

**Gerado automaticamente em:** 26 de Outubro de 2025  
**Versão:** 1.0  
**Status:** ✅ Completo
