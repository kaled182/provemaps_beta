e responda em # Fiber Route Editor → OSP Management System

**Data**: 2024-11-28  
**Versão**: v3.0.0 (Planejamento)  
**Status**: 📋 Em Planejamento

---

## 🎯 Objetivo da Refatoração

Transformar o atual **Fiber Route Editor** (simples desenhador de linhas) em um **Sistema Completo de Cadastro de Rede Externa (OSP - Outside Plant)**, onde a rota deixa de ser apenas "geometria no mapa" e passa a ser uma **entidade viva de engenharia** composta por:

- **Geometria**: Path coordinates (traçado físico)
- **Elementos Físicos**: Caixas de emenda (CEO), reservas técnicas, CTOs
- **Lógica de Conexão**: Fusões de fibras, ramificações, sangrias (mid-span)
- **Rastreabilidade**: Trace completo da rede (de onde vem, para onde vai)

---

## 🔄 Mudança de Paradigma

### Antes (v2.2.0)
```
Usuário desenha linha → Salva com nome → FIM
```

**Limitações**:
- Cabo tratado como "linha morta" no mapa
- Sem representação de elementos físicos (CEOs, reservas)
- Impossível rastrear ramificações
- Gerenciamento de fusões isolado do traçado

### Agora (v3.0.0)
```
Usuário abre Cabo do Inventário 
  → Edita traçado (desenho/KML)
  → Adiciona elementos físicos sobre o traçado (CEO, reservas)
  → Gerencia fusões dentro desses elementos
  → Sistema rastreia automaticamente toda a árvore de derivações
```

**Benefícios**:
- ✅ Rota como **entidade de engenharia** completa
- ✅ Rastreabilidade de rede (trace de ponta a ponta)
- ✅ Cálculo automático de distâncias e atenuações
- ✅ Visualização linear e geográfica simultâneas
- ✅ Suporte a sangrias e ramificações (dropout)

---

## 📐 Plano de Execução

### Fase 1: Frontend Refactor (Editor Workspace)
**Objetivo**: Layout profissional tipo GIS com mapa + sidebar de propriedades

### Fase 2: Backend Infrastructure Models
**Objetivo**: Modelar elementos físicos da rede (CEO, reservas, CTOs)

### Fase 3: Conexão Lógica (Fusões)
**Objetivo**: Integrar fusões com elementos físicos (CEOs)

---

## 🏗️ FASE 1: Novo Layout (Editor Workspace)

### Arquitetura Visual

```
┌─────────────────────────────────────────────────────────────┐
│ Header: Nome do Cabo | Status | [Salvar] [Cancelar]         │
├───────────────────────────────────────┬─────────────────────┤
│                                       │   SIDEBAR (396px)   │
│                                       │                     │
│         MAPA (Tela Cheia)             │ ┌─────────────────┐ │
│                                       │ │ Propriedades    │ │
│  ┌──────────────────────┐             │ ├─────────────────┤ │
│  │ [👁️] [✏️] Modo      │             │ │ Cabo: CB-001    │ │
│  └──────────────────────┘             │ │ Status: Ativo   │ │
│                                       │ │ Extensão: 2.5km │ │
│    [Desenho do traçado com           │ └─────────────────┘ │
│     marcadores de CEOs e reservas]    │                     │
│                                       │ ┌─────────────────┐ │
│                                       │ │ Rota Física     │ │
│                                       │ ├─────────────────┤ │
│                                       │ │ Site A          │ │
│                                       │ │  ↓ 500m         │ │
│                                       │ │ Reserva-01 (30m)│ │
│                                       │ │  ↓ 700m         │ │
│                                       │ │ CEO-01          │ │
│                                       │ │  ├─→ Derivado-01│ │
│                                       │ │  ↓ 1300m        │ │
│                                       │ │ Site B          │ │
│                                       │ └─────────────────┘ │
└───────────────────────────────────────┴─────────────────────┘
```

### Componente: FiberOspEditor.vue

**Rota**: `/network/osp/fiber/:id`  
**Localização**: `frontend/src/features/ospManagement/FiberOspEditor.vue`

