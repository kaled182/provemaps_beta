# 🧪 Testes: Modal de Mosaico de Câmeras

**Última atualização**: 2026-10-04

> A página HTML solta `test-mosaic-refs.html` foi removida do repositório em 2026-10-04
> (EV-0020). Os testes reais são o **Vitest** (`frontend/tests/unit`,
> `frontend/tests/components`; `cd frontend && npm run test:unit`) e o **Playwright**
> (`frontend/tests/e2e`; `cd frontend && npm run test:e2e`). Ver [TESTS_E2E_SETUP.md](TESTS_E2E_SETUP.md).

## ✅ Teste 1: Validação de Pattern Vue 3 Refs
**Arquivo**: `backend/tests/test_mosaic_refs.py`

Valida que o código segue o padrão correto:
- **Template**: `mosaicVideoRefs[key] = el` (sem .value)
- **Código**: `mosaicVideoRefs.value[key]` (com .value)

```bash
python backend/tests/test_mosaic_refs.py
# Resultado esperado: === RESULTADO: PASS ===
```

> O script lê o componente por um caminho absoluto de Windows
> (`d:/provemaps_beta/frontend/src/components/SiteDetailsModal.vue`). Em Linux é preciso apontá-lo para
> `frontend/src/components/SiteDetailsModal.vue` antes de o executar.

---

## ✅ Teste 2: Garantia de Renderização Completa
**Implementação**: `frontend/src/components/SiteDetailsModal.vue` (`connectMosaicCamera` e `attemptWhepConnectionViaComposable`)

### Estratégia Multi-Camada:
1. **`nextTick()`** após a conexão WebRTC: garante que o `v-for` dinâmico terminou
2. **Polling**: até 10 tentativas (100 ms) à espera do `<video>` e do stream
3. **Validação pre-flight**: aborta a conexão se o elemento `<video>` não existe
4. **Logs diagnósticos**: rastreiam cada etapa

```js
await rtc.connect(whepUrl)
await nextTick()

const maxAttempts = 10
for (let i = 0; i < maxAttempts; i++) {
  const videoEl = refsMap.value[connectionKey]
  if (videoEl && rtc.stream.value) {
    videoEl.srcObject = rtc.stream.value
    break
  }
  await delay(100)
}
```

### Validação Pre-Flight
Antes de cada conexão, valida que o elemento `<video>` existe:

```js
const videoEl = mosaicVideoRefs.value[key]
if (!videoEl) {
  console.error('ERRO: Elemento <video> não encontrado')
  return // Aborta conexão
}
```

---

## ✅ Teste 3: Vitest do mosaico (substitui o HTML standalone)
**Arquivos**: `frontend/tests/unit/SiteCamerasTab.spec.js`, `frontend/tests/unit/useSiteCameras.spec.js`

Cobrem a aba de câmeras do site: estados de loading/erro/vazio, lista de mosaicos, carga de um mosaico,
uso de `CameraPlayer`, classe da grelha conforme o número de câmeras e `stopStreams` ao desmontar.

```bash
cd frontend
npx vitest run tests/unit/SiteCamerasTab.spec.js tests/unit/useSiteCameras.spec.js
# ou toda a suite: npm run test:unit
```

Ainda não existe um spec Playwright específico do mosaico em `frontend/tests/e2e`; um novo teste E2E
entra ali (ver "Adicionar novo teste" em [TESTS_E2E_SETUP.md](TESTS_E2E_SETUP.md)).

---

## 📊 Logs Esperados no Console

> Só aparecem em build de desenvolvimento: o build de produção remove `console.log` (EV-0019);
> `console.warn` e `console.error` ficam.

### ✅ Sucesso:
```
[SiteDetailsModal] 🎥 Conectando câmera: {name: ..., connectionKey: 'mosaic-1-0', ...}
[SiteDetailsModal] ✓ Elemento <video> encontrado para <câmera>, key: mosaic-1-0
[SiteDetailsModal] Tentativa 1/10 - videoEl: true stream: true
[SiteDetailsModal] ✓ Stream vinculado ao vídeo para mosaico:<câmera>
```

### ❌ Falha (refs vazias):
```
[SiteDetailsModal] ERRO: Elemento <video> não encontrado para <câmera>, key: mosaic-1-0
[SiteDetailsModal] Keys disponíveis: []
```

---

## 🔄 Próximos Passos para Teste na Web

1. **Recarregar página**: Ctrl+R
2. **Abrir DevTools**: F12 → Console
3. **Abrir modal do site**: Clicar em "TESTE - Furacão"
4. **Abrir mosaico**: Clicar no card "Câmeras"
5. **Verificar logs**: Devem aparecer "✓ Elemento <video> encontrado" e "✓ Stream vinculado ao vídeo"
6. **Verificar vídeos**: Devem aparecer as imagens das câmeras

---

## 🐛 Se Ainda Falhar

Os logs vão mostrar exatamente onde está o problema:

1. **Se `Keys disponíveis: []`**: Vue não renderizou os elementos
   - Possível causa: Modal não está visível (`showMosaicModal = false`)
   - Solução: Verificar que modal está realmente aberto

2. **Se as keys estão erradas**: Mismatch entre `connectionKey` no template e código
   - O log de erro mostra as keys disponíveis para comparação
   - Solução: Ajustar `assignConnectionKey`

3. **Se stream não vincula**: Elementos existem mas WebRTC falha
   - Ver logs do `useWebRTC` composable
   - Validar URLs WHEP retornadas pelo backend
