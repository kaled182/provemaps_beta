# Cable Split V2 - Implementação com CableSegments

## 📋 Resumo da Implementação

### Problema Original
Quando um cabo era "partido" (split) para criar uma CEO, o sistema antigo:
- ❌ Criava **novos FiberCables** (cable_a, cable_b)
- ❌ **Ignorava** o sistema de CableSegments
- ❌ O **trace_route** continuava passando pelo cabo "rompido" (sem verificar integridade física)

### Solução Implementada
Nova abordagem usando **CableSegments** para representar descontinuidade física:
- ✅ **Mantém o FiberCable original** (não cria novos)
- ✅ **Cria CableSegments** representando os pedaços antes/depois do corte
- ✅ **Cria CableSegment.status=BROKEN** virtual representando o ponto de corte
- ✅ **Trace route detecta e para** ao encontrar segmento BROKEN

---

## 🏗️ Arquivos Criados/Modificados

### 1. **backend/inventory/api/cable_split_v2.py** (NOVO)
ViewSet para split usando CableSegments:
- Endpoint: `POST /api/v1/inventory/cables/<id>/split-at-ceo-v2/`
- Usa `auto_segment_cable_at_ceo()` do service layer
- Cria segmento BROKEN virtual no ponto de corte
- Retorna estrutura: `{before, broken, after}`

### 2. **backend/inventory/services/cable_segments.py** (MODIFICADO)
Service layer para gerenciamento de segmentos:
- `auto_segment_cable_at_ceo()`: Agora aceita `distance_meters` opcional
- Fallback: usa ponto médio se distância não informada

### 3. **backend/inventory/api/trace_route.py** (MODIFICADO - anterior)
Trace route com verificação de integridade:
- `check_cable_integrity()`: Verifica status dos segmentos do cabo
- `trace_direction()`: Para ao encontrar segmento BROKEN
- Adiciona step tipo `broken_segment` no resultado

### 4. **backend/inventory/models.py** (MODIFICADO - anterior)
CableSegment com campo status:
- Migration 0030: Adicionado campo `status` (active/broken/inactive)
- Constants: `STATUS_ACTIVE`, `STATUS_BROKEN`, `STATUS_INACTIVE`

### 5. **backend/inventory/urls_api.py** (MODIFICADO)
Nova rota registrada:
```python
path(
    "cables/<int:pk>/split-at-ceo-v2/",
    CableSplitV2ViewSet.as_view({'post': 'split_at_ceo'}),
    name="cable-split-ceo-v2",
)
```

---

## 🔄 Fluxo de Execução (Genérico para Qualquer Cabo)

### Split Cable (V2)
```
1. POST /api/v1/inventory/cables/<cable_id>/split-at-ceo-v2/
   Body: {"ceo_id": <ceo_id>, "split_point": {"lat": <lat>, "lng": <lng>}}

2. Validações:
   ├─ Cabo existe e tem path (geometria LineString)?
   ├─ CEO existe e é do tipo 'splice_box'?
   ├─ CEO pertence ao cabo (ceo.cable_id == cable.id)?
   └─ Se falhar → HTTP 400 Bad Request

3. cable_split_v2.py::split_at_ceo()
   ├─ Calcula distância da CEO ao longo do path do cabo
   ├─ Chama auto_segment_cable_at_ceo(cable, ceo, distance_meters)
   │  ├─ Cria segmento inicial se cabo não tem segmentos
   │  ├─ Divide segmento existente em seg_before e seg_after
   │  └─ Retorna (seg_before, seg_after)
   ├─ Renumera seg_after e segmentos posteriores (+1)
   ├─ Cria CableSegment BROKEN no número do seg_after original:
   │  - segment_number = (entre seg_before e seg_after)
   │  - start_infrastructure = ceo
   │  - end_infrastructure = ceo (ponto de descontinuidade)
   │  - length_meters = 0
   │  - status = STATUS_BROKEN
   ├─ Cria attachment: cable → ceo
   └─ Atualiza cable.notes com informação do split

4. Retorna estrutura de segmentos para QUALQUER cabo:
   {
     "status": "success",
     "cable": { "id": <id>, "name": <name> },
     "segments": {
       "before": {...},  // Segmento antes do corte
       "broken": {...},  // Segmento BROKEN (0m, status='broken')
       "after": {...}    // Segmento após o corte
     }
   }
```