#### Template Structure

```vue
<template>
  <div class="flex h-screen overflow-hidden bg-gray-50">
    
    <!-- Área do Mapa (Esquerda - Expansível) -->
    <div class="flex-1 relative z-0">
      <FiberMapComponent 
        :cable="cable" 
        :mode="editorMode" 
        :infrastructure-points="infrastructurePoints"
        @element-click="selectElement"
        @context-menu="handleRightClick"
        @path-updated="onPathUpdated"
      />
      
      <!-- Toolbar Flutuante (Modo de Edição) -->
      <div class="absolute top-4 left-1/2 -translate-x-1/2 bg-white rounded-lg shadow-md p-1 flex gap-2 z-10">
        <button 
          @click="setMode('read')" 
          :class="{'bg-gray-200': mode === 'read'}"
          class="px-4 py-2 rounded hover:bg-gray-100 transition"
        >
          <i class="fas fa-lock"></i> Visualizar
        </button>
        <button 
          @click="setMode('edit')" 
          :class="{'bg-blue-100 text-blue-600': mode === 'edit'}"
          class="px-4 py-2 rounded hover:bg-blue-50 transition"
        >
          <i class="fas fa-pen"></i> Editar Traçado
        </button>
        <button 
          @click="setMode('infrastructure')" 
          :class="{'bg-purple-100 text-purple-600': mode === 'infrastructure'}"
          class="px-4 py-2 rounded hover:bg-purple-50 transition"
        >
          <i class="fas fa-boxes"></i> Infraestrutura
        </button>
      </div>
    </div>

    <!-- Sidebar Direito (Propriedades e Timeline) -->
    <div 
      class="w-96 bg-white border-l border-gray-200 flex flex-col z-10 shadow-xl"
      :class="{'hidden': sidebarCollapsed}"
    >
      
      <!-- Header do Cabo -->
      <div class="p-4 border-b bg-gradient-to-r from-gray-50 to-gray-100">
        <div class="flex items-center justify-between mb-2">
          <h2 class="font-bold text-lg text-gray-800">{{ cable.name }}</h2>
          <span 
            class="badge text-xs px-2 py-1 rounded-full"
            :class="statusClass(cable.status)"
          >
            {{ cable.status }}
          </span>
        </div>
        
        <!-- Métricas Principais -->
        <div class="grid grid-cols-2 gap-3 mt-3">
          <div class="bg-white rounded p-2 shadow-sm">
            <div class="text-xs text-gray-500">Extensão Total</div>
            <div class="font-mono font-bold text-blue-600">
              {{ formatDistance(cable.total_length) }}
            </div>
          </div>
          <div class="bg-white rounded p-2 shadow-sm">
            <div class="text-xs text-gray-500">Perfil</div>
            <div class="font-semibold text-gray-900">
              {{ cable.profile?.name || 'N/A' }}
            </div>
          </div>
        </div>
        
        <!-- Atenuação Estimada (se disponível) -->
        <div v-if="cable.estimated_attenuation" class="mt-2 text-xs text-gray-600">
          <i class="fas fa-signal-slash"></i>
          Atenuação estimada: <strong>{{ cable.estimated_attenuation }} dB</strong>
        </div>
      </div>

      <!-- Lista de Elementos da Rota (Timeline Vertical) -->
      <div class="flex-1 overflow-y-auto p-4">
        <h3 class="text-xs font-bold text-gray-400 uppercase mb-3 tracking-wider">
          Rota Física
        </h3>
        
        <RouteTimeline 
          :items="infrastructureTimeline" 
          @item-click="onTimelineItemClick"
          @item-edit="onTimelineItemEdit"
        />
      </div>
      
      <!-- Footer com Ações -->
      <div class="p-4 border-t bg-gray-50 flex gap-2">
        <button 
          @click="saveChanges" 
          :disabled="!hasChanges"
          class="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          <i class="fas fa-save"></i> Salvar
        </button>
        <button 
          @click="cancelChanges"
          class="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100 transition"
        >
          Cancelar
        </button>
      </div>
      
    </div>
    
    <!-- Botão para Toggle Sidebar (quando colapsada) -->
    <button 
      v-if="sidebarCollapsed"
      @click="sidebarCollapsed = false"
      class="absolute top-4 right-4 z-20 bg-white p-3 rounded-full shadow-lg hover:shadow-xl transition"
    >
      <i class="fas fa-info-circle text-blue-600"></i>
    </button>
    
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useApi } from '@/composables/useApi';
import FiberMapComponent from './components/FiberMapComponent.vue';
import RouteTimeline from './components/RouteTimeline.vue';

const route = useRoute();
const api = useApi();
const cableId = route.params.id;

// State
const cable = ref({});
const infrastructurePoints = ref([]);
const editorMode = ref('read'); // 'read' | 'edit' | 'infrastructure'
const sidebarCollapsed = ref(false);
const hasChanges = ref(false);

// Computed
const infrastructureTimeline = computed(() => {
  // Constrói timeline ordenado por distance_from_origin
  const items = [
    { type: 'site', name: cable.value.site_a_name, distance: 0, icon: 'building' }
  ];
  
  infrastructurePoints.value
    .sort((a, b) => a.distance_from_origin - b.distance_from_origin)
    .forEach(point => {
      items.push({
        type: point.type,
        name: point.name,
        distance: point.distance_from_origin,
        icon: getIconForType(point.type),
        metadata: point.metadata
      });
    });
  
  items.push({ 
    type: 'site', 
    name: cable.value.site_b_name, 
    distance: cable.value.total_length,
    icon: 'building' 
  });
  
  return items;
});

// Methods
const loadCableData = async () => {
  cable.value = await api.get(`/api/v1/fiber-cables/${cableId}/`);
  infrastructurePoints.value = await api.get(`/api/v1/fiber-cables/${cableId}/infrastructure/`);
};

const setMode = (mode) => {
  editorMode.value = mode;
};

const handleRightClick = (event) => {
  // Menu de contexto será implementado na Fase 1
  console.log('Right click', event);
};

const onPathUpdated = (newPath) => {
  cable.value.path_coordinates = newPath;
  hasChanges.value = true;
};

const saveChanges = async () => {
  // Salvar path + infrastructure points
  await api.post(`/api/v1/fiber-cables/${cableId}/update-path/`, {
    path: cable.value.path_coordinates
  });
  hasChanges.value = false;
};

const statusClass = (status) => {
  const classes = {
    'active': 'bg-green-100 text-green-800',
    'planned': 'bg-yellow-100 text-yellow-800',
    'dark': 'bg-gray-100 text-gray-800'
  };
  return classes[status] || 'bg-gray-100';
};

const formatDistance = (meters) => {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(2)} km`;
  }
  return `${meters.toFixed(0)} m`;
};

