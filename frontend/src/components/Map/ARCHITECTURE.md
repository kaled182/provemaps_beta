# 📐 Arquitetura do Sistema Unificado de Mapas

## Diagrama de Componentes

```mermaid
graph TB
    subgraph "Vue Components"
        DashboardView[DashboardView.vue<br/>Monitoring Context]
        NetworkDesignView[NetworkDesignView.vue<br/>Design Context]
        AnalysisView[AnalysisView.vue<br/>Analysis Context]
    end
    
    subgraph "Unified Map System"
        UnifiedMap[UnifiedMapView.vue<br/>Wrapper Component]
        MapService[useMapService.js<br/>Core Composable]
        Registry[Plugin Registry]
    end
    
    subgraph "Map Plugins"
        SegmentsPlugin[segmentsPlugin.js<br/>Fiber Segments]
        DevicesPlugin[devicesPlugin.js<br/>Device Markers]
        DrawingPlugin[drawingPlugin.js<br/>Drawing Tools]
        ContextPlugin[contextMenuPlugin.js<br/>Context Menu]
    end
    
    subgraph "External APIs"
        GoogleMaps[Google Maps API]
        Backend[Backend REST APIs]
    end
    
    DashboardView --> UnifiedMap
    NetworkDesignView --> UnifiedMap
    AnalysisView --> UnifiedMap
    
    UnifiedMap --> MapService
    MapService --> Registry
    Registry --> SegmentsPlugin
    Registry --> DevicesPlugin
    Registry --> DrawingPlugin
    Registry --> ContextPlugin
    
    MapService --> GoogleMaps
    SegmentsPlugin --> Backend
    DevicesPlugin --> Backend
    
    style UnifiedMap fill:#3b82f6,color:#fff
    style MapService fill:#10b981,color:#fff
    style Registry fill:#f59e0b,color:#fff
    style SegmentsPlugin fill:#8b5cf6,color:#fff
    style DevicesPlugin fill:#8b5cf6,color:#fff
    style DrawingPlugin fill:#8b5cf6,color:#fff
    style ContextPlugin fill:#8b5cf6,color:#fff
```

## Fluxo de Dados - Monitoring Context

```mermaid
sequenceDiagram
    participant User
    participant DashboardView
    participant UnifiedMap
    participant MapService
    participant SegmentsPlugin
    participant DevicesPlugin
    participant Backend
    participant GoogleMaps

    User->>DashboardView: Acessa /monitoring/backbone
    DashboardView->>UnifiedMap: <UnifiedMapView mode="monitoring" :plugins="['segments', 'devices']">
    UnifiedMap->>MapService: initMap(container, options)
    MapService->>GoogleMaps: new google.maps.Map()
    GoogleMaps-->>MapService: map instance
    MapService-->>UnifiedMap: @map-ready
    
    UnifiedMap->>MapService: loadPlugin('segments', options)
    MapService->>SegmentsPlugin: createSegmentsPlugin(context, options)
    SegmentsPlugin-->>MapService: plugin instance
    MapService-->>UnifiedMap: @plugin-loaded('segments')
    
    UnifiedMap->>MapService: loadPlugin('devices', options)
    MapService->>DevicesPlugin: createDevicesPlugin(context, options)
    DevicesPlugin-->>MapService: plugin instance
    MapService-->>UnifiedMap: @plugin-loaded('devices')
    
    DashboardView->>UnifiedMap: getPlugin('segments')
    UnifiedMap-->>DashboardView: segmentsPlugin
    DashboardView->>Backend: fetch segments data
    Backend-->>DashboardView: segments[]
    DashboardView->>SegmentsPlugin: drawSegments(segments)
    SegmentsPlugin->>GoogleMaps: new Polyline()
    
    DashboardView->>Backend: fetch devices data
    Backend-->>DashboardView: devices[]
    DashboardView->>DevicesPlugin: drawDevices(devices)
    DevicesPlugin->>GoogleMaps: new Marker()
    
    User->>GoogleMaps: Click on segment
    GoogleMaps->>SegmentsPlugin: click event
    SegmentsPlugin->>DashboardView: onSegmentClick(segment)
    DashboardView->>User: Show segment details
```

