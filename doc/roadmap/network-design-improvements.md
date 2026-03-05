# Network Design - Roadmap de Melhorias

**Data**: 05/03/2026  
**Status**: Planejamento  
**Prioridade**: Média-Alta

## Contexto

Após a implementação bem-sucedida do **Provider Pattern** para suporte multi-provider de mapas (Mapbox, Google Maps, etc.), identificamos oportunidades de melhoria na página de criação/edição de cabos de fibra óptica.

A funcionalidade básica está **100% operacional**:
- ✅ Desenhar rotas no mapa
- ✅ Vincular dispositivos e portas
- ✅ Salvar cabos no banco de dados
- ✅ Editar cabos existentes
- ✅ Importar via KML
- ✅ Funciona com qualquer provider de mapas configurado

## 🎯 Melhorias Propostas

### 1. Indicadores Visuais de Origem/Destino

**Problema Atual**: Todos os marcadores são círculos vermelhos idênticos, dificultando identificar origem e destino.

**Solução Proposta**:
- **Marcador de origem**: Verde, ícone "A" ou "🔵"
- **Marcador de destino**: Vermelho, ícone "B" ou "🔴"
- **Pontos intermediários**: Azul claro, menores
- **Preview da rota**: Cor laranja antes de salvar, azul após salvo

**Impacto**: Alto  
**Esforço**: 2-3 horas  
**Prioridade**: 🔥 Alta

**Arquivos a modificar**:
- `frontend/src/providers/maps/MapboxProvider.js` - `MapboxMarker` class
- `frontend/src/providers/maps/GoogleMapsProvider.js` - `GoogleMarkerClass`
- `frontend/src/features/networkDesign/fiberRouteBuilder.js` - lógica de criação de markers

---

### 2. Validação em Tempo Real

**Problema Atual**: Validações só acontecem ao clicar "Save", resultando em frustração do usuário.

**Solução Proposta**:
- Validar se porta origem/destino já está em uso (consulta real-time à API)
- Destacar campos obrigatórios faltantes (borda vermelha)
- Alertar sobre nomes de cabos duplicados
- Validar distância mínima (< 100m pode indicar erro de digitação)
- Mostrar ícone ✅ ou ❌ ao lado de cada campo

**Impacto**: Alto  
**Esforço**: 3-4 horas  
**Prioridade**: 🔥 Alta

**Implementação**:
```javascript
// Novo arquivo: frontend/src/features/networkDesign/validators.js
export async function validatePortAvailability(deviceId, portId) {
  const response = await api.get(`/api/v1/inventory/ports/${portId}/availability/`);
  return response.available;
}
```

**Endpoints necessários**:
- `GET /api/v1/inventory/ports/{id}/availability/` - Retorna se porta está livre
- `GET /api/v1/inventory/fibers/check-name/?name={name}` - Verifica duplicação de nome

---

### 3. Autocomplete com Busca de Dispositivos

**Problema Atual**: Select dropdown simples, difícil encontrar dispositivo em redes grandes (100+ devices).

**Solução Proposta**:
- Substituir `<select>` por componente autocomplete
- Busca por nome, IP, ou localização
- Ordenar por proximidade do ponto clicado no mapa
- Exibir ícone de status Zabbix (🟢 online / 🔴 offline)
- Mostrar distância estimada do dispositivo

**Impacto**: Alto  
**Esforço**: 4-5 horas  
**Prioridade**: 🟡 Média

**Biblioteca sugerida**: `@headlessui/vue` (Combobox component) ou Vue Select

**Preview**:
```
┌──────────────────────────────────────────────┐
│ Switch Santana                          [🟢] │
│ 192.168.1.10 · 2.3km do ponto selecionado    │
├──────────────────────────────────────────────┤
│ Switch Centro                           [🟢] │
│ 192.168.1.20 · 5.1km do ponto selecionado    │
└──────────────────────────────────────────────┘
```

---

### 4. Undo/Redo para Edição de Rota

**Problema Atual**: Não há como desfazer adição de pontos, usuário precisa recarregar a página.

**Solução Proposta**:
- **Ctrl+Z**: Desfazer último ponto
- **Ctrl+Y**: Refazer ponto removido
- **Botão "Clear Route"**: Recomeçar do zero
- Histórico visual de ações

**Impacto**: Médio  
**Esforço**: 3-4 horas  
**Prioridade**: 🟡 Média

**Implementação**:
```javascript
// Pattern: Command Pattern para histórico
class RouteHistory {
  constructor() {
    this.history = [];
    this.currentIndex = -1;
  }
  
  addPoint(point) {
    this.history = this.history.slice(0, this.currentIndex + 1);
    this.history.push({ type: 'add', point });
    this.currentIndex++;
  }
  
  undo() {
    if (this.currentIndex >= 0) {
      const action = this.history[this.currentIndex];
      this.currentIndex--;
      return action;
    }
  }
  
  redo() {
    if (this.currentIndex < this.history.length - 1) {
      this.currentIndex++;
      return this.history[this.currentIndex];
    }
  }
}
```

