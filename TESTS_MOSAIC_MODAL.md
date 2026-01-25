# 🧪 Testes Implementados: Modal de Mosaico de Câmeras

## ✅ Teste 1: Validação de Pattern Vue 3 Refs
**Arquivo**: `test_mosaic_refs.py`
**Status**: PASS ✓

Valida que o código segue o padrão correto:
- **Template**: `mosaicVideoRefs[key] = el` (sem .value)
- **Código**: `mosaicVideoRefs.value[key]` (com .value)

```bash
python test_mosaic_refs.py
# Resultado: === RESULTADO: PASS ===
```

---

## ✅ Teste 2: Garantia de Renderização Completa
**Implementação**: SiteDetailsModal.vue (linhas após mosaicCameras.value)

### Estratégia Multi-Camada:
1. **Duplo `nextTick()`**: Garante que v-for dinâmico terminou
2. **Retry com Polling**: Valida que refs foram populadas
3. **Logs Diagnósticos**: Rastreia cada etapa

```js
await nextTick()
await nextTick() // Segundo tick para v-for completo

// Retry até todas as refs estarem prontas
for (let i = 0; i < 5; i++) {
  const refCount = Object.keys(mosaicVideoRefs.value).length
  if (refCount >= mosaicCameras.value.length) break
  await delay(100)
}
```

### Validação Pre-Flight
Antes de cada conexão, valida que o elemento `<video>` existe:

```js
const videoEl = mosaicVideoRefs.value[key]
if (!videoEl) {
  console.error('ERRO: Elemento não encontrado')
  return // Aborta conexão
}
```

---

## ✅ Teste 3: HTML de Teste Standalone
**Arquivo**: `test-mosaic-refs.html`

Teste isolado Vue 3 para validar comportamento de refs dinâmicas.

**Como usar**:
```bash
cd frontend
python -m http.server 8080
# Abrir http://localhost:8080/test-mosaic-refs.html
# Verificar console do navegador
```

---

## 📊 Logs Esperados no Console

### ✅ Sucesso:
```
[SiteDetailsModal] Câmeras enriquecidas: 4
[SiteDetailsModal] Vue renderizou, elementos video disponíveis
[SiteDetailsModal] mosaicVideoRefs.value keys: ['mosaic-1-0', 'mosaic-1-1', 'mosaic-1-2', 'mosaic-1-3']
[SiteDetailsModal] mosaicCameras connectionKeys: ['mosaic-1-0', 'mosaic-1-1', 'mosaic-1-2', 'mosaic-1-3']
[SiteDetailsModal] ✓ Todas as 4 refs prontas
[SiteDetailsModal] ✓ Elemento <video> encontrado para 12314
[SiteDetailsModal] ✓ Stream vinculado ao vídeo para mosaico:12314
```

### ❌ Falha (refs vazias):
```
[SiteDetailsModal] mosaicVideoRefs.value keys: []
[SiteDetailsModal] Aguardando refs... (0/4) tentativa 1/5
[SiteDetailsModal] ERRO: Elemento <video> não encontrado para 12314
```

---

## 🔄 Próximos Passos para Teste na Web

1. **Recarregar página**: Ctrl+R
2. **Abrir DevTools**: F12 → Console
3. **Abrir modal do site**: Clicar em "TESTE - Furacão"
4. **Abrir mosaico**: Clicar no card "Câmeras"
5. **Verificar logs**: Devem aparecer "✓ Todas as X refs prontas"
6. **Verificar vídeos**: Devem aparecer as imagens das câmeras

---

## 🐛 Se Ainda Falhar

Os logs vão mostrar exatamente onde está o problema:

1. **Se `mosaicVideoRefs.value keys: []`**: Vue não renderizou os elementos
   - Possível causa: Modal não está visível (`showMosaicModal = false`)
   - Solução: Verificar que modal está realmente aberto

2. **Se keys estão erradas**: Mismatch entre connectionKey no template e código
   - Logs mostram ambas as listas para comparação
   - Solução: Ajustar `assignConnectionKey`

3. **Se stream não vincula**: Elementos existem mas WebRTC falha
   - Ver logs do useWebRTC composable
   - Validar URLs WHEP retornadas pelo backend
