# 🧪 Instruções de Teste no Navegador - Canary Rollout Phase 1

**Data:** 12/11/2025 — 18:05  
**Configuração Atual:** 100% Vue Dashboard (para testes)  
**Credenciais:** admin / admin123

---

## 🌐 Acessar Dashboard

### 1. Abrir Navegador
```
URL: http://localhost:8000/maps_view/dashboard
```

### 2. Login
- **Username:** `admin`
- **Password:** `admin123`

---

## ✅ Checklist de Testes

### A. Dashboard Load (Vue SPA)
- [ ] Página carrega em <3 segundos
- [ ] Sem erros no console (F12 → Console)
- [ ] Header mostra: **"MapsProve Dashboard"**
- [ ] Sidebar visível com StatusChart
- [ ] Map container carregado (direita)
- [ ] Connection status indicator presente

**Verificar no Console:**
```javascript
// Should see Vue 3 app initialized
// No errors related to missing assets
```

---

### B. WebSocket Connection
- [ ] F12 → Network → WS tab
- [ ] WebSocket URL: `ws://localhost:8000/ws/dashboard/status/`
- [ ] Status: **101 Switching Protocols**
- [ ] Frames com JSON messages (mensagens periódicas)
- [ ] Status indicator: **"Conectado"** (green dot)

**Verificar Frames:**
- Clique na conexão WebSocket
- Aba "Messages" / "Frames"
- Deve receber JSON com: `{"hosts": {...}, "summary": {...}}`

---

### C. Host Cards
- [ ] StatusChart (topo da sidebar) renderiza com barras coloridas
- [ ] Host cards exibem:
  - ✅ Host name
  - ✅ Status badge (Operacional/Atenção/Crítico/Offline)
  - ✅ Metrics: CPU %, Memory %, Uptime
  - ✅ Last update timestamp (ex: "2m atrás")
- [ ] Cards com cores de status corretas:
  - Verde: Operacional
  - Amarelo: Atenção
  - Vermelho: Crítico
  - Cinza: Offline

**Se nenhum host aparecer:**
- Verificar API: http://localhost:8000/api/v1/dashboard/
- Deve retornar JSON com hosts (ou vazio se Zabbix não configurado)

---

### D. Google Maps Integration
- [ ] Map carrega (ou mostra mensagem de API key se não configurada)
- [ ] Centro do mapa posicionado corretamente
- [ ] Zoom level adequado

**Se API Key inválida:**
- Esperado: Mensagem "Google Maps API key required"
- Map container ainda renderiza (cinza)

---