---

### 5. Edição Interativa de Vértices (Mapbox GL Draw)

**Problema Atual**: Console mostra warning "Full editing with mapbox-gl-draw not implemented yet". Não é possível arrastar vértices da rota.

**Solução Proposta**:
- Integrar plugin `@mapbox/mapbox-gl-draw`
- Arrastar vértices para ajustar rota
- Adicionar ponto clicando na linha
- Remover ponto com botão direito

**Impacto**: Alto  
**Esforço**: 6-8 horas  
**Prioridade**: 🟡 Média

**Dependências**:
```bash
npm install @mapbox/mapbox-gl-draw
```

**Implementação**:
```javascript
// Em MapboxProvider.js
import MapboxDraw from '@mapbox/mapbox-gl-draw';

class MapboxMap extends IMap {
  enableEditing() {
    this.draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: {
        point: false,
        line_string: true,
        polygon: false,
      }
    });
    this.map.addControl(this.draw);
  }
}
```

---

### 6. Snap to Roads (Seguir Estradas)

**Problema Atual**: Linha reta entre pontos, não reflete rota real do cabo em rodovias.

**Solução Proposta**:
- Toggle "Snap to Roads" ON/OFF
- Usar Mapbox Directions API para calcular rota seguindo estradas
- Útil para cabos que seguem rodovias
- Mostrar distância real vs. distância em linha reta

**Impacto**: Médio  
**Esforço**: 5-6 horas  
**Prioridade**: 🟢 Baixa

**API**:
```javascript
// Mapbox Directions API
const response = await fetch(
  `https://api.mapbox.com/directions/v5/mapbox/driving/${coords}?access_token=${token}`
);
```

**Custo**: Requer atenção aos limites da API Mapbox (50k requisições/mês grátis)

---

### 7. Copiar Cabo como Template

**Problema Atual**: Cabos paralelos (mesma rota, dispositivos diferentes) precisam ser desenhados do zero.

**Solução Proposta**:
- Botão "Duplicate Cable" no menu de contexto (botão direito)
- Copia rota geográfica
- Adiciona sufixo automático no nome (ex: "Cabo X" → "Cabo X (cópia)")
- Pede apenas para selecionar novos dispositivos/portas

**Impacto**: Médio  
**Esforço**: 2-3 horas  
**Prioridade**: 🟡 Média

**Fluxo**:
1. Botão direito no cabo → "Duplicate"
2. Modal aparece com rota já preenchida
3. Usuário altera nome e dispositivos
4. Salva

---

### 8. Importar Múltiplos Formatos

**Problema Atual**: Só aceita KML.

**Solução Proposta**:
- **GeoJSON**: Padrão moderno, mais fácil de gerar programaticamente
- **GPX**: Comum em dispositivos GPS
- **Drag & Drop**: Arrastar arquivo direto no mapa

**Impacto**: Médio  
**Esforço**: 4-5 horas  
**Prioridade**: 🟢 Baixa

**Biblioteca**: `@mapbox/togeojson` (converte KML/GPX para GeoJSON)

---

### 9. Prevenção de Conflitos

**Problema Atual**: Possível criar cabos com portas/dispositivos já em uso.

**Solução Proposta**:
- Validar se porta origem/destino já está vinculada a outro cabo
- Detectar cabos muito próximos (< 50m) → "Cabo similar já existe?"
- Validar se dispositivos têm coordenadas geográficas
- Checar se portas existem no Zabbix

**Impacto**: Alto (previne erros de dados)  
**Esforço**: 3-4 horas  
**Prioridade**: 🔥 Alta

**Validações**:
```python
# Backend: inventory/validators.py
def validate_port_not_in_use(port_id):
    existing = FiberCable.objects.filter(
        Q(origin_port_id=port_id) | Q(dest_port_id=port_id)
    ).exists()
    if existing:
        raise ValidationError(f"Port {port_id} already in use")