const getIconForType = (type) => {
  const icons = {
    'slack': 'infinity',
    'splice_box': 'box',
    'splitter_box': 'network-wired',
    'site': 'building'
  };
  return icons[type] || 'circle';
};

onMounted(() => {
  loadCableData();
});
</script>
```

---

## 🎛️ Interação: Menu de Contexto (Right-Click)

### Regras de Negócio

1. **Menu só aparece no modo `infrastructure`** (para evitar ações acidentais)
2. **Click deve ser sobre a linha do cabo** (não no vazio do mapa)
3. **Elementos criados devem "snapar" no traçado** usando PostGIS `ST_LineLocatePoint`

### Implementação: modules/contextMenu.js

```javascript
/**
 * Context Menu para adicionar elementos de infraestrutura
 * 
 * @param {LatLng} latlng - Posição do click no mapa
 * @param {number} cableId - ID do cabo sendo editado
 * @param {Object} cable - Objeto completo do cabo (para cálculos)
 * @returns {Array} Menu items
 */
export const getCableContextMenu = (latlng, cableId, cable) => {
  return [
    {
      label: '<i class="fas fa-box text-blue-600"></i> Adicionar Caixa de Emenda (CEO)',
      action: () => openModal('CreateSpliceBox', { 
        location: latlng, 
        cableId,
        estimatedDistance: calculateDistanceAlongPath(cable.path_coordinates, latlng)
      })
    },
    {
      label: '<i class="fas fa-infinity text-green-600"></i> Adicionar Reserva Técnica',
      action: () => createSlack(latlng, cableId) // Cria direto: reserva padrão de 30m
    },
    { 
      separator: true 
    },
    {
      label: '<i class="fas fa-network-wired text-purple-600"></i> Adicionar CTO (Splitter)',
      action: () => openModal('CreateSplitterBox', { location: latlng, cableId })
    },
    {
      label: '<i class="fas fa-cut text-orange-600"></i> Sangria (Mid-span Tap)',
      action: () => initiateMidSpan(latlng, cable)
    }
  ];
};

