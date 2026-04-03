# Trace Route - Rastreamento de Caminho Óptico 🔍

Sistema completo de rastreamento bidirecional de fibras ópticas com cálculo automático de power budget.

## 🎯 Visão Geral

O **Trace Route** rastreia o caminho completo da luz através da infraestrutura de fibra, seguindo:

1. **Conexões físicas**: `FiberStrand.connected_device_port` (Switch/DIO → Fibra)
2. **Fusões**: `FiberStrand.fused_to` (Emendas em CEOs)
3. **Segmentos de cabo**: Distâncias e atenuações

### Caminho Típico

```
┌─────────────┐      ┌──────┐      ┌──────────┐      ┌─────────┐      ┌──────┐      ┌─────────────┐
│  Switch A   │ ───> │ DIO  │ ───> │  Cabo A  │ ───> │   CEO   │ ───> │ Cabo B │ ───> │  Switch B   │
│  (Porta 1)  │      │(P. 5)│      │ (FO 01)  │      │ (Fusão) │      │ (FO 01)│      │  (Porta 5)  │
└─────────────┘      └──────┘      └──────────┘      └─────────┘      └────────┘      └─────────────┘
     0.5 dB            0 dB          0.875 dB           0.1 dB           0.6 dB            0.5 dB
   (Conector)                     (2.5 km × 0.35)      (Fusão)       (1.7 km × 0.35)    (Conector)
```

**Perda Total**: 2.575 dB  
**Margem Disponível**: 15.425 dB (TX: 0 dBm, RX: -18 dBm)  
**Status**: ✅ **VIÁVEL** (margem > 3 dB)

---

## 📁 Estrutura de Arquivos

### Backend
```
backend/inventory/api/
├── trace_route.py          # Algoritmo de rastreamento bidirecional
└── tests/
    └── test_trace_route.py # Testes unitários e integração
```

### Frontend
```
frontend/src/
├── components/TraceRoute/
│   ├── TraceRouteView.vue        # Visualização timeline (metro-style)
│   ├── TraceRouteModal.vue       # Modal wrapper com loading
│   └── IntegrationExample.vue    # Exemplo de integração
└── composables/
    └── useTraceRoute.js          # Composable para API calls
```

---

## 🚀 Quick Start

### Backend: Endpoint API

```python
# GET /api/v1/inventory/trace-route/?strand_id=123

from inventory.api.trace_route import trace_fiber_route

# Resposta JSON:
{
  "trace_id": "trace_123_1701234567",
  "source": {
    "device_name": "SW-Core-01",
    "port_name": "GigabitEthernet1/0/1",
    "site_name": "Site A - Core"
  },
  "destination": {
    "device_name": "SW-Dist-05",
    "port_name": "SFP2",
    "site_name": "Site B - Distribution"
  },
  "path": [
    {
      "step_number": 1,
      "type": "device_port",
      "name": "SW-Core-01 - GigabitEthernet1/0/1",
      "loss_db": 0.5
    },
    {
      "step_number": 2,
      "type": "fiber_strand",
      "name": "Cabo-Backbone-01 - Fibra 5 (Verde)",
      "details": {
        "distance_km": 2.5,
        "attenuation_measured_db": 0.875
      },
      "loss_db": 0.875
    },
    // ... mais steps
  ],
  "total_distance_km": 4.2,
  "total_loss_db": 2.575,
  "fusion_count": 1,
  "connector_count": 2,
  "power_budget": {
    "tx_power_dbm": 0,
    "rx_sensitivity_dbm": -18,
    "available_margin_db": 15.425,
    "required_margin_db": 3,
    "is_viable": true,
    "status": "OK",
    "message": "Link viável com 15.43 dB de margem"
  },
  "status": "OK"
}
```

### Frontend: Uso Básico

```vue
<template>
  <button @click="showTrace = true">🔍 Trace Route</button>
  
  <TraceRouteModal
    :strand-id="selectedStrandId"
    :is-open="showTrace"
    @close="showTrace = false"
  />
</template>

<script setup>
import { ref } from 'vue';
import TraceRouteModal from '@/components/TraceRoute/TraceRouteModal.vue';

const showTrace = ref(false);
const selectedStrandId = ref(123);
</script>
```

### Frontend: Uso Avançado (Composable)

```javascript
import { useTraceRoute } from '@/composables/useTraceRoute';

const { traceFromStrand, loading, traceResult, exportTracePDF } = useTraceRoute();

// Executar trace
await traceFromStrand(123);

// Acessar resultado
console.log(traceResult.value.power_budget);

// Exportar relatório
exportTracePDF(traceResult.value);
```

---

## 🧮 Cálculo de Power Budget

### Fórmula

```
Margem Disponível = TX Power - RX Sensitivity - Perdas Totais
Perdas Totais = (Fibra × 0.35 dB/km) + (Fusões × 0.1 dB) + (Conectores × 0.5 dB)
```

### Valores Típicos

| Componente | Perda Típica | Notas |
|------------|--------------|-------|
| **Fibra SM** | 0.35 dB/km | Monomodo 1310nm/1550nm |
| **Fusão** | 0.1 dB | Emenda por fusão (splice) |
| **Conector SC/LC** | 0.5 dB | Conector mecânico |
| **TX Power (SFP)** | -3 a 0 dBm | Potência de transmissão |
| **RX Sensitivity** | -18 a -23 dBm | Sensibilidade do receptor |
| **Margem Mínima** | 3 dB | Fator de segurança |

