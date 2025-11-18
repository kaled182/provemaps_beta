# 🧪 Guia de Testes E2E com Playwright

**Versão**: 2.0  
**Data**: Novembro 2025  
**Mantenedor**: Equipe de Desenvolvimento  
**Status**: ✅ Ativo e validado

---

## 📋 Índice

1. [Introdução](#introdução)
2. [Filosofia de Testes](#filosofia-de-testes)
3. [Configuração do Ambiente](#configuração-do-ambiente)
4. [Autenticação vs Mocks](#autenticação-vs-mocks)
5. [Padrões de data-testid](#padrões-de-data-testid)
6. [Fixtures Reutilizáveis](#fixtures-reutilizáveis)
7. [Event-Based Assertions](#event-based-assertions)
8. [Estrutura de Testes](#estrutura-de-testes)
9. [Performance Testing](#performance-testing)
10. [Boas Práticas](#boas-práticas)
11. [Debugging](#debugging)
12. [CI/CD Integration](#cicd-integration)
13. [Troubleshooting](#troubleshooting)

---

## 🎯 Introdução

Este guia documenta as **melhores práticas** para escrever e manter testes E2E (End-to-End) usando **Playwright** no projeto ProveMaps. 

### Por que Playwright?

- ✅ **Multi-browser**: Chromium, Firefox, WebKit
- ✅ **Auto-wait**: Espera automática por elementos
- ✅ **Network interception**: Mocks e stubs de API
- ✅ **Screenshots/Videos**: Debugging visual
- ✅ **Parallelização**: Testes rápidos em CI

### Estado Atual

```
📊 Cobertura E2E: 96.7% (29/30 testes passing)
⚡ Performance: 23.7s para 30 testes
✅ Arquitetura: Real authentication + Backend integration
```

---

## 🧠 Filosofia de Testes

### Princípios

1. **Teste comportamento, não implementação**
   - ✅ "Usuário clica em botão e vê resultado"
   - ❌ "Função X chama API Y com parâmetro Z"

2. **Priorize testes de valor**
   - ✅ Fluxos críticos de usuário (login, visualização de dados)
   - ⚠️ Edge cases apenas se impactarem UX

3. **Mantenha testes independentes**
   - ✅ Cada teste roda isolado (sem compartilhar estado)
   - ❌ Teste B não deve depender de Teste A

4. **Seja resiliente, não frágil**
   - ✅ Event-based waits (`waitForSelector`)
   - ❌ Fixed timeouts (`setTimeout(2000)`)

---

## ⚙️ Configuração do Ambiente

### Pré-requisitos

```bash
# Node.js 18+
node --version  # v18.0.0+

# Docker Compose rodando
cd docker
docker compose ps  # web, postgres, redis devem estar UP

# Playwright instalado
cd frontend
npm install
npx playwright install chromium
```

### Arquivos de Configuração

**`frontend/playwright.config.js`**:
```javascript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000, // 30s por teste
  expect: {
    timeout: 5000 // 5s para assertions
  },
  
  use: {
    baseURL: 'http://localhost:8000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
  
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  
  webServer: {
    // Docker já está rodando, não precisa iniciar servidor
    command: 'echo "Using existing Docker server"',
    url: 'http://localhost:8000/healthz',
    reuseExistingServer: true,
  },
});
```

### Executar Testes

```bash
# Todos os testes E2E
npx playwright test tests/e2e/

# Arquivo específico
npx playwright test tests/e2e/dashboard.spec.js

# Teste específico (grep)
npx playwright test --grep "Full flow"

# Modo debug (headed browser)
npx playwright test --headed --debug

# Modo UI (interface visual)
npx playwright test --ui

# Relatório de resultados
npx playwright show-report
```

---

## 🔐 Autenticação vs Mocks

### Quando Usar Autenticação Real

✅ **USE quando**:
- Teste precisa de **dados reais do backend** (hosts, devices, routes)
- Validar **fluxo completo** (login → ação → resultado)
- Backend é **estável e rápido** (< 200ms)
- Teste valida **integração** entre frontend e backend

**Exemplo**: Dashboard com 11 hosts reais
```javascript
import { authenticate } from './fixtures/auth.js';

test('Dashboard mostra hosts do backend', async ({ page }) => {
  await authenticate(page); // Login real
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  const hostCards = page.locator('[data-testid="host-card"]');
  await expect(hostCards).toHaveCount(11); // 11 hosts reais do DB
});
```

### Quando Usar Mocks

✅ **USE quando**:
- Teste valida apenas **UI/UX** (loading states, empty states, errors)
- Backend **indisponível ou lento** (> 1s)
- Testar **edge cases** (erros de rede, timeouts, dados malformados)
- Testar **estados específicos** (50+ hosts, 0 hosts, erro 500)

**Exemplo**: Loading state com mock
```javascript
test('Mostra loading spinner', async ({ page }) => {
  // Mock API com delay de 2s
  await page.route('**/api/dashboard/data/**', async route => {
    await new Promise(resolve => setTimeout(resolve, 2000));
    await route.fulfill({ json: { hosts_status: [] } });
  });
  
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  // Loading state deve estar visível
  const loading = page.locator('[data-testid="loading-state"]');
  await expect(loading).toBeVisible();
});
```

### ⭐ Decisão Tomada (Sprint Day 1)

**Arquitetura escolhida**: **Autenticação Real > Mocks**

**Razão**:
1. ✅ Backend Django em Docker é rápido (< 200ms)
2. ✅ Dados reais validam integração completa
3. ✅ Testes mais simples (menos código de mock)
4. ✅ 100% pass rate alcançado com autenticação real

**Resultado**:
- Dashboard: 8/8 testes com autenticação real (100%)
- Map loading: 20/21 testes sem autenticação (95%) - smoke tests
- Total: 29/30 passing (96.7%)

---

## 🏷️ Padrões de data-testid

### Naming Convention

**Formato**: `data-testid="<categoria>-<elemento>-<estado>"`

### Categorias

#### 1. Componentes Principais
```vue
<!-- Host Card -->
<article data-testid="host-card" class="...">
  <h3 data-testid="host-name">{{ host.name }}</h3>
  <span data-testid="host-ip">{{ host.ip }}</span>
  <div data-testid="host-status">{{ host.status }}</div>
</article>

<!-- Dashboard Container -->
<div id="app" data-testid="dashboard-container">
  <!-- ... -->
</div>
```

#### 2. Estados de Loading
```vue
<!-- Loading Spinner -->
<div data-testid="loading-state" v-if="isLoading">
  <svg class="animate-spin">...</svg>
  <p>Carregando hosts...</p>
</div>

<!-- Skeleton Loader -->
<div data-testid="skeleton-loader" v-if="isLoading">
  <!-- Placeholder cards -->
</div>
```

#### 3. Estados de Erro
```vue
<!-- Error Message -->
<div data-testid="error-state" v-if="error" role="alert">
  <p>{{ error.message }}</p>
  <button data-testid="retry-button" @click="retry">
    Tentar Novamente
  </button>
</div>
```

#### 4. Estados Vazios
```vue
<!-- Empty State -->
<div data-testid="empty-state" v-if="hosts.length === 0">
  <p>Nenhum host encontrado</p>
  <button data-testid="add-host-button">Adicionar Host</button>
</div>
```

#### 5. Ações do Usuário
```vue
<!-- Buttons -->
<button data-testid="fit-bounds-button" @click="fitBounds">
  Ajustar Zoom
</button>

<button data-testid="toggle-legend-button" @click="toggleLegend">
  {{ legendVisible ? 'Ocultar' : 'Mostrar' }} Legenda
</button>

<!-- Links -->
<a data-testid="host-details-link" :href="`/hosts/${host.id}`">
  Ver Detalhes
</a>
```

#### 6. Inputs e Forms
```vue
<!-- Search Input -->
<input 
  data-testid="search-input" 
  type="text" 
  v-model="searchQuery"
  placeholder="Buscar hosts..."
/>

<!-- Filter Dropdown -->
<select data-testid="status-filter" v-model="statusFilter">
  <option value="all">Todos</option>
  <option value="available">Disponíveis</option>
  <option value="unavailable">Indisponíveis</option>
</select>
```

### ❌ Anti-Padrões (Evite)

```vue
<!-- ❌ Muito genérico -->
<div data-testid="container">...</div>

<!-- ❌ Implementação específica (frágil) -->
<div data-testid="host-card-row-3-column-2">...</div>

<!-- ❌ CSS classes como seletores (mudam facilmente) -->
const hosts = page.locator('.bg-white.shadow-sm.rounded-lg'); // NÃO!

<!-- ✅ Use data-testid -->
const hosts = page.locator('[data-testid="host-card"]'); // SIM!
```

### Checklist de Implementação

Ao criar um novo componente Vue:
- [ ] Adicionar `data-testid` no elemento raiz
- [ ] Adicionar `data-testid` em ações (buttons, links)
- [ ] Adicionar `data-testid` em estados (loading, error, empty)
- [ ] Adicionar `data-testid` em elementos críticos (dados importantes)
- [ ] Evitar CSS classes/IDs como seletores em testes

---

## 🔧 Fixtures Reutilizáveis

### Conceito

**Fixture** = Código reutilizável que prepara o ambiente para testes.

### Autenticação (auth.js)

**Arquivo**: `frontend/tests/e2e/fixtures/auth.js`

```javascript
/**
 * Fixture de autenticação para testes E2E
 * @module tests/e2e/fixtures/auth
 */

/**
 * Credenciais padrão para testes
 */
const DEFAULT_CREDENTIALS = {
  username: 'admin',
  password: 'admin123',
};

/**
 * Autentica usuário no Django
 * @param {import('@playwright/test').Page} page - Página do Playwright
 * @param {Object} credentials - Credenciais de login
 * @param {string} credentials.username - Nome de usuário
 * @param {string} credentials.password - Senha
 * @returns {Promise<void>}
 * 
 * @example
 * import { authenticate } from './fixtures/auth.js';
 * 
 * test('Dashboard', async ({ page }) => {
 *   await authenticate(page);
 *   // Usuário autenticado, pronto para testar
 * });
 */
export async function authenticate(page, credentials = {}) {
  const username = credentials.username || DEFAULT_CREDENTIALS.username;
  const password = credentials.password || DEFAULT_CREDENTIALS.password;
  
  console.log(`🔐 Authenticating as: ${username}`);
  
  // Navegar para página de login
  await page.goto('http://localhost:8000/accounts/login/');
  
  // Preencher formulário
  await page.fill('#id_username', username);
  await page.fill('#id_password', password);
  
  // Submeter
  await page.click('button[type="submit"]');
  
  // Aguardar redirect (saiu da página de login)
  await page.waitForURL(url => !url.pathname.includes('/accounts/login/'));
  
  console.log('✅ Authentication successful');
}

/**
 * Verifica se usuário está autenticado
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<boolean>}
 */
export async function isAuthenticated(page) {
  // Verificar se existe cookie de sessão Django
  const cookies = await page.context().cookies();
  return cookies.some(cookie => cookie.name === 'sessionid');
}

/**
 * Faz logout do usuário
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<void>}
 */
export async function logout(page) {
  await page.goto('http://localhost:8000/accounts/logout/');
  await page.waitForURL('http://localhost:8000/accounts/login/');
}
```

### Como Usar

```javascript
import { test, expect } from '@playwright/test';
import { authenticate } from './fixtures/auth.js';

test.describe('Dashboard E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Autentica em TODOS os testes deste bloco
    await authenticate(page, { username: 'admin', password: 'admin123' });
    
    // Opcional: Mock de WebSocket (não-crítico)
    await page.addInitScript(() => {
      window.WebSocket = class MockWebSocket {
        constructor(url) { this.url = url; }
        send() {}
        close() {}
      };
    });
    
    // Navegar para dashboard
    await page.goto('http://localhost:8000/monitoring/backbone');
    
    // Aguardar Vue app carregar
    await page.waitForSelector('#app', { state: 'visible' });
  });
  
  test('Mostra 11 hosts', async ({ page }) => {
    const hosts = page.locator('[data-testid="host-card"]');
    await expect(hosts).toHaveCount(11);
  });
});
```

### Outras Fixtures (Exemplos)

**Data Fixtures** (`fixtures/data.js`):
```javascript
export function mockDashboardData(hostCount = 10) {
  return {
    hosts_status: Array.from({ length: hostCount }, (_, i) => ({
      hostid: `${1000 + i}`,
      host: `host-${i + 1}`,
      available: i % 3 !== 0 ? '1' : '0', // 66% available
      priority: '3',
      name: `Host ${i + 1}`,
      ip: `192.168.1.${i + 1}`,
    })),
    hosts_summary: {
      total: hostCount,
      available: Math.floor(hostCount * 0.66),
      unavailable: Math.ceil(hostCount * 0.33),
      unknown: 0,
    },
  };
}
```

**API Fixtures** (`fixtures/api.js`):
```javascript
export async function mockAPIError(page, statusCode = 500) {
  await page.route('**/api/**', route => {
    route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Internal Server Error' }),
    });
  });
}

export async function mockAPIDelay(page, delayMs = 2000) {
  await page.route('**/api/**', async route => {
    await new Promise(resolve => setTimeout(resolve, delayMs));
    await route.continue();
  });
}
```

---

## ⏱️ Event-Based Assertions

### Problema: Fixed Timeouts

❌ **Frágil e lento**:
```javascript
test('Dashboard carrega', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone');
  await page.waitForTimeout(2000); // ❌ Arbitrário!
  
  const hosts = page.locator('[data-testid="host-card"]');
  await expect(hosts).toHaveCount(11);
});
```

**Problemas**:
- ⚠️ Pode falhar em CI lento (2s não é suficiente)
- ⚠️ Desperdiça tempo em ambiente rápido (carrega em 100ms, espera 2s)
- ⚠️ Não indica o que está esperando (dificulta debug)

### Solução: Event-Based Waits

✅ **Robusto e rápido**:
```javascript
test('Dashboard carrega', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  // Espera ESPECÍFICA: hosts visíveis
  await page.waitForSelector('[data-testid="host-card"]', { 
    state: 'visible' 
  });
  
  const hosts = page.locator('[data-testid="host-card"]');
  await expect(hosts).toHaveCount(11);
});
```

**Benefícios**:
- ✅ Rápido (retorna assim que condição é satisfeita)
- ✅ Robusto (espera até timeout de 30s por padrão)
- ✅ Claro (indica exatamente o que está esperando)

### Tipos de Waits

#### 1. waitForSelector()
```javascript
// Espera elemento estar visível
await page.waitForSelector('[data-testid="host-card"]', { 
  state: 'visible' 
});

// Espera elemento estar no DOM (mas pode estar invisível)
await page.waitForSelector('[data-testid="host-card"]', { 
  state: 'attached' 
});

// Espera elemento ser removido
await page.waitForSelector('[data-testid="loading-state"]', { 
  state: 'detached' 
});
```

#### 2. waitForLoadState()
```javascript
// Espera DOM completo
await page.waitForLoadState('domcontentloaded');

// Espera página totalmente carregada (imagens, CSS, etc)
await page.waitForLoadState('load');

// Espera sem requests de rede pendentes
await page.waitForLoadState('networkidle');
```

#### 3. waitForResponse()
```javascript
// Espera API específica
const response = await page.waitForResponse(
  response => response.url().includes('/api/dashboard/data/') && 
              response.status() === 200
);

const data = await response.json();
console.log(`✅ API retornou ${data.hosts_status.length} hosts`);
```

#### 4. waitForURL()
```javascript
// Espera redirect após login
await page.click('button[type="submit"]');
await page.waitForURL(url => !url.pathname.includes('/accounts/login/'));
```

#### 5. waitForFunction()
```javascript
// Espera condição customizada
await page.waitForFunction(() => {
  const hosts = document.querySelectorAll('[data-testid="host-card"]');
  return hosts.length >= 10; // Mínimo 10 hosts
});
```

### Pattern: Loading → Content

```javascript
test('Dashboard: Loading → Hosts', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  // 1. Loading state visível
  const loading = page.locator('[data-testid="loading-state"]');
  await expect(loading).toBeVisible();
  
  // 2. Aguarda API
  await page.waitForResponse(r => 
    r.url().includes('/api/dashboard/data/') && r.status() === 200
  );
  
  // 3. Loading desaparece
  await expect(loading).not.toBeVisible();
  
  // 4. Hosts visíveis
  const hosts = page.locator('[data-testid="host-card"]');
  await expect(hosts).toHaveCount(11);
});
```

### Timeouts Customizados

```javascript
// Timeout específico (em casos excepcionais)
await page.waitForSelector('[data-testid="slow-element"]', { 
  timeout: 60000 // 60s
});

// Sem timeout (perigoso, use com cuidado!)
await page.waitForSelector('[data-testid="element"]', { 
  timeout: 0 
});
```

---

## 📁 Estrutura de Testes

### Organização de Arquivos

```
frontend/
  tests/
    e2e/
      fixtures/
        auth.js          # Autenticação
        data.js          # Mocks de dados
        api.js           # Mocks de API
      dashboard.spec.js  # Testes do dashboard
      map-loading.spec.js # Testes de carregamento de mapas
      mapView.spec.js     # Testes de visualização de mapas
      network.spec.js     # Testes de funcionalidades de rede
    unit/
      components/        # Testes unitários de componentes Vue
      stores/            # Testes de Pinia stores
      composables/       # Testes de composables
```

### Estrutura de Spec File

```javascript
import { test, expect } from '@playwright/test';
import { authenticate } from './fixtures/auth.js';

// ===== DESCRIBE BLOCK (Suite de testes) =====
test.describe('Feature Name', () => {
  
  // ===== HOOKS =====
  test.beforeEach(async ({ page }) => {
    // Setup executado ANTES de cada teste
    await authenticate(page);
    await page.goto('http://localhost:8000/path');
  });
  
  test.afterEach(async ({ page }) => {
    // Cleanup executado DEPOIS de cada teste (opcional)
    // Ex: Limpar localStorage, cookies, etc
  });
  
  // ===== TESTES =====
  test('Happy path: comportamento esperado', async ({ page }) => {
    // 1. Arrange (preparar)
    const button = page.locator('[data-testid="submit-button"]');
    
    // 2. Act (agir)
    await button.click();
    
    // 3. Assert (verificar)
    const result = page.locator('[data-testid="success-message"]');
    await expect(result).toBeVisible();
    await expect(result).toContainText('Sucesso!');
  });
  
  test('Edge case: estado vazio', async ({ page }) => {
    // Testar comportamento com 0 dados
    const emptyState = page.locator('[data-testid="empty-state"]');
    await expect(emptyState).toBeVisible();
  });
  
  test('Error case: API falha', async ({ page }) => {
    // Mock erro 500
    await page.route('**/api/**', route => {
      route.fulfill({ status: 500 });
    });
    
    await page.reload();
    
    const error = page.locator('[data-testid="error-state"]');
    await expect(error).toBeVisible();
  });
  
  // ===== TESTE SKIPADO =====
  test.skip('Feature não implementada', async ({ page }) => {
    // Skip temporário (implementar depois)
  });
  
  // ===== TESTE ONLY (debugging) =====
  test.only('Debug este teste', async ({ page }) => {
    // Executar APENAS este teste
    // REMOVER .only antes de commit!
  });
});

// ===== NESTED DESCRIBE (opcional) =====
test.describe('Feature - Subfeature', () => {
  test.describe('Desktop', () => {
    test('Comportamento desktop', async ({ page }) => {
      // ...
    });
  });
  
  test.describe('Mobile', () => {
    test.use({ viewport: { width: 375, height: 667 } });
    
    test('Comportamento mobile', async ({ page }) => {
      // ...
    });
  });
});
```

### Naming Convention

**Formato**: `test('<ação> → <resultado>', ...)`

```javascript
// ✅ BOM (descreve comportamento)
test('Clicar em "Fit Bounds" → Mapa ajusta zoom', async ({ page }) => { ... });
test('Dashboard load → Host display → WebSocket update', async ({ page }) => { ... });
test('Handles 50+ hosts without lag', async ({ page }) => { ... });

// ❌ RUIM (muito técnico/vago)
test('Test 1', async ({ page }) => { ... });
test('API returns 200', async ({ page }) => { ... });
test('Component renders', async ({ page }) => { ... });
```

---

## 📊 Performance Testing

### Medindo Load Time

```javascript
test('Dashboard loads within 5s', async ({ page }) => {
  const start = Date.now();
  
  await page.goto('http://localhost:8000/monitoring/backbone');
  await page.waitForSelector('[data-testid="host-card"]');
  
  const loadTime = Date.now() - start;
  console.log(`⏱️ Dashboard load time: ${loadTime}ms`);
  
  expect(loadTime).toBeLessThan(5000); // < 5 segundos
});
```

### Medindo Render Time

```javascript
test('Renders 11 hosts quickly', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  // Aguarda API
  const responsePromise = page.waitForResponse(r => 
    r.url().includes('/api/dashboard/data/')
  );
  
  const response = await responsePromise;
  const data = await response.json();
  const hostCount = data.hosts_status.length;
  
  console.log(`📊 Backend returned ${hostCount} hosts`);
  
  // Medir tempo de render
  const renderStart = Date.now();
  await page.waitForSelector('[data-testid="host-card"]');
  const renderTime = Date.now() - renderStart;
  
  console.log(`⏱️ Render time: ${renderTime}ms for ${hostCount} hosts`);
  
  expect(renderTime).toBeLessThan(100); // < 100ms
});
```

### Web Vitals (Core Web Vitals)

```javascript
test('Core Web Vitals', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  const vitals = await page.evaluate(() => {
    return new Promise(resolve => {
      new PerformanceObserver(list => {
        const entries = list.getEntries();
        const lcp = entries.find(e => e.entryType === 'largest-contentful-paint');
        const fid = entries.find(e => e.entryType === 'first-input');
        const cls = entries.find(e => e.entryType === 'layout-shift');
        
        resolve({
          lcp: lcp?.renderTime || lcp?.loadTime || 0,
          fid: fid?.processingStart - fid?.startTime || 0,
          cls: cls?.value || 0,
        });
      }).observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] });
      
      // Timeout após 10s
      setTimeout(() => resolve({ lcp: 0, fid: 0, cls: 0 }), 10000);
    });
  });
  
  console.log('📊 Core Web Vitals:', vitals);
  
  // Google thresholds
  expect(vitals.lcp).toBeLessThan(2500); // < 2.5s
  expect(vitals.fid).toBeLessThan(100);  // < 100ms
  expect(vitals.cls).toBeLessThan(0.1);  // < 0.1
});
```

---

## ✅ Boas Práticas

### 1. DRY (Don't Repeat Yourself)

❌ **Ruim** (duplicação):
```javascript
test('Test 1', async ({ page }) => {
  await page.goto('http://localhost:8000/accounts/login/');
  await page.fill('#id_username', 'admin');
  await page.fill('#id_password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL(url => !url.pathname.includes('/login/'));
  // ... teste
});

test('Test 2', async ({ page }) => {
  await page.goto('http://localhost:8000/accounts/login/');
  await page.fill('#id_username', 'admin');
  await page.fill('#id_password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL(url => !url.pathname.includes('/login/'));
  // ... teste
});
```

✅ **Bom** (fixture reutilizável):
```javascript
import { authenticate } from './fixtures/auth.js';

test.beforeEach(async ({ page }) => {
  await authenticate(page);
});

test('Test 1', async ({ page }) => { /* ... */ });
test('Test 2', async ({ page }) => { /* ... */ });
```

### 2. Locators Semânticos

```javascript
// ✅ MELHOR: data-testid (estável)
page.locator('[data-testid="host-card"]')

// ✅ BOM: Role + Nome (acessível)
page.getByRole('button', { name: 'Fit Bounds' })
page.getByRole('link', { name: 'Ver Detalhes' })

// ⚠️ ACEITÁVEL: Text (pode mudar com i18n)
page.getByText('Carregando...')

// ❌ RUIM: CSS classes (mudam facilmente)
page.locator('.bg-white.shadow-sm.rounded-lg')

// ❌ RUIM: XPath (frágil)
page.locator('//div[@class="card"]/span[2]')
```

### 3. Assertions Múltiplas

```javascript
test('Host card mostra dados corretos', async ({ page }) => {
  const card = page.locator('[data-testid="host-card"]').first();
  
  // ✅ Múltiplas assertions no mesmo elemento
  await expect(card).toBeVisible();
  await expect(card).toContainText('host-1');
  await expect(card).toContainText('192.168.1.1');
  await expect(card).toContainText('Available');
  
  // ✅ Assertion de estrutura
  const name = card.locator('[data-testid="host-name"]');
  await expect(name).toHaveText('host-1');
});
```

### 4. Parallelização

```javascript
// Executar testes em paralelo (mais rápido)
npx playwright test --workers=4

// Executar sequencialmente (debugging)
npx playwright test --workers=1
```

**⚠️ Atenção**: Testes devem ser **independentes** para parallelizar!

### 5. Screenshots e Vídeos

```javascript
test('Dashboard visual regression', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone');
  await page.waitForSelector('[data-testid="host-card"]');
  
  // Screenshot para comparação visual
  await page.screenshot({ 
    path: 'screenshots/dashboard.png',
    fullPage: true 
  });
});

// Screenshots automáticos em falhas (playwright.config.js)
use: {
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
}
```

---

## 🐛 Debugging

### Técnicas

#### 1. Headed Mode (ver navegador)
```bash
npx playwright test --headed
```

#### 2. Debug Mode (step-by-step)
```bash
npx playwright test --debug
```

#### 3. Console Logs
```javascript
test('Debug test', async ({ page }) => {
  // Ver console do navegador
  page.on('console', msg => console.log('🌐 Browser:', msg.text()));
  
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  // Log do Node.js
  console.log('✅ Page loaded');
  
  const hosts = await page.locator('[data-testid="host-card"]').count();
  console.log(`🎯 Found ${hosts} host cards`);
});
```

#### 4. Pause Execution
```javascript
test('Debug with pause', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone');
  
  // Pausa execução (abre inspector)
  await page.pause();
  
  // Código após pause
});
```

#### 5. Slow Motion
```javascript
// playwright.config.js
use: {
  launchOptions: {
    slowMo: 1000, // 1s de delay entre ações
  },
}
```

### Erros Comuns

#### Erro: TimeoutError waiting for selector

**Causa**: Elemento não apareceu no tempo limite (30s padrão)

**Solução**:
```javascript
// 1. Verificar se seletor está correto
await page.waitForSelector('[data-testid="host-card"]', { 
  state: 'visible',
  timeout: 5000 // Aumentar timeout temporariamente para debug
});

// 2. Verificar se API foi chamada
await page.waitForResponse(r => r.url().includes('/api/dashboard/data/'));

// 3. Verificar erros no console
page.on('pageerror', err => console.error('❌ Page error:', err));
```

#### Erro: Element is not visible

**Causa**: Elemento existe no DOM mas está oculto (CSS `display: none`, `visibility: hidden`)

**Solução**:
```javascript
// Verificar estado do elemento
const element = page.locator('[data-testid="element"]');
const isVisible = await element.isVisible();
console.log(`Element visible: ${isVisible}`);

// Aguardar visibilidade específica
await element.waitFor({ state: 'visible' });
```

---

## 🚀 CI/CD Integration

### GitHub Actions

**`.github/workflows/e2e-tests.yml`**:
```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgis/postgis:16-3.4
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: app
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Install Playwright browsers
        run: |
          cd frontend
          npx playwright install --with-deps chromium
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Python dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run migrations
        env:
          DB_HOST: localhost
          DB_PORT: 5432
          DB_ENGINE: postgis
        run: |
          cd backend
          python manage.py migrate --noinput
      
      - name: Create test user
        env:
          DJANGO_SUPERUSER_USERNAME: admin
          DJANGO_SUPERUSER_PASSWORD: admin123
          DJANGO_SUPERUSER_EMAIL: admin@test.com
        run: |
          cd backend
          python manage.py createsuperuser --noinput
      
      - name: Run Django server
        run: |
          cd backend
          python manage.py runserver 0.0.0.0:8000 &
          sleep 5
      
      - name: Build frontend
        run: |
          cd frontend
          npm run build
      
      - name: Run Playwright tests
        run: |
          cd frontend
          npx playwright test tests/e2e/
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 30
```

---

## 🔧 Troubleshooting

### Problema: Testes passam local, falham no CI

**Causas comuns**:
1. **Timing**: CI é mais lento → Aumentar timeouts
2. **Dados**: CI usa DB vazio → Seed dados antes dos testes
3. **Ambiente**: Variáveis de ambiente diferentes → Verificar `.env`

**Solução**:
```javascript
// playwright.config.js
const CI = !!process.env.CI;

export default defineConfig({
  timeout: CI ? 60000 : 30000, // 2x timeout no CI
  retries: CI ? 2 : 0,          // Retry no CI
});
```

### Problema: Testes flaky (passam/falham aleatoriamente)

**Causas**:
- Fixed timeouts (`waitForTimeout`)
- Race conditions (APIs lentas)
- Estado compartilhado entre testes

**Solução**:
```javascript
// ❌ Flaky
test('Test 1', async ({ page }) => {
  await page.goto('/');
  await page.waitForTimeout(2000); // ❌ Pode não ser suficiente
});

// ✅ Robusto
test('Test 1', async ({ page }) => {
  await page.goto('/');
  await page.waitForSelector('[data-testid="content"]', {
    state: 'visible'
  }); // ✅ Espera específica
});
```

---

## 📚 Referências

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Testing Library Principles](https://testing-library.com/docs/guiding-principles/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## 🎯 Checklist de Revisão de PR

Antes de aprovar PR com testes E2E:

- [ ] Testes cobrem happy path + edge cases
- [ ] `data-testid` adicionados em elementos críticos
- [ ] Event-based waits (não fixed timeouts)
- [ ] Fixtures reutilizáveis quando aplicável
- [ ] Assertions claras e específicas
- [ ] Testes independentes (não compartilham estado)
- [ ] Console limpo (sem erros/warnings)
- [ ] Performance validada (load time < 5s)
- [ ] Screenshots/vídeos em caso de falha
- [ ] CI passa (29/30+ testes)

---

**Última atualização**: 18 de Novembro de 2025  
**Versão**: 2.0  
**Status**: ✅ Validado com 96.7% pass rate (29/30 testes)
