# Sistema de Mapas Personalizados - MapsProveFiber

## 🎯 Visão Geral

Sistema que permite criar múltiplos mapas customizados, cada um com sua própria seleção de equipamentos, cabos, câmeras e racks do inventário.

## 📍 Localização

```
/monitoring/backbone/          → Lista de mapas + criação
/monitoring/:category/map/:id  → Visualizador do mapa
```

## 🏗️ Arquitetura

### Backend

#### Modelo: `CustomMap`
```python
# backend/inventory/models.py
class CustomMap(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey('auth.User')
    
    # Seleções (JSON com IDs)
    selected_devices = LenientJSONField(default=list)
    selected_cables = LenientJSONField(default=list)
    selected_cameras = LenientJSONField(default=list)
    selected_racks = LenientJSONField(default=list)
```

#### API Endpoints
```python
# backend/inventory/api_custom_maps.py

# Lista e criação
GET  /api/v1/maps/custom/
POST /api/v1/maps/custom/

# Detalhes, edição e remoção
GET    /api/v1/maps/custom/<id>/
PUT    /api/v1/maps/custom/<id>/
DELETE /api/v1/maps/custom/<id>/

# Salvar itens selecionados
POST /api/v1/maps/custom/<id>/items/

# Dispositivos com localização
GET /api/v1/maps/devices-location/
```

### Frontend

#### Componentes

**1. CustomMapsManager.vue**
- Lista todos os mapas criados
- Botão "Criar Novo Mapa"
- Modal de criação/edição
- Card para cada mapa mostrando:
  - Nome e descrição
  - Quantidade de itens
  - Ações (editar, excluir)
- Mapa padrão (sempre visível)

**2. CustomMapViewer.vue**
- Visualizador do mapa com Google Maps
- Toolbar superior:
  - Botão voltar
  - Título do mapa
  - Botão "Gerenciar Itens"
  - Botão fullscreen
- Painel lateral deslizante:
  - Abas: Devices | Cables | Cameras | Racks
  - Busca de itens
  - Checkboxes para selecionar
  - Botão "Selecionar Todos"
  - Botão "Salvar"
- Legenda de status
- Markers no mapa (Google Maps)

## 🎨 Design Visual

### Estilo Glassmorphism
```css
background: rgba(30, 33, 57, 0.95);
backdrop-filter: blur(10px);
border: 1px solid rgba(255, 255, 255, 0.1);
```

### Cores
- **Primary**: #10b981 (Verde)
- **Background**: #1a1d2e (Azul escuro)
- **Cards**: rgba(255, 255, 255, 0.05)
- **Borders**: rgba(255, 255, 255, 0.1)

### Status dos Dispositivos
- 🟢 **Online**: #10b981
- 🟡 **Warning**: #f59e0b
- 🔴 **Critical**: #ef4444
- ⚫ **Offline**: #6b7280

## 📊 Fluxo de Uso

### 1. Criar Novo Mapa
```
1. Acessar /monitoring/backbone/
2. Clicar em "Criar Novo Mapa"
3. Preencher:
   - Nome do mapa
   - Descrição (opcional)
   - Categoria (backbone/gpon/dwdm/custom)
   - Público ou privado
4. Clicar em "Criar Mapa"
```

### 2. Selecionar Itens
```
1. Clicar no card do mapa
2. Clicar em "Gerenciar Itens"
3. Selecionar aba (Devices/Cables/Cameras/Racks)
4. Marcar checkboxes dos itens desejados
5. Clicar em "Salvar"
```

### 3. Visualizar no Mapa
```
- Markers aparecem automaticamente
- Clicar no marker para ver detalhes
- Botão "foco" para centralizar item
- Legenda mostra status
```

## 🔐 Permissões

### Criação
- Qualquer usuário autenticado pode criar mapas

### Visualização
- **Mapas públicos**: Todos os usuários
- **Mapas privados**: Apenas o criador

### Edição/Exclusão
- Apenas o criador do mapa