### Critérios de Viabilidade

- ✅ **VIÁVEL**: `Margem Disponível ≥ 3 dB`
- ⚠️ **ATENÇÃO**: `Margem Disponível < 3 dB`
- ❌ **INVIÁVEL**: `Margem Disponível < 0 dB`

---

## 🎨 Componentes Frontend

### TraceRouteView.vue

Visualização em formato **timeline horizontal** (estilo mapa de metrô).

**Features**:
- ✅ Ícones diferenciados por tipo (🟢 Switch, 🟠 Fusão, ━━ Fibra)
- ✅ Card de Power Budget com status visual
- ✅ Detalhes expandidos por step (click para expandir)
- ✅ Badges de cor para identificação de fibras
- ✅ Exportação de relatório em TXT

### TraceRouteModal.vue

Modal wrapper com:
- ✅ Loading state com spinner
- ✅ Error handling
- ✅ Auto-trace ao abrir modal
- ✅ Eventos `@export` e `@locate-fault`

### useTraceRoute.js

Composable reativo com:
- `traceFromStrand(strandId)` - Executar trace
- `loading` - Estado de carregamento
- `traceResult` - Resultado completo
- `exportTracePDF(trace)` - Exportar relatório
- `isLinkViable(powerBudget)` - Verificar viabilidade

---

## 🧪 Testes

### Backend: Pytest

```bash
pytest backend/inventory/tests/test_trace_route.py -v
```

**Cobertura de Testes**:
- ✅ Serialização de device ports, fiber strands, fusões
- ✅ Cálculo de power budget com links viáveis
- ✅ Trace completo bidirecional (Switch A → Switch B)
- ✅ Caminhos parciais (apenas uma extremidade conectada)
- ✅ Validação de parâmetros (strand_id obrigatório)
- ✅ Tratamento de erros (strand não encontrado)

### Frontend: Vitest

```bash
npm run test:unit -- TraceRoute
```

---

## 🔧 Configuração

### Variáveis de Ambiente (Opcional)

```bash
# Valores padrão de power budget
TRACE_DEFAULT_TX_POWER=0        # dBm
TRACE_DEFAULT_RX_SENS=-18       # dBm
TRACE_REQUIRED_MARGIN=3         # dB

# Perdas padrão
TRACE_FIBER_LOSS=0.35           # dB/km
TRACE_FUSION_LOSS=0.1           # dB
TRACE_CONNECTOR_LOSS=0.5        # dB
```

---

## 📊 Casos de Uso

### 1. Planejamento de Link

**Antes de ativar um link novo**:
1. Selecione a fibra planejada
2. Execute Trace Route
3. Verifique power budget: `is_viable = true`?
4. Se não viável, ajuste: use fibra menor, reduza fusões, troque SFP

### 2. Troubleshooting de Falhas

**Quando um link cai**:
1. Execute Trace Route
2. Identifique último ponto com sinal (RX power)
3. Use OTDR para localizar ponto de ruptura
4. Visualize no mapa (botão "Localizar Falha")

### 3. Documentação Técnica

**Para relatórios de campo**:
1. Execute Trace Route
2. Clique em "Exportar Relatório"
3. Arquivo TXT gerado com: caminho completo, perdas, power budget
4. Anexe ao relatório de projeto/manutenção

---

## 🚧 Roadmap (Próximas Fases)

### Fase 12: OTDR Integration
- [ ] Integrar medições OTDR reais
- [ ] Plotar gráfico de atenuação vs distância
- [ ] Auto-detectar rupturas e plotar no mapa

### Fase 13: Multi-Path Analysis
- [ ] Suportar múltiplos caminhos paralelos
- [ ] Análise de redundância (path A vs path B)
- [ ] Cálculo de disponibilidade (uptime)

### Fase 14: AI-Powered Recommendations
- [ ] Sugerir otimizações de rota
- [ ] Prever degradação de sinal
- [ ] Alertas proativos de margem baixa

---

## 🐛 Troubleshooting

### "Trace ID not found"
- **Causa**: `strand_id` inválido ou fibra deletada
- **Solução**: Verifique se a fibra existe no banco: `FiberStrand.objects.get(id=123)`

### "Loop infinito no trace"
- **Causa**: Fusão circular (A → B → A)
- **Solução**: Algoritmo tem proteção com `visited` set, mas verifique dados

### "Power budget sempre WARNING"
- **Causa**: Valores default muito conservadores
- **Solução**: Ajuste TX power e RX sensitivity no código ou env vars

---

## 📚 Referências

- [ITU-T G.652](https://www.itu.int/rec/T-REC-G.652) - Especificação de fibra monomodo
- [TIA-568.3](https://tiaonline.org/) - Padrões de cabeamento óptico
- [RFC 6988](https://datatracker.ietf.org/doc/html/rfc6988) - GMPLS para fibra óptica

---

## 👥 Contribuindo

Para adicionar novos recursos:
1. Backend: Edite `inventory/api/trace_route.py`
2. Frontend: Componentes em `components/TraceRoute/`
3. Testes: Adicione em `tests/test_trace_route.py`

**Contato**: Ver `doc/contributing/README.md`

---

**Versão**: 1.0.0 (Phase 11.5)  
**Última Atualização**: 2024-11-30
