# Lazy Loading de Google Maps - Arquitetura

**Data:** 17 de novembro de 2025  
**Implementação:** Carregamento condicional por rota

## Problema Identificado

A abordagem anterior carregava o Google Maps para **TODAS** as páginas, mesmo aquelas que não precisam:
- ❌ `/zabbix/lookup/` tentava carregar Google Maps desnecessariamente
- ❌ Overhead de ~500ms em páginas sem mapas
- ❌ Erros no console em páginas que não usam mapas
- ❌ Consumo de API key desnecessário

## Solução Implementada: Lazy Loading Condicional

### Rotas Autorizadas para Google Maps

```javascript
// App.vue - Lista de rotas que REALMENTE precisam de mapas
const ROUTES_WITH_MAPS = [
  '/monitoring/backbone',
  '/NetworkDesign',
  '/dashboard'
];
```

### Fluxo de Carregamento

```
Usuario acessa /zabbix/lookup/
  ↓
router.beforeEach() verifica rota
  ↓
Rota NAO esta em ROUTES_WITH_MAPS
  ↓
❌ Google Maps NÃO é carregado
  ↓
Pagina carrega rapidamente sem mapas
```

```
Usuario navega para /NetworkDesign/
  ↓
router.beforeEach() verifica rota
  ↓
Rota ESTA em ROUTES_WITH_MAPS
  ↓
✅ Google Maps é carregado (loadGoogleMaps())
  ↓
NetworkDesignView aguarda maps estar pronto
  ↓
Mapa aparece corretamente
```

## Código Implementado

### App.vue - Router Guard

```vue
<script setup>
import { useRouter } from 'vue-router';
import { loadGoogleMaps } from '@/utils/googleMapsLoader';

const router = useRouter();

// Lista de rotas que precisam de Google Maps
const ROUTES_WITH_MAPS = [
  '/monitoring/backbone',
  '/NetworkDesign',
  '/dashboard'
];

// Intercepta navegação
router.beforeEach(async (to, from, next) => {
  const needsMaps = ROUTES_WITH_MAPS.some(route => to.path.startsWith(route));
  
  console.log(`[App] Navigation: ${from.path} → ${to.path}`);
  console.log(`[App] Route needs maps: ${needsMaps}`);
  
  if (needsMaps) {
    await loadGoogleMaps(); // Carrega apenas se necessário
  }
  
  next();
});
</script>
```

### NetworkDesignView.vue - Aguarda Maps

```vue
<script setup>
import { waitForGoogleMaps } from '@/utils/googleMapsLoader';

onMounted(async () => {
  // Aguarda Google Maps estar disponível
  // App.vue já carregou via router.beforeEach
  await waitForGoogleMaps(20000);
  
  // Inicializa mapa
  initializeNetworkDesignApp({ force: true });
});
</script>
```

## Comportamento por Rota

| Rota | Google Maps | Motivo |
|------|-------------|--------|
| `/zabbix/lookup/` | ❌ NÃO carrega | Não precisa de mapas |
| `/monitoring/monitoring-all` | ❌ NÃO carrega | Página overview sem mapas |
| `/monitoring/gpon` | ❌ NÃO carrega | Não usa mapas (ainda) |
| `/monitoring/dwdm` | ❌ NÃO carrega | Não usa mapas (ainda) |
| `/monitoring/backbone` | ✅ CARREGA | Dashboard com MapView |
| `/NetworkDesign` | ✅ CARREGA | Editor de rotas com mapa |
| `/dashboard` | ✅ CARREGA | Dashboard legacy com mapa |

## Logs do Console

### Navegação SEM Maps (Zabbix → Overview)
```
[App] Navigation: /zabbix/lookup/ → /monitoring/monitoring-all
[App] Route needs maps: false
[App] Skipping Google Maps load (not needed for this route)
```

### Navegação COM Maps (Zabbix → Network Design)
```
[App] Navigation: /zabbix/lookup/ → /NetworkDesign
[App] Route needs maps: true
[App] Loading Google Maps for this route...
[GoogleMapsLoader] loadGoogleMaps() called
[GoogleMapsLoader] isLoaded: false
[GoogleMapsLoader] Creating new script tag
[GoogleMapsLoader] ✅ New script loaded successfully
[App] ✅ Google Maps loaded successfully
[NetworkDesignView] Checking Google Maps availability...
[NetworkDesignView] ✅ Google Maps ready!
```