/**
 * Calcula distância ao longo do path até o ponto clicado
 * Útil para pré-popular o campo distance_from_origin
 */
function calculateDistanceAlongPath(pathCoords, clickPoint) {
  // Implementar usando Google Maps Geometry Library
  // ou enviar para backend PostGIS
  return 0; // placeholder
}

/**
 * Cria reserva técnica diretamente (sem modal)
 */
async function createSlack(latlng, cableId) {
  const api = useApi();
  
  const slackData = {
    cable: cableId,
    type: 'slack',
    name: `Reserva-${Date.now()}`, // Auto-naming
    location: {
      type: 'Point',
      coordinates: [latlng.lng, latlng.lat]
    },
    metadata: {
      length_added: 30 // metros padrão
    }
  };
  
  const result = await api.post('/api/v1/fiber-infrastructure/', slackData);
  
  // Recarregar lista de elementos
  EventBus.emit('infrastructure-added', result);
}
```

### Visualização do Menu (CSS)

```css
/* components/ContextMenu.vue - Estilo do menu */
.context-menu {
  position: absolute;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  min-width: 250px;
  z-index: 9999;
  padding: 4px 0;
}

.context-menu-item {
  padding: 10px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s;
}

.context-menu-item:hover {
  background: #f3f4f6;
}

.context-menu-separator {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 0;
}