## Fluxo de Dados - Network Design Context

```mermaid
sequenceDiagram
    participant User
    participant NetworkDesignView
    participant UnifiedMap
    participant MapService
    participant DrawingPlugin
    participant ContextMenuPlugin
    participant GoogleMaps

    User->>NetworkDesignView: Acessa /NetworkDesign/
    NetworkDesignView->>UnifiedMap: <UnifiedMapView mode="design" :plugins="['drawing', 'contextMenu']">
    UnifiedMap->>MapService: initMap(container, options)
    MapService->>GoogleMaps: new google.maps.Map()
    GoogleMaps-->>MapService: map instance
    
    UnifiedMap->>MapService: loadPlugin('drawing', options)
    MapService->>DrawingPlugin: createDrawingPlugin(context, options)
    DrawingPlugin-->>MapService: plugin instance
    
    UnifiedMap->>MapService: loadPlugin('contextMenu', options)
    MapService->>ContextMenuPlugin: createContextMenuPlugin(context, options)
    ContextMenuPlugin-->>MapService: plugin instance
    
    User->>NetworkDesignView: Click "Start Drawing"
    NetworkDesignView->>DrawingPlugin: startDrawing()
    DrawingPlugin->>GoogleMaps: addListener('click', handler)
    
    User->>GoogleMaps: Click on map to add point
    GoogleMaps->>DrawingPlugin: click event
    DrawingPlugin->>GoogleMaps: new Marker(draggable)
    DrawingPlugin->>GoogleMaps: polyline.setPath([...points])
    DrawingPlugin->>NetworkDesignView: onPathChange(coords, distance)
    NetworkDesignView->>User: Update distance display
    
    User->>GoogleMaps: Right-click on map
    GoogleMaps->>ContextMenuPlugin: rightclick event
    ContextMenuPlugin->>User: Show context menu
    User->>ContextMenuPlugin: Click "Save Route"
    ContextMenuPlugin->>NetworkDesignView: onItemClick('save-route')
    NetworkDesignView->>DrawingPlugin: getPathCoordinates()
    DrawingPlugin-->>NetworkDesignView: coordinates[]
    NetworkDesignView->>Backend: POST /api/v1/cables/
```

## Arquitetura de Plugins

```mermaid
classDiagram
    class MapService {
        -Map mapInstance
        -Map loadedPlugins
        +initMap(container, options) Promise~Map~
        +loadPlugin(name, options) Promise~Plugin~
        +unloadPlugin(name) void
        +getPlugin(name) Plugin
        +cleanup() void
    }
    
    class PluginRegistry {
        -Map plugins
        +register(name, factory) void
        +get(name) Function
        +has(name) boolean
    }
    
    class PluginBase {
        <<interface>>
        +cleanup() void
    }
    
    class SegmentsPlugin {
        -Map polylines
        -InfoWindow infoWindow
        +drawSegments(segments[]) void
        +showSegmentInfo(segment, position) void
        +clearSegments() void
        +fitBounds() void
        +cleanup() void
    }
    
    class DevicesPlugin {
        -Map markers
        -MarkerClusterer clusterer
        +drawDevices(devices[]) void
        +showDeviceInfo(device, marker) void
        +focusDevice(deviceId, zoom) void
        +clearDevices() void
        +cleanup() void
    }
    
    class DrawingPlugin {
        -Polyline polyline
        -Marker[] markers
        -LatLng[] path
        +startDrawing() void
        +stopDrawing() void
        +addPoint(latLng) Marker
        +removePoint(index) void
        +setPath(coords[]) void
        +getPathCoordinates() Object[]
        +getDistance() number
        +clearPath() void
        +cleanup() void
    }
    
    class ContextMenuPlugin {
        -HTMLElement menuElement
        -MenuItem[] menuItems
        +showMenu(latLng, event) void
        +hideMenu() void
        +addMenuItem(item) void
        +removeMenuItem(itemId) void
        +cleanup() void
    }
    
    MapService --> PluginRegistry : uses
    PluginRegistry --> PluginBase : manages
    SegmentsPlugin ..|> PluginBase : implements
    DevicesPlugin ..|> PluginBase : implements
    DrawingPlugin ..|> PluginBase : implements
    ContextMenuPlugin ..|> PluginBase : implements
```