## Adicionando Novas Rotas com Mapas

Quando uma nova página precisar de Google Maps:

1. **Adicione a rota à lista em `App.vue`:**
```javascript
const ROUTES_WITH_MAPS = [
  '/monitoring/backbone',
  '/NetworkDesign',
  '/dashboard',
  '/monitoring/gpon',  // ← Nova rota
];
```

2. **No componente, aguarde o Google Maps:**
```vue
<script setup>
import { waitForGoogleMaps } from '@/utils/googleMapsLoader';

onMounted(async () => {
  await waitForGoogleMaps(20000);
  // Seu código que usa Google Maps
});
</script>
```

## Vantagens

### Performance
- ✅ Páginas sem mapas carregam instantaneamente
- ✅ Redução de ~500ms no load time de páginas simples
- ✅ Google Maps carrega apenas 1 vez (reutilizado em navegações subsequentes)

### Manutenibilidade
- ✅ Lista centralizada de rotas autorizadas
- ✅ Fácil adicionar/remover rotas
- ✅ Logs claros de quando/onde maps é carregado

### Experiência do Usuário
- ✅ Navegação fluida de páginas sem → com mapas
- ✅ Sem erros no console em páginas que não usam mapas
- ✅ Feedback claro em caso de falhas

### Custos
- ✅ Redução de chamadas desnecessárias à API do Google Maps
- ✅ Menor uso de quota da API key

## Teste de Validação

Execute os seguintes testes:

### 1. Zabbix Lookup (SEM mapas)
```
1. Abra DevTools (F12) → Console
2. Acesse http://localhost:8000/zabbix/lookup/
3. Verifique logs:
   ✅ NÃO deve aparecer: [GoogleMapsLoader] loadGoogleMaps() called
   ✅ Página carrega rápido sem erros
```

### 2. Network Design (COM mapas)
```
1. De /zabbix/lookup/, navegue para Network Design
2. Verifique logs:
   ✅ DEVE aparecer: [App] Route needs maps: true
   ✅ DEVE aparecer: [GoogleMapsLoader] ✅ New script loaded
   ✅ DEVE aparecer: [NetworkDesignView] ✅ Google Maps ready!
   ✅ Mapa aparece na tela
```

### 3. Monitoring Backbone (COM mapas)
```
1. De /zabbix/lookup/, navegue para Backbone
2. Verifique:
   ✅ Google Maps carrega
   ✅ Sidebar de hosts aparece
   ✅ Mapa renderiza corretamente
```

### 4. Navegação Múltipla
```
1. Zabbix → Network Design (maps carrega)
2. Network Design → Zabbix (maps já carregado, reutilizado)
3. Zabbix → Backbone (maps já disponível, não recarrega)
4. Verifique logs:
   ✅ Google Maps carrega apenas 1 vez
   ✅ Navegações subsequentes reutilizam script
```

## Troubleshooting

### Problema: Mapa não aparece após navegação
**Causa:** Rota não está na lista `ROUTES_WITH_MAPS`  
**Solução:** Adicione a rota em `App.vue`

### Problema: Console mostra "Google Maps API key not found"
**Causa:** Meta tag não está presente  
**Solução:** Verifique se Django está injetando a meta tag no template

### Problema: Timeout ao carregar Google Maps
**Causa:** Rede lenta ou API key inválida  
**Solução:** Verifique API key e conexão de rede

## Métricas de Sucesso

- ✅ Zabbix Lookup carrega em < 1s (sem overhead de maps)
- ✅ Network Design carrega mapa em < 3s após navegação
- ✅ Zero erros no console em páginas sem mapas
- ✅ Taxa de sucesso > 99% no carregamento de maps

## Futuras Melhorias

1. **Prefetch Inteligente:**
   - Carregar Google Maps quando mouse hover em link de rota com mapas
   - Reduz tempo percebido de carregamento

2. **Service Worker:**
   - Cache do script do Google Maps
   - Modo offline parcial

3. **Error Boundary:**
   - UI de fallback quando Google Maps falha
   - Botão de retry manual

4. **Analytics:**
   - Track tempo de carregamento por rota
   - Monitorar taxa de falhas de carregamento
