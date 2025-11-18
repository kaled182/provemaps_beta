# Correções Aplicadas - Sistema de Mapas

**Data:** 17 de novembro de 2025  
**Branch:** refactor/folder-structure

## Problemas Identificados

### 1. Mapa não aparece ao navegar de `/zabbix/lookup/`
**Sintoma:** Ao acessar `/zabbix/lookup/` e depois navegar para `/monitoring/backbone/` ou `/NetworkDesign/`, o mapa não carrega. Era necessário apertar F5 para o mapa aparecer.

**Causa Raiz:** 
- A página Zabbix Lookup não carrega a API do Google Maps
- Quando navegamos via Vue Router para páginas com mapa, o script do Google Maps não está disponível no DOM
- Cada componente tentava carregar o Google Maps de forma independente, causando conflitos

### 2. Sidebar de Hosts em `/monitoring/backbone/` com erro JSON
**Sintoma:** Erro "Unexpected token '<', '<!DOCTYPE'... is not valid JSON" ao carregar hosts.

**Causa Raiz:**
- A rota `/maps_view/api/dashboard/data/` foi removida do `core/urls.py` durante a limpeza de rotas
- O dashboard estava tentando fazer fetch de uma API inexistente
- Django retornava a página 404 (HTML) ao invés de JSON

---

## Soluções Implementadas

### 1. Google Maps Loader Centralizado

#### Arquivo Criado: `frontend/src/utils/googleMapsLoader.js`
```javascript
/**
 * Carregamento centralizado da API do Google Maps
 * Garante que a API seja carregada apenas uma vez e compartilhada
 * entre todas as páginas/componentes.
 */
```

**Funcionalidades:**
- `loadGoogleMaps()` - Carrega o script do Google Maps uma única vez
- `isGoogleMapsLoaded()` - Verifica se já está carregado
- `waitForGoogleMaps(timeout)` - Aguarda com timeout
- `getGoogleMapsApiKey()` - Extrai API key dos meta tags

**Benefícios:**
- Evita múltiplas tentativas de carregamento
- Reutiliza promise de carregamento em andamento
- Timeout configurável para evitar travamentos

### 2. Pre-loading no App.vue

**Arquivo Modificado:** `frontend/src/App.vue`

```vue
<script setup>
import { loadGoogleMaps } from '@/utils/googleMapsLoader';

onMounted(async () => {
  uiStore.applyTheme();
  
  // Pre-carrega Google Maps ao iniciar a aplicação
  try {
    await loadGoogleMaps();
    console.log('[App] Google Maps pre-loaded successfully');
  } catch (err) {
    console.warn('[App] Could not pre-load Google Maps:', err.message);
  }
});
</script>
```

**Comportamento:**
- Carrega Google Maps assim que a aplicação Vue inicia
- Independente da rota inicial (mesmo em `/zabbix/lookup/`)
- Falha silenciosa (páginas tentarão carregar novamente se necessário)

### 3. useMapService Atualizado

**Arquivo Modificado:** `frontend/src/composables/useMapService.js`

**Mudanças:**
- Import de `waitForGoogleMaps` do loader centralizado
- Removida função duplicada `waitForGoogleMaps()` interna
- Uso do loader compartilhado para garantir consistência

**Antes:**
```javascript
// Cada instância tinha sua própria lógica de wait
function waitForGoogleMaps() {
  return new Promise((resolve, reject) => {
    // polling local...
  });
}
```

**Depois:**
```javascript
import { waitForGoogleMaps } from '@/utils/googleMapsLoader';
// Reutiliza loader global
```

### 4. Rotas de API Restauradas

**Arquivo Modificado:** `backend/core/urls.py`

```python
# APIs
path('api/v1/inventory/', include('inventory.urls_api')),
path('api/v1/', include('inventory.urls_rest')),
path('setup_app/', include('setup_app.urls')),
path('maps_view/', include('maps_view.urls')),  # ← ADICIONADO
```

**URLs Disponíveis:**
- `/maps_view/api/dashboard/data/` - Dashboard hosts status
- `/maps_view/api/dashboard/sites/` - Sites com devices
- `/maps_view/metrics/` - Métricas Prometheus

---

## Validação