### Trace Route (Detecta Break)
```
1. GET /api/v1/inventory/trace-route/?strand_id=123

2. trace_route.py::trace_fiber_route()
   ├─ Itera conexões via FiberFusion
   ├─ Para cada fibra, chama check_cable_integrity(strand)
   │  ├─ Verifica: strand.segment.status == 'broken' ?
   │  ├─ Verifica: cable.segments.filter(status=BROKEN).exists() ?
   │  └─ Retorna (is_intact, broken_segment, message)
   ├─ Se not is_intact:
   │  ├─ Adiciona step tipo 'broken_segment'
   │  ├─ Para loop (break)
   │  └─ Luz NÃO passa
   └─ Retorna path completo ou interrompido

3. Retorna:
   {
     "path": [
       {"type": "device_port", ...},
       {"type": "fiber_strand", ...},
       {"type": "broken_segment", "message": "BREAK detectado!"}
     ],
     "power_budget": {"is_viable": false, "status": "BROKEN"}
   }
```

---

## ⚠️ Requisitos e Limitações

### Pré-requisitos para Split (QUALQUER Cabo)
1. **Cabo deve ter `path`** (geometria LineString em SRID 4326)
2. **CEO deve pertencer ao cabo** (`ceo.cable_id == cable.id`)
3. **CEO deve estar no path do cabo** (dentro da rota geométrica)
4. **Split point** deve estar próximo da CEO (lat/lng)

### Modelo de CEOs no Sistema
**IMPORTANTE**: No MapsProveFiber, `FiberInfrastructure` (CEOs) são **sempre associadas a um cabo específico** via FK `cable_id`. Isso significa:

- ✅ Cada CEO "pertence" a um cabo
- ✅ Quando adicionamos CEO via UI, ela já tem `cable_id` definido
- ✅ O split V2 funciona com CEOs existentes do cabo
- ❌ NÃO podemos reutilizar CEO de outro cabo (validação no endpoint)

**Exemplo**:
```python
# CEO criada via UI ao clicar no mapa sobre um cabo
ceo = FiberInfrastructure.objects.create(
    cable=cabo_backbone_50,  # FK obrigatória
    type='splice_box',
    name='CEO-Planaltina-01',
    location=Point(-47.8, -15.5, srid=4326)
)
# Agora pode fazer split usando esta CEO
```

### Como Funciona com Cabos Novos
1. **Cabo novo criado** → não tem segmentos inicialmente
2. **Primeira CEO adicionada** → `auto_segment_cable_at_ceo()` cria Seg1 inicial
3. **Split executado** → Seg1 dividido em Seg1 + BREAK + Seg2
4. **Próximos splits** → funcionam da mesma forma, dividindo segmentos existentes

### Como Funciona com Cabos Existentes
1. **Cabo existente sem segmentos** → comportamento igual a cabo novo
2. **Cabo com segmentos** → divide o segmento que contém a CEO
3. **Cabo já splitado** → pode fazer split novamente em outro ponto

---

## 🧪 Como Testar

### 1. Fazer Split de Cabo
```bash
# Via curl (substituir <cabo_id> e <ceo_id>)
curl -X POST http://localhost:8000/api/v1/inventory/cables/50/split-at-ceo-v2/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{
    "ceo_id": 2098,
    "split_point": {"lat": -15.5, "lng": -47.8}
  }'
```

### 2. Verificar Segmentos Criados
```python
from inventory.models import CableSegment, FiberCable

cable = FiberCable.objects.get(id=50)
segments = cable.segments.all().order_by('segment_number')

for seg in segments:
    print(f"{seg.name}: {seg.status}, {seg.length_meters}m")

# Saída esperada:
# CABO-BACKBONE-50-Seg1: active, 5250m
# CABO-BACKBONE-50-BREAK-CEO-2098: broken, 0m
# CABO-BACKBONE-50-Seg2: active, 5250m
```

### 3. Testar Trace Route
```bash
# Via curl (substituir <strand_id>)
curl http://localhost:8000/api/v1/inventory/trace-route/?strand_id=456

# Verificar se tem step tipo "broken_segment" no path
```

### 4. Logs do Django
```bash
docker compose logs web --since 5m | Select-String "SPLIT V2"

# Saída esperada:
# [SPLIT V2] Iniciando split usando CableSegments...
# [SPLIT V2] Segmentos criados: Seg1 e Seg2
# [SPLIT V2] Segmento BROKEN criado: CABO-...-BREAK-CEO-...
# [SPLIT V2] Split concluído com sucesso!
```