.context-menu-item i {
  width: 20px;
  text-align: center;
}
```

---

## 🗄️ FASE 2: Modelagem Backend (Infrastructure)

### Model: FiberInfrastructure

**Arquivo**: `backend/inventory/models_infrastructure.py`

```python
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class FiberInfrastructure(models.Model):
    """
    Representa qualquer elemento físico na rota de um cabo.
    
    Tipos suportados:
    - slack: Reserva técnica (looping de cabo extra)
    - splice_box: Caixa de emenda (CEO) - onde ocorrem fusões
    - splitter_box: Caixa de atendimento (CTO) - onde ficam splitters ópticos
    
    A ordenação por distance_from_origin garante que possamos
    construir uma "timeline linear" da rota.
    """
    
    TYPES = [
        ('slack', 'Reserva Técnica'),
        ('splice_box', 'Caixa de Emenda (CEO)'),
        ('splitter_box', 'Caixa de Atendimento (CTO)'),
    ]
    
    # Relacionamento
    cable = models.ForeignKey(
        'FiberCable', 
        related_name='infrastructure_points', 
        on_delete=models.CASCADE
    )
    
    # Tipo e identificação
    type = models.CharField(max_length=20, choices=TYPES)
    name = models.CharField(
        max_length=100, 
        help_text="Ex: CEO-05-GANDRA, RES-001, CTO-CENTRO-01"
    )
    
    # Localização geográfica exata (WGS84)
    location = models.PointField(geography=True, srid=4326)
    
    # **CRÍTICO**: Distância sequencial a partir da Origem (Site A)
    # Calculado via PostGIS ST_LineLocatePoint ao salvar
    # Permite ordenação e cálculo de atenuação progressiva
    distance_from_origin = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="Metros a partir do Site A (calculado automaticamente)"
    )
    
    # Dados específicos (flexível por tipo)
    # Reserva: { "length_added": 30 }
    # CEO: { "capacity": 24, "model": "FOSC-400", "manufacturer": "Furukawa" }
    # CTO: { "splitter_ratio": "1:8", "model": "CTO-16" }
    metadata = models.JSONField(default=dict, blank=True)
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['cable', 'distance_from_origin']
        indexes = [
            models.Index(fields=['cable', 'distance_from_origin']),
            models.Index(fields=['type']),
        ]
        verbose_name = "Elemento de Infraestrutura"
        verbose_name_plural = "Elementos de Infraestrutura"
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.name} ({self.cable.name} @ {self.distance_from_origin}m)"
    
    def save(self, *args, **kwargs):
        """
        Override save para calcular distance_from_origin automaticamente
        usando PostGIS ST_LineLocatePoint + ST_Length
        """
        if not self.distance_from_origin:
            self.distance_from_origin = self._calculate_distance_from_origin()
        super().save(*args, **kwargs)
    
    def _calculate_distance_from_origin(self):
        """
        Calcula distância ao longo do path do cabo até este ponto.
        
        Usa PostGIS:
        - ST_LineLocatePoint: retorna fração (0.0 a 1.0) do path
        - ST_Length: comprimento total do path
        - Multiplica para obter distância em metros
        """
        from django.contrib.gis.geos import LineString
        from django.db import connection
        
        cable = self.cable
        if not cable.path_coordinates or len(cable.path_coordinates) < 2:
            return 0.0
        
        # Converte path_coordinates JSON para LineString
        coords = [(p['lng'], p['lat']) for p in cable.path_coordinates]
        line = LineString(coords, srid=4326)
        
        # Query PostGIS
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ST_Length(
                        ST_LineSubstring(
                            %s::geography,
                            0,
                            ST_LineLocatePoint(%s::geography, %s::geography)
                        )
                    )
            """, [line.wkt, line.wkt, self.location.wkt])
            
            result = cursor.fetchone()
            return float(result[0]) if result else 0.0
```

### Serializer: FiberInfrastructureSerializer

**Arquivo**: `backend/inventory/serializers.py` (adicionar)

```python
class FiberInfrastructureSerializer(serializers.ModelSerializer):
    """
    Serializer para elementos de infraestrutura na rota do cabo.
    """
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    # Location em formato GeoJSON
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = FiberInfrastructure
        fields = [
            'id',
            'cable',
            'type',
            'type_display',
            'name',
            'location',
            'distance_from_origin',
            'metadata',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'distance_from_origin', 'created_at', 'updated_at']
    
    def get_location(self, obj):
        """Retorna location como {lat, lng} para frontend"""
        if obj.location:
            return {
                'lat': obj.location.y,
                'lng': obj.location.x
            }
        return None
    
    def create(self, validated_data):
        """
        Override create para converter location {lat, lng} → Point
        """
        from django.contrib.gis.geos import Point
        
        location_data = self.initial_data.get('location')
        if location_data:
            validated_data['location'] = Point(
                location_data['lng'], 
                location_data['lat'],
                srid=4326
            )
        
        return super().create(validated_data)
```

### ViewSet: FiberInfrastructureViewSet

**Arquivo**: `backend/inventory/viewsets.py` (adicionar)

```python
class FiberInfrastructureViewSet(viewsets.ModelViewSet):
    """
    API para gerenciar elementos de infraestrutura (CEO, reservas, CTOs).
    """
    queryset = FiberInfrastructure.objects.select_related('cable').all()
    serializer_class = FiberInfrastructureSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filtrar por cable_id via query param"""
        queryset = super().get_queryset()
        cable_id = self.request.query_params.get('cable')
        
        if cable_id:
            queryset = queryset.filter(cable_id=cable_id)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='by-cable/(?P<cable_id>[^/.]+)')
    def by_cable(self, request, cable_id=None):
        """
        Retorna todos elementos de infraestrutura de um cabo específico,
        ordenados por distance_from_origin.
        """
        points = self.queryset.filter(cable_id=cable_id).order_by('distance_from_origin')
        serializer = self.get_serializer(points, many=True)
        
        return Response({
            'cable_id': cable_id,
            'count': points.count(),
            'total_slack_length': sum(
                p.metadata.get('length_added', 0) 
                for p in points if p.type == 'slack'
            ),
            'infrastructure_points': serializer.data
        })
