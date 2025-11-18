# 🎯 CAUSA RAIZ IDENTIFICADA E CORRIGIDA

## ❌ Problema Original
Menu lateral quebrava no primeiro F5 em `/NetworkDesign/`

## 🔍 Causa Raiz Descoberta

### 1. **Race Condition no Vue Component**
- `uiStore.isNavMenuOpen` era lido durante render **antes** do localStorage ser carregado
- Resultado: `menuWidth` ficava com valor intermediário (~135px)
- **Correção:** `onBeforeMount()` agora força leitura do `localStorage` **antes** do primeiro render

### 2. **CACHE DO NAVEGADOR SERVINDO JS ANTIGO** ⚠️ **PRINCIPAL**
- `docker-compose.yml` forçava `STATIC_ASSET_VERSION=1.0.2` (valor fixo)
- Navegador cacheava `main.js?v=1.0.2` indefinidamente
- Mesmo com código Vue corrigido, o **browser servia JavaScript antigo**
- **Correção:** Removida env var fixa, agora usa timestamp UTC dinâmico

## ✅ Correções Aplicadas

### **Código Vue (TheNavMenu.vue)**
```vue
<script setup>
// Nova ref local para estabilizar CSS variable
const menuWidth = ref('280px');

// Garantir sincronização com localStorage ANTES do mount
onBeforeMount(() => {
  const storedValue = localStorage.getItem('ui.navMenuOpen');
  const shouldBeOpen = storedValue === null ? true : storedValue === 'true';
  
  if (uiStore.isNavMenuOpen !== shouldBeOpen) {
    console.warn('[NavMenu] Store dessincronizado, corrigindo');
    uiStore.isNavMenuOpen = shouldBeOpen;
  }
  
  menuWidth.value = shouldBeOpen ? '280px' : '60px';
});

// Watcher para sincronizar mudanças do store
watch(() => uiStore.isNavMenuOpen, (newValue) => {
  menuWidth.value = newValue ? '280px' : '60px';
});
</script>

<template>
  <aside :style="{ '--nav-menu-width': menuWidth }">
    <!-- Usa menuWidth ao invés de computed dinâmico -->
  </aside>
</template>

<style scoped>
.nav-menu {
  /* CSS com !important para evitar shrinking */
  flex: 0 0 var(--nav-menu-width,280px) !important;
  width: var(--nav-menu-width,280px) !important;
  min-width: var(--nav-menu-width,280px) !important;
  max-width: var(--nav-menu-width,280px) !important;
}
</style>
```

### **Django Settings (settings/dev.py)**
```python
# Timestamp UTC dinâmico ao invés de fixo
STATIC_ASSET_VERSION = (
    f"{_git_sha()}-{_time.strftime('%Y%m%d%H%M%S', _time.gmtime())}"
)
# Resultado: nosha-20251115045304 (15 nov 04:53 UTC)
```

### **Docker Compose (docker-compose.yml)**
```yaml
# ANTES (ERRADO):
environment:
  STATIC_ASSET_VERSION: "1.0.2"  # ❌ Valor fixo causava cache infinito

# DEPOIS (CORRETO):
# STATIC_ASSET_VERSION removido - usa timestamp dinâmico do settings
```

## 🧪 Como Testar Agora

### **IMPORTANTE: LIMPAR CACHE DO NAVEGADOR**

**Opção 1: Hard Refresh (Recomendado)**
```
Chrome/Edge: Ctrl + Shift + R (ou Cmd + Shift + R no Mac)
Firefox:     Ctrl + Shift + R
```

**Opção 2: DevTools**
1. Abra DevTools (F12)
2. Aba **Application** → **Storage** → **Clear site data**
3. Marque **Cache storage** e **Cached images and files**
4. Click **Clear site data**
5. Feche e reabra o navegador

**Opção 3: Incognito/Private Mode**
```
Ctrl + Shift + N (Chrome/Edge)
Ctrl + Shift + P (Firefox)
```

### **Sequência de Validação**

1. **Limpe o cache** (escolha uma opção acima)

2. **Acesse:**
   ```
   http://localhost:8000/accounts/login/
   ```

3. **Login:**
   - Usuário: `admin`
   - Senha: `admin123`

4. **Navegue para:**
   ```
   http://localhost:8000/NetworkDesign/
   ```

5. **Teste de F5 (CRÍTICO):**
   - Pressione **F5** pelo menos **5 vezes**
   - Menu lateral deve permanecer visível **sempre**
   - Largura deve ser estável (280px expandido ou 60px recolhido)