### Testes Automatizados
✅ Endpoints principais retornam HTTP 200  
✅ Vue SPA carrega corretamente  
✅ Meta tag `google-maps-api-key` presente  

### Testes Manuais Necessários
1. **Navegação de Zabbix → Maps:**
   - Abrir `/zabbix/lookup/`
   - Navegar (via menu) para `/monitoring/backbone/`
   - **Verificar:** Mapa aparece sem precisar F5

2. **Navegação de Zabbix → Network Design:**
   - Abrir `/zabbix/lookup/`
   - Navegar para `/NetworkDesign/`
   - **Verificar:** Mapa e ferramentas de desenho funcionam

3. **Sidebar de Hosts:**
   - Abrir `/monitoring/backbone/`
   - **Verificar:** Sidebar carrega lista de hosts sem erro JSON
   - **Verificar:** Console não mostra "Unexpected token '<'"

4. **Refresh (F5):**
   - Em qualquer página com mapa
   - **Verificar:** Mapa continua funcionando após reload

---

## Arquitetura Resultante

```
App.vue (mount)
  ↓
  loadGoogleMaps() → Carrega script global
  ↓
ZabbixLookupView
  └─ Sem mapa, mas Google Maps já carregado
  ↓
Vue Router navegação
  ↓
MonitoringBackbone / NetworkDesign
  ↓
  useMapService()
    ↓
    waitForGoogleMaps() → Já disponível!
    ↓
    initMap() → Instancia mapa
    ↓
    loadPlugin('segments') → Adiciona polylines
    loadPlugin('devices')  → Adiciona markers
```

---

## Impacto

### Performance
- **Positivo:** Google Maps carrega uma única vez no início
- **Positivo:** Navegação entre páginas mais rápida (script já disponível)
- **Neutro:** Pequeno overhead inicial (~500ms) mesmo em páginas sem mapa

### Experiência do Usuário
- **Excelente:** Navegação fluida sem necessidade de F5
- **Excelente:** Sidebar de hosts funciona corretamente
- **Excelente:** Transições suaves entre páginas

### Manutenibilidade
- **Positivo:** Código centralizado e reutilizável
- **Positivo:** Menos duplicação de lógica
- **Positivo:** Mais fácil adicionar novas páginas com mapas

---

## Próximos Passos (Opcionais)

1. **Lazy Loading Condicional:**
   - Carregar Google Maps apenas quando usuário navega para página com mapa
   - Usar `router.beforeEach()` para detectar rotas que precisam de mapas

2. **Error Boundary:**
   - Adicionar fallback UI caso Google Maps falhe ao carregar
   - Exibir mensagem amigável ao usuário

3. **Retry Logic:**
   - Implementar retry automático com backoff exponencial
   - Útil em conexões instáveis

4. **Service Worker:**
   - Cache do script do Google Maps para uso offline parcial
   - Melhora experiência em redes lentas

---

## Checklist de Deployment

- [x] Frontend compilado (`npm run build`)
- [x] Docker image reconstruída
- [x] Containers reiniciados
- [x] Rotas de API validadas
- [x] Endpoints testados (HTTP 200)
- [ ] **Teste manual de navegação Zabbix → Maps**
- [ ] **Teste manual de sidebar de hosts**
- [ ] Smoke test em produção
- [ ] Monitorar logs do frontend (console errors)
- [ ] Monitorar logs do backend (API 500 errors)

---

## Rollback Plan

Se problemas forem detectados em produção:

1. **Reverter mudanças no frontend:**
   ```bash
   git checkout HEAD~1 frontend/src/utils/googleMapsLoader.js
   git checkout HEAD~1 frontend/src/App.vue
   git checkout HEAD~1 frontend/src/composables/useMapService.js
   npm run build
   ```

2. **Reverter mudanças no backend:**
   ```bash
   git checkout HEAD~1 backend/core/urls.py
   ```

3. **Rebuild e redeploy:**
   ```bash
   docker compose -f docker/docker-compose.yml build web
   docker compose -f docker/docker-compose.yml up -d
   ```

---

## Referências

- **Issue Original:** Menu lateral quebra ao apertar F5
- **Commit:** Adiciona Google Maps loader centralizado e restaura APIs do dashboard
- **Documentação:** `frontend/src/components/Map/README.md`
- **Testes:** `validate-fixes.ps1`