```

---

### 10. Metadados Avançados do Cabo

**Problema Atual**: Só armazena nome, dispositivos e coordenadas.

**Solução Proposta**:
- **Tipo de fibra**: Monomodo (SMF) / Multimodo (MMF)
- **Número de fibras**: 12, 24, 48, 96, 144, etc.
- **Fornecedor/Contrato**: Referência externa
- **Data de instalação**: Útil para garantias
- **Custo estimado**: Auto-calculado (distância × R$/km configurável)

**Impacto**: Médio  
**Esforço**: 3-4 horas  
**Prioridade**: 🟢 Baixa

**Modelo de dados**:
```python
# Backend: inventory/models.py
class FiberCable(models.Model):
    # ... campos existentes ...
    fiber_type = models.CharField(
        max_length=10,
        choices=[('SMF', 'Single Mode'), ('MMF', 'Multi Mode')],
        default='SMF'
    )
    fiber_count = models.IntegerField(default=12)
    vendor = models.CharField(max_length=100, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    cost_per_km = models.DecimalField(max_digits=10, decimal_places=2, null=True)
```

---

### 11. Preview Antes de Salvar

**Problema Atual**: Usuário não vê resumo antes de confirmar.

**Solução Proposta**:
- Card de confirmação com resumo visual:
  ```
  ┌────────────────────────────────────────────┐
  │ 📋 RESUMO DO CABO                          │
  ├────────────────────────────────────────────┤
  │ 📍 Origem:                                 │
  │    Switch Santana M → XGigabitEthernet0/2  │
  │                                            │
  │ 📍 Destino:                                │
  │    Huawei-Switch Santana M → (desabilitado)│
  │                                            │
  │ 📏 Distância: 197.075 km                   │
  │ 🔵 Pontos: 7                               │
  │ ⚠️  Monitoramento: Apenas origem           │
  ├────────────────────────────────────────────┤
  │         [Cancelar]  [✓ Confirmar]          │
  └────────────────────────────────────────────┘
  ```

**Impacto**: Médio  
**Esforço**: 2 horas  
**Prioridade**: 🟡 Média

---

### 12. Estatísticas da Rede em Tempo Real

**Problema Atual**: Não há visão geral da rede.

**Solução Proposta**:
- Painel lateral com métricas:
  - **Total de cabos**: 42 cabos
  - **Distância total**: 1.234,56 km
  - **Cabos com problemas**: 3 (sem coordenadas)
  - **Última importação**: 05/03/2026 14:30
  - **Dispositivos conectados**: 18

**Impacto**: Baixo (nice to have)  
**Esforço**: 3-4 horas  
**Prioridade**: 🟢 Baixa

---

## 📊 Matriz de Priorização

| Melhoria                        | Impacto | Esforço | Prioridade | Ordem |
|---------------------------------|---------|---------|------------|-------|
| Indicadores visuais origem/dest | Alto    | 2-3h    | 🔥 Alta    | 1     |
| Validação em tempo real         | Alto    | 3-4h    | 🔥 Alta    | 2     |
| Prevenção de conflitos          | Alto    | 3-4h    | 🔥 Alta    | 3     |
| Autocomplete de dispositivos    | Alto    | 4-5h    | 🟡 Média   | 4     |
| Undo/Redo                       | Médio   | 3-4h    | 🟡 Média   | 5     |
| Preview antes de salvar         | Médio   | 2h      | 🟡 Média   | 6     |
| Copiar cabo como template       | Médio   | 2-3h    | 🟡 Média   | 7     |
| Edição interativa vértices      | Alto    | 6-8h    | 🟡 Média   | 8     |
| Importar múltiplos formatos     | Médio   | 4-5h    | 🟢 Baixa   | 9     |
| Snap to Roads                   | Médio   | 5-6h    | 🟢 Baixa   | 10    |
| Metadados avançados             | Médio   | 3-4h    | 🟢 Baixa   | 11    |
| Estatísticas em tempo real      | Baixo   | 3-4h    | 🟢 Baixa   | 12    |

**Total estimado**: 42-54 horas (~6-7 dias de desenvolvimento)

---

## 🚀 Roadmap de Implementação

### Sprint 1 - Quick Wins (1 semana)
- [x] Provider Pattern (CONCLUÍDO - v2.1.0)
- [ ] Indicadores visuais origem/destino
- [ ] Preview antes de salvar
- [ ] Copiar cabo como template

### Sprint 2 - Validações (1 semana)
- [ ] Validação em tempo real
- [ ] Prevenção de conflitos
- [ ] Autocomplete de dispositivos

### Sprint 3 - Edição Avançada (1-2 semanas)
- [ ] Undo/Redo
- [ ] Edição interativa de vértices (Mapbox GL Draw)
- [ ] Importar múltiplos formatos

### Sprint 4 - Features Avançadas (1 semana)
- [ ] Snap to Roads
- [ ] Metadados avançados
- [ ] Estatísticas em tempo real

---

## 📝 Notas Técnicas

### Performance
- Validações em tempo real devem usar **debounce** (300ms) para evitar sobrecarga
- Autocomplete deve cachear lista de dispositivos no frontend
- Snap to Roads deve ser opcional (impacto na API quota)

### Compatibilidade
- Todas as melhorias devem funcionar com **qualquer provider** (Mapbox, Google Maps, etc.)
- Manter abstração via `IMapProvider` interface

### Testes
- Adicionar testes unitários para validators
- Testes E2E com Playwright para fluxos críticos
- Testar com datasets grandes (1000+ cabos)

---

## 🔗 Referências

- [Mapbox GL Draw Documentation](https://github.com/mapbox/mapbox-gl-draw)
- [Mapbox Directions API](https://docs.mapbox.com/api/navigation/directions/)
- [Vue Headless UI - Combobox](https://headlessui.com/vue/combobox)
- [Command Pattern for Undo/Redo](https://refactoring.guru/design-patterns/command)

---

**Última atualização**: 05/03/2026  
**Responsável**: Equipe de Desenvolvimento  
**Status**: Aguardando aprovação