## Estados e Transições

```mermaid
stateDiagram-v2
    [*] --> NotInitialized
    NotInitialized --> Initializing : initMap()
    Initializing --> Ready : success
    Initializing --> Error : fail
    Error --> Initializing : retry
    
    Ready --> LoadingPlugin : loadPlugin()
    LoadingPlugin --> PluginLoaded : success
    LoadingPlugin --> Ready : fail
    PluginLoaded --> Ready
    
    Ready --> UnloadingPlugin : unloadPlugin()
    UnloadingPlugin --> Ready
    
    Ready --> Cleanup : cleanup()
    Cleanup --> [*]
    
    state Ready {
        [*] --> Idle
        Idle --> Drawing : startDrawing()
        Drawing --> Idle : stopDrawing()
        Idle --> Interacting : user interaction
        Interacting --> Idle
    }
```

## Estrutura de Diretórios

```
frontend/src/
│
├── composables/
│   ├── useMapService.js           # Core service
│   │   ├── useMapService()        # Main composable
│   │   ├── registerMapPlugin()    # Plugin registration
│   │   └── useGoogleMapsApiKey()  # API key helper
│   │
│   └── mapPlugins/
│       ├── index.js               # Plugin registry
│       ├── segmentsPlugin.js      # Fiber segments
│       ├── devicesPlugin.js       # Device markers
│       ├── drawingPlugin.js       # Drawing tools
│       └── contextMenuPlugin.js   # Context menu
│
├── components/
│   └── Map/
│       ├── UnifiedMapView.vue     # Main wrapper
│       ├── MapControls.vue        # Optional controls
│       ├── README.md              # Documentation
│       └── USAGE_EXAMPLES.vue     # Usage examples
│
├── stores/
│   ├── map.js                     # Map state
│   ├── inventory.js               # Inventory data
│   └── dashboard.js               # Dashboard state
│
└── tests/
    ├── unit/
    │   └── useMapService.spec.js  # Service tests
    └── e2e/
        └── map-loading.spec.js    # E2E tests
```

## Padrões de Design Utilizados

### 1. **Plugin Architecture**
- Extensibilidade via plugins independentes
- Registro central de plugins
- Contexto compartilhado entre plugins

### 2. **Composable Pattern**
- Lógica reutilizável via composables Vue 3
- Reatividade automática
- Lifecycle management integrado

### 3. **Factory Pattern**
- Plugins criados via factory functions
- Configuração flexível via options
- Instanciação lazy (sob demanda)

### 4. **Observer Pattern**
- Eventos emitidos para componentes pai
- Callbacks em plugin options
- Reatividade Vue para estado

### 5. **Facade Pattern**
- UnifiedMapView como facade simplificada
- API consistente independente de plugins
- Abstração da complexidade interna

## Benefícios da Arquitetura

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Reutilização** | Código duplicado em múltiplos componentes | Um único sistema reutilizável |
| **Manutenção** | Mudanças em N lugares | Mudanças em 1 lugar |
| **Testabilidade** | Testes acoplados ao componente | Plugins testáveis isoladamente |
| **Performance** | Carrega tudo sempre | Carrega apenas o necessário |
| **Extensibilidade** | Difícil adicionar features | Fácil via novos plugins |
| **Complexidade** | Alta (código espalhado) | Média (bem organizada) |

## Métricas de Código

| Métrica | Valor |
|---------|-------|
| **LOC Core** | ~250 linhas |
| **LOC por Plugin** | ~150-200 linhas |
| **Plugins Disponíveis** | 4 (segments, devices, drawing, contextMenu) |
| **Coverage de Testes** | >80% (target) |
| **Tamanho Bundle** | ~15KB (core + 1 plugin) |
| **Tempo Init** | <100ms (mapa) + <50ms (plugin) |

---

**Autor:** Maps Prove Fiber Team  
**Data:** 2025-11-17  
**Versão:** 1.0.0
