# Integração: Câmeras como Ativos de Inventário

## Status: ✅ Fase 1 Completa | 🚧 Fase 2 Planejada

---

## Visão Geral

Este documento detalha a integração entre **Inventário Físico** (Sites/Equipamentos), **Monitoramento Lógico** (Zabbix) e **Monitoramento Visual** (Câmeras) em uma Central de Operações unificada.

---

## ✅ Fase 1: Permissões por Departamento (Implementado)

### Backend Changes

#### 1. Modelo `VideoMosaic` Atualizado

**Arquivo**: [`backend/setup_app/models.py`](../../backend/setup_app/models.py)

```python
class VideoMosaic(models.Model):
    name = models.CharField(max_length=120)
    layout = models.CharField(max_length=8, choices=LAYOUT_CHOICES)
    cameras = models.JSONField(default=list)
    
    # NOVO: Permissões por departamento
    departments = models.ManyToManyField(
        'core.Department',
        related_name='video_mosaics',
        blank=True,
        help_text="Departamentos com permissão para visualizar este mosaico"
    )
```

**Migration**: `setup_app/migrations/0018_add_departments_to_videomosaic.py`

#### 2. API Filtrada por Departamento

**Arquivo**: [`backend/setup_app/api_views.py`](../../backend/setup_app/api_views.py#L3664-L3698)

```python
def video_mosaics_list(request):
    if request.user.is_superuser:
        mosaics = VideoMosaic.objects.all()
    else:
        user_depts = request.user.profile.departments.all()
        # Mosaicos públicos (sem departamento) OU do departamento do usuário
        mosaics = VideoMosaic.objects.filter(
            Q(departments__in=user_depts) | Q(departments__isnull=True)
        ).distinct()
```

**Regras de Acesso:**
- Superuser: Vê todos os mosaicos
- Usuários normais: Veem apenas mosaicos de seus departamentos
- Mosaicos sem departamento: Públicos (acessíveis a todos)

### Frontend Changes

#### 1. Menu Reorganizado

**Arquivo**: [`frontend/src/components/Layout/TheNavMenu.vue`](../../frontend/src/components/Layout/TheNavMenu.vue#L525-L548)

**Antes:**
```
├── Monitoring
├── Network
└── Video  ← Separado
    ├── Câmeras
    ├── Mosaicos
    └── Grupos
```

**Depois:**
```
├── Monitoring
└── Network
    ├── Device Import
    ├── Network Design
    ├── Network Inventory
    ├── Monitoramento Visual  ← Integrado
    ├── Mosaicos de Vídeo
    └── Grupos de Câmeras
```

**Vantagens:**
- Contexto unificado: Câmeras são ativos de rede
- Fluxo de trabalho otimizado: Operador não precisa trocar de seção
- Preparação para integração com Sites

---

## 🚧 Fase 2: Câmeras como Equipamentos (Planejado)

### Conceito

Transformar cada câmera em um `inventory.Device`, associando-a automaticamente a um `Site`.

### Benefícios

1. **Herança de Localização**: Câmeras herdam coordenadas GPS do Site
2. **Contexto no Mapa**: Clicar em um Site mostra câmeras disponíveis
3. **Alertas Correlacionados**: Se o Site cai, todas as câmeras recebem alerta
4. **Histórico Unificado**: Manutenções, downtime, tickets no mesmo sistema

### Estrutura Proposta

```python
# inventory/models.py (FUTURO)
class Device(models.Model):
    name = models.CharField(max_length=255)
    site = models.ForeignKey('Site', related_name='devices')
    device_type = models.CharField(
        choices=[
            ('switch', 'Switch'),
            ('router', 'Router'),
            ('olt', 'OLT'),
            ('camera', 'Câmera IP'),  # NOVO
            # ...
        ]
    )
    
    # Para câmeras (quando device_type == 'camera')
    video_gateway = models.ForeignKey(
        'setup_app.MessagingGateway',
        null=True,
        blank=True,
        related_name='linked_device'
    )
```

### API Endpoint Futuro

```python
@require_GET
@login_required
def site_cameras(request, site_id: int):
    """Retorna todas as câmeras de um site específico."""
    site = Site.objects.get(pk=site_id)
    cameras = site.devices.filter(device_type='camera')
    
    # Enriquecer com dados do MessagingGateway
    camera_data = [
        {
            "id": cam.id,
            "name": cam.name,
            "playback_url": cam.video_gateway.config.get('stream_url'),
            "online": cam.video_gateway.status == 'active',
        }
        for cam in cameras
    ]
    
    return JsonResponse({"success": True, "cameras": camera_data})
```

---

## 📱 Frontend: Modal de Site com Contexto Visual

### Mockup de Fluxo

```
Operador clica em PIN de Site no Mapa
    ↓
Modal abre com abas:
    ├── 📊 Monitoramento (Gráficos Zabbix)
    ├── 📹 Câmeras (Stream WebRTC ao vivo)
    ├── 🔌 Equipamentos (Lista de devices)
    └── 📋 Tickets (Histórico)
```

### Componente Vue (Exemplo)

```vue
<!-- frontend/src/components/Sites/SiteDetailModal.vue -->
<template>
  <div class="modal">
    <div class="tabs">
      <button @click="activeTab = 'monitoring'">📊 Monitoramento</button>
      <button @click="activeTab = 'cameras'">📹 Câmeras</button>
    </div>
    
    <div v-if="activeTab === 'cameras'" class="cameras-grid">
      <div v-for="camera in siteCameras" :key="camera.id" class="camera-card">
        <video :id="`camera-${camera.id}`" autoplay muted></video>
        <p>{{ camera.name }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useWebRTC } from '@/composables/useWebRTC';

const siteCameras = ref([]);
const activeTab = ref('monitoring');

onMounted(async () => {
  // Fetch cameras from /api/sites/{id}/cameras/
  const res = await api.get(`/inventory/api/sites/${props.siteId}/cameras/`);
  siteCameras.value = res.cameras;
  
  // Inicializar WebRTC para cada câmera
  res.cameras.forEach(camera => {
    const rtc = useWebRTC();
    rtc.connect(camera.playback_url);
    watch(rtc.stream, (stream) => {
      document.getElementById(`camera-${camera.id}`).srcObject = stream;
    });
  });
});
</script>
```

---

## 🎯 Roadmap de Implementação

### Fase 2.1: Backend
- [ ] Adicionar `device_type = 'camera'` ao `inventory.Device`
- [ ] Criar `ForeignKey` para `MessagingGateway` em `Device`
- [ ] Migração de dados: Converter `MessagingGateway(type='video')` → `Device`
- [ ] Criar endpoint `/api/sites/{id}/cameras/`

### Fase 2.2: Frontend
- [ ] Adicionar aba "Câmeras" no `SiteDetailModal.vue`
- [ ] Reutilizar `useWebRTC` composable para streams
- [ ] Implementar botão "Ver Câmeras do Site" no PIN do mapa

### Fase 2.3: Integração Zabbix
- [ ] Correlacionar alertas: Se `Site.status = down`, marcar câmeras como offline
- [ ] Adicionar trigger Zabbix para câmeras (Ex: "Camera offline > 5 min")

---

## 📖 Referências

- [Playbook AI - Architecture](../.github/copilot-instructions.md)
- [Guia WebRTC/WHEP](./VIDEO_STREAMING_WHEP.md)
- [Modelo Department](../../backend/core/models.py#L50-L56)
- [Modelo VideoMosaic](../../backend/setup_app/models.py#L188-L223)

---

## 💡 Exemplo de Uso Final

**Cenário Real:**

1. Operador recebe alerta Zabbix: "Switch Braga - CPU 95%"
2. Clica no PIN do Site "Braga" no mapa
3. Modal abre mostrando:
   - Gráfico de CPU em tempo real (Zabbix)
   - 4 câmeras do datacenter (WebRTC)
   - Vê fumaça saindo do rack na câmera 2
   - Abre ticket "Incêndio Rack 3 - Braga" diretamente do modal

**Tempo de Resposta:**
- Antes: 5-10 minutos (navegar entre módulos)
- Depois: 30 segundos (tudo em um modal)

---

**Autor**: AI Agent  
**Data**: 22/01/2026  
**Status**: Fase 1 Completa ✅ | Fase 2 Planejada 🚧