---

## 📊 Modelo de Dados

### CableSegment (atualizado)
```python
class CableSegment(models.Model):
    cable = models.ForeignKey(FiberCable, on_delete=models.CASCADE, related_name='segments')
    segment_number = models.DecimalField(max_digits=5, decimal_places=1)  # Permite 0.5 para BREAK
    name = models.CharField(max_length=100)
    start_infrastructure = models.ForeignKey(FiberInfrastructure, null=True, on_delete=models.SET_NULL, related_name='+')
    end_infrastructure = models.ForeignKey(FiberInfrastructure, null=True, on_delete=models.SET_NULL, related_name='+')
    length_meters = models.FloatField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Ativo'),
            ('broken', 'Rompido'),      # NOVO: representa descontinuidade física
            ('inactive', 'Inativo')
        ],
        default='active'
    )
```

### Estrutura após Split
```
FiberCable (id=50, name="CABO-BACKBONE-50")
├─ CableSegment (id=1, segment_number=1, status='active')
│  └─ FiberStrands (associados a este segmento)
├─ CableSegment (id=2, segment_number=1.5, status='broken')  # VIRTUAL BREAK
│  - length_meters = 0
│  - start_infrastructure = CEO-2098
│  - end_infrastructure = CEO-2098
└─ CableSegment (id=3, segment_number=2, status='active')
   └─ FiberStrands (associados a este segmento)
```

---

## 🔍 Comparação V1 vs V2

| Aspecto | V1 (cable_split.py) | V2 (cable_split_v2.py) |
|---------|---------------------|------------------------|
| **Cria novos FiberCables?** | ✅ Sim (cable_a, cable_b) | ❌ Não (mantém original) |
| **Usa CableSegments?** | ❌ Não | ✅ Sim |
| **Duplica estrutura (tubes/strands)?** | ✅ Sim | ❌ Não (reutiliza) |
| **Marca descontinuidade física?** | ❌ Não | ✅ Sim (segmento BROKEN) |
| **Trace route detecta break?** | ❌ Não | ✅ Sim |
| **Complexidade** | Alta (duplicação) | Baixa (apenas segmentos) |
| **Integridade de dados** | Média | Alta (single source of truth) |

---

## 🚀 Próximos Passos

### Backend
- [x] Criar cable_split_v2.py com novo endpoint
- [x] Modificar cable_segments.py para aceitar distance_meters
- [x] Integrar com trace_route (já feito anteriormente)
- [x] Registrar rotas em urls_api.py
- [ ] **Deprecar cable_split.py** (V1) ou mantê-lo como fallback?
- [ ] **Migração de dados**: converter splits existentes para usar segmentos?

### Frontend
- [ ] Atualizar modal de split para chamar endpoint V2
- [ ] Visualizar segmentos BROKEN no mapa (linha tracejada vermelha?)
- [ ] Mostrar ícone ⚠️ ou 🔴 na CEO onde há BREAK
- [ ] Timeline de trace route destacar ponto de break

### Testes
- [ ] Teste unitário: `test_cable_split_v2_creates_segments()`
- [ ] Teste unitário: `test_trace_route_stops_at_broken_segment()`
- [ ] Teste de integração: split → trace → verificar break
- [ ] Teste de edge case: split em cabo já splitado

---

## 🐛 Troubleshooting

### Erro: "CEO sem distance_from_origin"
**Causa**: FiberInfrastructure não tem campo `distance_from_origin`
**Solução**: cable_segments.py usa **fallback** para ponto médio do cabo
**Log**: `WARNING: CEO {name} sem distance_from_origin, usando ponto médio: {distance}m`

### Segmento BROKEN não aparece no trace
**Verificar**:
1. Segmento foi criado? `CableSegment.objects.filter(status='broken')`
2. check_cable_integrity() está sendo chamado? Adicionar logger.debug()
3. Lógica do trace está correta? Verificar `if not is_intact: break`

### Split não cria segmentos
**Verificar**:
1. Cabo tem path configurado? `cable.path is not None`
2. Distance calculation retorna valor válido?
3. Transaction está commitando? Verificar logs de erro

---

**Versão**: 2026-01-02 (Implementação inicial)
**Autor**: AI Assistant (GitHub Copilot)
**Status**: ✅ Pronto para testes