## 🗄️ Estrutura de Dados

### Payload de Criação
```json
{
  "name": "Backbone Principal",
  "description": "Equipamentos do backbone principal",
  "category": "backbone",
  "is_public": true
}
```

### Payload de Itens Selecionados
```json
{
  "selected_items": {
    "devices": [1, 2, 3],
    "cables": [10, 11],
    "cameras": [],
    "racks": [5]
  }
}
```

### Response do Mapa
```json
{
  "map": {
    "id": 1,
    "name": "Backbone Principal",
    "description": "...",
    "category": "backbone",
    "is_public": true,
    "items_count": 15,
    "devices_count": 8,
    "cables_count": 12,
    "cameras_count": 0
  },
  "selected_items": {
    "devices": [1, 2, 3],
    "cables": [10, 11],
    "cameras": [],
    "racks": [5]
  }
}
```

## 🚀 Implementação

### Migration
```bash
cd backend
python manage.py migrate inventory
```

### Rotas Frontend
```javascript
// frontend/src/router/index.js
{
  path: '/monitoring/backbone',
  component: () => import('@/views/monitoring/CustomMapsManager.vue')
},
{
  path: '/monitoring/:category/map/:mapId',
  component: () => import('@/views/monitoring/CustomMapViewer.vue')
}
```

### Rotas Backend
```python
# backend/inventory/urls.py
path('api/v1/maps/custom/', custom_maps_list),
path('api/v1/maps/custom/<int:map_id>/', custom_map_detail),
path('api/v1/maps/custom/<int:map_id>/items/', save_map_items),
```

## 🎯 Próximos Passos

### Fase 1: MVP ✅
- [x] Modelo CustomMap
- [x] API CRUD de mapas
- [x] Interface de listagem
- [x] Modal de criação
- [x] Visualizador com Google Maps
- [x] Painel de seleção de itens

### Fase 2: Melhorias (Futuro)
- [ ] Filtros avançados (por status, tipo, localização)
- [ ] Compartilhamento de mapas
- [ ] Exportar mapa como imagem
- [ ] Rotas entre devices
- [ ] Clusters de markers
- [ ] Heatmaps
- [ ] Edição de posição manual
- [ ] Camadas customizadas

### Fase 3: Integrações (Futuro)
- [ ] Alertas em tempo real nos markers
- [ ] Métricas Zabbix nos popups
- [ ] Links para câmeras
- [ ] Status de cabos ópticos
- [ ] Alarmes visuais

## 📝 Observações

### Mapa Padrão
- ID: "default"
- Sempre presente
- Mostra todos os equipamentos
- Não pode ser editado ou excluído

### Categorias
- **backbone**: Infraestrutura backbone
- **gpon**: Redes GPON
- **dwdm**: Sistemas DWDM
- **custom**: Mapas personalizados

### Google Maps
- Usa a integração existente
- Estilos dark mode
- Markers personalizados por status
- InfoWindow com detalhes

## 🐛 Troubleshooting

### Markers não aparecem
```javascript
// Verificar se devices têm latitude/longitude
const devices = await get('/api/v1/maps/devices-location/')
console.log(devices) // Deve ter lat/lng
```

### Erro ao salvar itens
```python
# Verificar permissões
if custom_map.created_by != request.user:
    return Response({'error': 'Sem permissão'}, status=403)
```

### Migration error
```bash
# Executar manualmente
python manage.py migrate inventory 0050_add_custom_maps
```

## 📚 Referências

- **Playbook**: `doc/process/AGENTS.md`
- **Modelo**: `backend/inventory/models.py` (CustomMap)
- **API**: `backend/inventory/api_custom_maps.py`
- **Manager**: `frontend/src/views/monitoring/CustomMapsManager.vue`
- **Viewer**: `frontend/src/views/monitoring/CustomMapViewer.vue`
- **Migration**: `backend/inventory/migrations/0050_add_custom_maps.py`