### E. Segments Loading (BBox API)
- [ ] Pan/zoom no mapa
- [ ] Segments carregam ao mover viewport
- [ ] Polylines renderizam com cores:
  - 🟢 Verde (#16a34a): operational
  - 🔵 Azul (#3b82f6): maintenance
  - 🟠 Laranja (#f59e0b): degraded
  - ⚪ Cinza (#6b7280): unknown
- [ ] Click em segment → InfoWindow abre com detalhes da rota

**Verificar no Console:**
```javascript
// Should see fetch requests to:
// /api/v1/inventory/segments/?bbox=...
```

---

### F. Map Controls
- [ ] Botão "Ajustar visualização" (fit bounds) presente
- [ ] Click → Map zoom/pan para mostrar todos os segments
- [ ] Animação suave
- [ ] Botão "Toggle Legend" funciona
  - Click → Legend panel aparece/desaparece
  - Estado persiste durante sessão

**Keyboard Navigation:**
- [ ] Tab: Cycle pelos botões
- [ ] Enter: Ativa botão focado
- [ ] Focus indicators visíveis (outline azul)

---

### G. Mobile Responsive
**Resize browser para 375px (iPhone SE):**
- [ ] F12 → Toggle device toolbar (Ctrl+Shift+M)
- [ ] Sidebar esconde automaticamente
- [ ] Toggle button (☰) aparece no header
- [ ] Click toggle → Sidebar slide-in suavemente
- [ ] Sidebar width: 80% da tela (max 320px)
- [ ] Map controls touch-friendly (≥44px)
- [ ] Sem scroll horizontal

---

### H. Performance
**DevTools Performance:**
- [ ] F12 → Performance tab
- [ ] Record page load
- [ ] Stop recording após load completo
- [ ] Métricas:
  - **Load Time:** _____ ms (target <3000ms)
  - **FCP:** _____ ms (target <1500ms)
  - **LCP:** _____ ms (target <2500ms)

**Network Tab:**
- [ ] main.js: ~96 KB (gzipped ~38 KB)
- [ ] DashboardView.js: ~13 KB (gzipped ~5 KB)
- [ ] MapView.js (lazy): ~26 KB (gzipped ~9.5 KB)
- [ ] Total < 200 KB

---

### I. Error Handling
**Simulate Network Issues:**
1. F12 → Network → Throttle to "Offline"
2. Wait 5 seconds
3. Switch back to "Online"

**Verificar:**
- [ ] Dashboard mostra estado de erro gracefully
- [ ] WebSocket status: "Desconectado" (red dot)
- [ ] WebSocket reconecta automaticamente após 2s, 4s, 8s
- [ ] Sem crash da aplicação
- [ ] Sem erros unhandled no console

---

### J. Virtual Scrolling (Se >20 hosts)
**Se houver muitos hosts:**
- [ ] Scroll suave (60fps)
- [ ] Apenas ~10-15 cards renderizados no DOM
- [ ] Cards aparecem/desaparecem ao scrollar
- [ ] Sem lag ou frame drops

**Verificar no Elements tab:**
- Inspecionar `.host-cards-list-virtual`
- Contar elementos `.host-card` no DOM
- Deve ser ~10-15, não todos os hosts

---

## 🔍 Troubleshooting

### Página em Branco
```javascript
// Console deve mostrar erro específico
// Comum: Failed to fetch /api/v1/dashboard/
// Solução: Verificar se backend está rodando
```

### WebSocket Não Conecta
```bash
# Verificar Redis
docker compose -f docker/docker-compose.yml ps redis

# Logs do web service
docker compose -f docker/docker-compose.yml logs web | Select-String "websocket"
```

### Segments Não Carregam
```bash
# Testar API diretamente
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/inventory/segments/?bbox=-48,-25,-47,-24"

# Verificar se há RouteSegments no banco
docker compose exec web python manage.py shell
>>> from inventory.models import RouteSegment
>>> RouteSegment.objects.count()
```

### Map Não Carrega
- **API Key inválida:** Esperado (mostra mensagem)
- **Erro JS:** Verificar console para stack trace
- **Componente não renderiza:** Checar se `MapView.js` foi carregado (lazy load)

---

## 📸 Screenshots Esperados

### Desktop (>768px)
```
+----------------------------------+
| Header: MapsProve Dashboard      |
+--------+-------------------------+
| Side-  | Map                     |
| bar    | (Google Maps)           |
| (25%)  | (75%)                   |
|        |                         |
| Status |                         |
| Chart  | Segments (polylines)    |
|        |                         |
| Host   |                         |
| Cards  | Controls (bottom-right) |
|        | - Fit bounds            |
|        | - Toggle legend         |
+--------+-------------------------+
```

### Mobile (<768px)
```
+----------------------------------+
| Header: ☰ MapsProve Dashboard    |
+----------------------------------+
| Map (Full width)                 |
| (Google Maps)                    |
|                                  |
| Segments                         |
|                                  |
| Controls (bottom-right)          |
+----------------------------------+

// Sidebar escondida (toggle abre overlay)
```

---

## 🎯 Critérios de Sucesso

### Mínimo Aceitável (MVP):
- ✅ Dashboard carrega sem erros
- ✅ WebSocket conecta (status verde)
- ✅ Host cards renderizam (ou empty state)
- ✅ Map inicializa (mesmo sem API key)
- ✅ Controles respondem a clicks
- ✅ Mobile responsive funciona

### Ideal (Production-Ready):
- ✅ Load time <3s
- ✅ Segments carregam e renderizam
- ✅ InfoWindow abre com dados corretos
- ✅ Performance 60fps durante scroll
- ✅ Virtual scroll para >20 hosts
- ✅ Sem erros no console
- ✅ WebSocket reconexão automática

---

## 📊 Métricas a Registrar

| Métrica | Valor Medido | Target | Status |
|---------|--------------|--------|--------|
| Load Time | _______ ms | <3000ms | [ ] |
| FCP | _______ ms | <1500ms | [ ] |
| LCP | _______ ms | <2500ms | [ ] |
| Bundle Size | _______ KB | <100KB | [ ] |
| WebSocket Connect | _______ ms | <1000ms | [ ] |
| Segments Load | _______ ms | <2000ms | [ ] |

---

## 🚀 Após Testes Bem-Sucedidos

### Voltar para Canary 10%
```powershell
# 1. Edit docker-compose.yml
# VUE_DASHBOARD_ROLLOUT_PERCENTAGE: "10"

# 2. Restart web
docker compose -f docker/docker-compose.yml restart web

# 3. Testar distribuição (10 sessões, ~1 Vue, ~9 Legacy)
```

### Iniciar Monitoring 24h
```powershell
# Ver: doc/operations/MONITORING_COMMANDS_PHASE1.md
# Health checks a cada 4h
```

---

**Status:** 🧪 Teste Manual em Andamento  
**Next Step:** Validar todos os checkboxes acima  
**Última atualização:** 12/11/2025 — 18:05