```

### URLs

**Arquivo**: `backend/inventory/urls_api.py`

```python
from .viewsets import FiberInfrastructureViewSet

router.register('fiber-infrastructure', FiberInfrastructureViewSet, basename='fiber-infrastructure')
```

---

## 🔗 FASE 3: Conexão Lógica (Fusões + CEOs)

### Conceito: Fusões acontecem DENTRO de CEOs

**Modelo Mental**:
```
Cabo Principal (48FO)
  |
  |--- CEO-01 (km 1.2)
  |     |
  |     +--- Fusão: Fibra #12 (Cabo Principal) ←→ Fibra #1 (Cabo Derivado-01)
  |     +--- Fusão: Fibra #13 (Cabo Principal) ←→ Fibra #2 (Cabo Derivado-01)
  |
  |--- Site B
```

### Modal de Fusão (CEO Context)

Ao **clicar duas vezes em uma CEO no mapa**, abre modal:

```vue
<template>
  <div class="modal-fusao">
    <h3>Gerenciar Fusões: {{ ceo.name }}</h3>
    <p class="text-sm text-gray-500">
      Localização: Km {{ (ceo.distance_from_origin / 1000).toFixed(2) }} do traçado
    </p>
    
    <div class="grid grid-cols-2 gap-4 mt-4">
      <!-- Coluna Esquerda: Fibras do Cabo Principal -->
      <div>
        <h4 class="font-bold mb-2">Cabo: {{ mainCable.name }}</h4>
        <div class="fiber-list">
          <div 
            v-for="fiber in mainCable.fibers" 
            :key="fiber.id"
            class="fiber-item"
            :class="{ 'fused': fiber.fused_to }"
            @click="selectFiber(fiber, 'main')"
          >
            <span class="fiber-number">{{ fiber.number }}</span>
            <span class="fiber-status">{{ fiber.fused_to ? 'Fusionada' : 'Livre' }}</span>
          </div>
        </div>
      </div>
      
      <!-- Coluna Direita: Fibras de Cabos Derivados -->
      <div>
        <h4 class="font-bold mb-2">Cabos Derivados</h4>
        <select v-model="selectedDerivedCable" class="mb-2">
          <option v-for="c in derivedCables" :value="c">{{ c.name }}</option>
        </select>
        
        <div class="fiber-list">
          <div 
            v-for="fiber in selectedDerivedCable?.fibers" 
            :key="fiber.id"
            class="fiber-item"
            @click="selectFiber(fiber, 'derived')"
          >
            <span class="fiber-number">{{ fiber.number }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <div class="mt-4 flex gap-2">
      <button @click="createFusion" :disabled="!canFuse">
        <i class="fas fa-plug"></i> Fusionar Selecionadas
      </button>
      <button @click="close">Fechar</button>
    </div>
  </div>
</template>

<script setup>
const selectedMainFiber = ref(null);
const selectedDerivedFiber = ref(null);

const canFuse = computed(() => {
  return selectedMainFiber.value && 
         selectedDerivedFiber.value && 
         !selectedMainFiber.value.fused_to &&
         !selectedDerivedFiber.value.fused_to;
});

const createFusion = async () => {
  await api.post('/api/v1/fiber-strands/fuse/', {
    fiber_a: selectedMainFiber.value.id,
    fiber_b: selectedDerivedFiber.value.id,
    splice_location: ceo.value.id, // Referência à CEO
    loss_db: 0.1 // Perda padrão ou input do usuário
  });
  
  // Reload
  loadCeoFusions();
};
</script>
```

---

## 🌳 Algoritmo de Trace (Rastreabilidade)

### Objetivo
Dado um cabo principal, retornar toda a **árvore de derivações** (ramificações via fusões em CEOs).

### Lógica Recursiva

```python
# backend/inventory/usecases/trace.py

def trace_cable_network(cable_id: int) -> dict:
    """
    Rastreia toda a árvore de conexões a partir de um cabo raiz.
    
    Retorna estrutura hierárquica:
    {
        "cable": {...},
        "infrastructure": [...],
        "branches": [
            {
                "splice_box": {...},
                "derived_cable": {...},
                "fibers_used": [...]
            }
        ]
    }
    """
    from inventory.models import FiberCable, FiberInfrastructure, FiberStrand
    
    cable = FiberCable.objects.get(id=cable_id)
    infrastructure = list(cable.infrastructure_points.all().order_by('distance_from_origin'))
    
    branches = []
    
    # Para cada CEO (caixa de emenda)
    for point in infrastructure:
        if point.type != 'splice_box':
            continue
        
        # Buscar fusões que acontecem nesta CEO
        # (assumindo que FiberStrand tenha campo splice_location apontando para FiberInfrastructure)
        fusions = FiberStrand.objects.filter(
            cable=cable,
            fused_to__isnull=False,
            splice_location=point
        ).select_related('fused_to__cable')
        
        for fusion in fusions:
            derived_cable = fusion.fused_to.cable
            
            # Evitar loop infinito (se cabo derivado já foi visitado)
            if derived_cable.id == cable_id:
                continue
            
            # Recursão: traça o cabo derivado
            derived_trace = trace_cable_network(derived_cable.id)
            
            branches.append({
                'splice_box': {
                    'id': point.id,
                    'name': point.name,
                    'distance': point.distance_from_origin
                },
                'derived_cable': derived_trace,
                'fibers_used': [
                    {
                        'main_fiber': fusion.number,
                        'derived_fiber': fusion.fused_to.number,
                        'loss_db': fusion.loss_db
                    }
                ]
            })
    
    return {
        'cable': {
            'id': cable.id,
            'name': cable.name,
            'length': cable.length_km
        },
        'infrastructure': [
            {'name': p.name, 'type': p.type, 'distance': p.distance_from_origin}
            for p in infrastructure
        ],
        'branches': branches
    }
```

### Endpoint de Trace

```python
# backend/inventory/viewsets.py

class FiberCableViewSet(viewsets.ModelViewSet):
    
    @action(detail=True, methods=['get'])
    def trace(self, request, pk=None):
        """
        Retorna árvore completa de rastreabilidade do cabo.
        """
        from inventory.usecases.trace import trace_cable_network
        
        cable = self.get_object()
        trace_result = trace_cable_network(cable.id)
        
        return Response(trace_result)
```

**Uso**: `GET /api/v1/fiber-cables/123/trace/`

### Visualização no Sidebar

```
📍 Site A: POP Gandra
  |
  | ─── 500m ───
  |
  ♾️ Reserva-01 (30m extra)
  |
  | ─── 700m ───
  |
  📦 CEO-01: Sangria Principal
  |  ├─→ 🔌 Fusão: Fibra #12 → CB-DERIVADO-01
  |  │     └─→ 📦 CTO-CENTRO-01
  |  │           └─→ 🏠 Cliente Final
  |  └─→ 🔌 Fusão: Fibra #13 → CB-DERIVADO-02
  |
  | ─── 1300m ───
  |
  📍 Site B: Datacenter
```

---

## 📋 Roadmap de Implementação

### Sprint 1: Frontend Foundation (1 semana)
- [ ] Criar layout com sidebar + mapa (FiberOspEditor.vue)
- [ ] Implementar toggle Read/Edit/Infrastructure modes
- [ ] Criar componente RouteTimeline para lista de elementos
- [ ] Menu de contexto visual (mock, sem backend ainda)

### Sprint 2: Backend Infrastructure (1 semana)
- [ ] Criar model FiberInfrastructure + migration
- [ ] Implementar cálculo de distance_from_origin (PostGIS)
- [ ] Criar serializer + viewset + endpoints
- [ ] Testes unitários de criação de CEO/reserva

### Sprint 3: Integração Frontend-Backend (1 semana)
- [ ] Conectar menu de contexto com API real
- [ ] Implementar criação de CEO/reserva via modal
- [ ] Atualizar mapa em tempo real ao adicionar elementos
- [ ] Sidebar timeline carrega dados reais do banco

### Sprint 4: Fusões + Trace (2 semanas)
- [ ] Modal de fusão dentro de CEO
- [ ] Endpoint de fusão (criar/listar/deletar)
- [ ] Implementar algoritmo de trace recursivo
- [ ] Visualização da árvore de derivações no sidebar
- [ ] Teste com cenário complexo (3 níveis de ramificação)

### Sprint 5: Refinamentos (1 semana)
- [ ] Atenuação estimada end-to-end
- [ ] Export de trace como relatório PDF
- [ ] Validações de negócio (não permitir fusão se fibra já usada)
- [ ] Otimizações de performance (cache, queries)
- [ ] Documentação final

---

## 📊 Comparação: v2.2.0 → v3.0.0

| Aspecto | v2.2.0 (Atual) | v3.0.0 (OSP System) |
|---------|----------------|---------------------|
| **Traçado** | Linha no mapa | Linha + Elementos físicos |
| **Reservas** | Não suportado | Marcadores no mapa + metragem |
| **CEOs/Caixas** | Não existe | Posicionadas no traçado, gerenciam fusões |
| **Ramificações** | Impossível visualizar | Trace completo com árvore |
| **Distâncias** | Comprimento total | Segmentado (Site A → CEO → Site B) |
| **Atenuação** | Não calculada | Estimativa progressiva por segmento |
| **UX** | Modal simples | Workspace profissional tipo GIS |
| **Caso de Uso** | Cadastro básico | Gestão completa de rede externa |

---

## 🎓 Conceitos Técnicos Chave

### PostGIS: ST_LineLocatePoint
Retorna a **fração** (0.0 a 1.0) de um LineString onde um Point está mais próximo.

**Exemplo**:
```sql
SELECT ST_LineLocatePoint(
  ST_GeomFromText('LINESTRING(-47.1 -15.7, -47.2 -15.8)'),
  ST_GeomFromText('POINT(-47.15 -15.75)')
); 
-- Retorna: 0.5 (50% do caminho)
```

**Uso**: Multiplicar por `ST_Length(line)` para obter distância em metros.

### Timeline Linear vs Mapa Geográfico

**Linear** (sidebar):
- Ordem sequencial por distância
- Fácil visualizar "o que vem depois"
- Útil para planejamento de atenuação

**Geográfico** (mapa):
- Posição real no território
- Útil para logística de instalação
- Visualiza proximidade com outros ativos

Ambos são **complementares** e devem coexistir.

---

## 🔐 Validações de Negócio

### Ao criar CEO/Reserva
- ✅ Deve estar sobre o traçado do cabo (validar proximidade < 10m)
- ✅ `distance_from_origin` calculado automaticamente
- ✅ Nome único dentro do mesmo cabo
- ❌ Não permitir se cabo não tem traçado definido

### Ao criar Fusão
- ✅ Fibras devem estar livres (não fusionadas)
- ✅ Deve existir uma CEO no ponto de fusão
- ✅ Cabos devem ser diferentes (não fusionar consigo mesmo)
- ❌ Não permitir ciclos (cabo A → B → A)

### Ao deletar CEO
- ⚠️ Avisar se existem fusões (exigir confirmação)
- Opções: 
  - Deletar fusões junto (cascata)
  - Transferir fusões para outra CEO
  - Bloquear deleção

---

## 📖 Referências

- **PostGIS Documentation**: https://postgis.net/docs/ST_LineLocatePoint.html
- **OSP Standards**: TIA-758-B (Optical Fiber Outside Plant)
- **GIS UX Patterns**: QGIS, ArcGIS, Google Earth Pro
- **Fiber Trace Algorithms**: Bellman-Ford adaptado para grafos de fibra

---

**Status**: 📋 Documentação completa para início da implementação  
**Próximo Passo**: Usuário fornecerá detalhes específicos da primeira feature a ser implementada  
**Estimativa Total**: 6-7 semanas para OSP System completo

---

**Observação**: Este documento serve como **master plan**. Cada Sprint terá sua própria doc de implementação detalhada conforme avançarmos.