6. **Verificar Console (DevTools F12):**
   ```javascript
   // Deve aparecer no console ao carregar:
   [NavMenu] onBeforeMount - menuWidth: 280px isOpen: true
   ```

7. **Testar Toggle:**
   - Clique no botão de expandir/recolher (setas duplas)
   - Transição deve ser suave (300ms)
   - Largura deve alternar entre 280px ↔ 60px

8. **Testar Outras Rotas:**
   ```
   http://localhost:8000/monitoring/monitoring-all
   http://localhost:8000/monitoring/backbone
   ```
   - Menu deve persistir em todas as rotas
   - F5 em cada uma não deve quebrar o menu

## 📊 Validação Técnica

### **Verificar Asset Version no HTML**
```powershell
$html = (Invoke-WebRequest -Uri "http://localhost:8000/NetworkDesign/" -UseBasicParsing).Content
$html -match 'main\.js\?v=([^"]+)"'
# Deve retornar: nosha-20251115045304 (ou timestamp posterior)
```

### **Verificar JavaScript Carregado**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/static/vue-spa/assets/main.js?v=nosha-20251115045304" `
  -Method HEAD | Select-Object StatusCode,@{Name='Size';Expression={$_.Headers.'Content-Length'}}
# Deve retornar: 200, Size: 420009 bytes
```

### **Debug no Console do Navegador**
```javascript
// Executar no Console (F12)
window.__navMenuDebug()

// Saída esperada:
{
  width: 280,
  height: 937,
  isNavMenuOpen: true,
  path: "/NetworkDesign/"
}
```

## 🚨 Se o Menu Ainda Quebrar

### **Diagnóstico Rápido**

1. **Verificar se está usando JS antigo:**
   ```javascript
   // No console do navegador:
   localStorage.getItem('ui.navMenuOpen')
   // Se retornar null ou 'false', forçar:
   localStorage.setItem('ui.navMenuOpen', 'true')
   location.reload()
   ```

2. **Verificar versão do asset carregado:**
   - Abra DevTools → **Network**
   - Filtre por `main.js`
   - Verifique query string `?v=nosha-20251115...`
   - Se aparecer `?v=1.0.2` → **ainda está com cache antigo!**

3. **Forçar reload do Docker:**
   ```powershell
   cd D:\provemaps_beta\docker
   docker compose down
   docker compose up -d
   Start-Sleep -Seconds 10
   # Depois: Hard refresh no navegador (Ctrl+Shift+R)
   ```

4. **Coletar logs de debug:**
   ```javascript
   // Console do navegador:
   window.__navMenuDebug()
   
   // Enviar screenshot mostrando:
   // - Largura do menu
   // - Valor de isNavMenuOpen
   // - Path atual
   // - Console logs [NavMenu]
   ```

## 📝 Teste de Regressão (Automated)

```powershell
# Executar suite E2E Playwright:
cd D:\provemaps_beta\frontend
npx playwright test tests\nav_menu.spec.ts

# Deve passar 3/3 testes:
# ✓ Menu visível em /monitoring/monitoring-all
# ✓ Menu visível em /monitoring/backbone
# ✓ Menu visível em /NetworkDesign/
```

## 🎯 Resumo da Solução

| Componente | Problema | Solução |
|------------|----------|---------|
| **TheNavMenu.vue** | Race condition com localStorage | `onBeforeMount()` + ref local `menuWidth` |
| **CSS** | Flexbox permitia shrinking | `!important` em 4 propriedades + min/max-width |
| **settings.dev** | Timestamp local errado | Mudado para `gmtime()` (UTC) |
| **docker-compose.yml** | STATIC_ASSET_VERSION fixo | Removida env var, usa timestamp dinâmico |
| **Browser Cache** | Servia JS antigo indefinidamente | Novo timestamp a cada restart força bust |

---

## ✅ Status Final

- ✅ Código Vue corrigido com `onBeforeMount()`
- ✅ CSS hardened com `!important` + min/max-width
- ✅ Cache busting dinâmico (timestamp UTC)
- ✅ Docker env var removida
- ✅ Build realizado (420.01 KB)
- ✅ Container reiniciado
- ✅ Versão atual: `nosha-20251115045304`

**Próximo passo:** LIMPAR CACHE DO NAVEGADOR e testar com Ctrl+Shift+R ⚡
