# 🧪 VALIDAÇÃO MANUAL DE VÍDEOS NO MODAL

## ✅ Passos para Validação

### 1. Abrir Aplicação
- Navegue para: http://localhost:8000/monitoring/backbone/map/default
- Faça login se necessário

### 2. Abrir Modal de Mosaico
- Clique em qualquer site no mapa
- No modal do site, clique no card/botão de "Câmeras" ou "Mosaico"
- Aguarde o modal de mosaico abrir

### 3. Executar Script de Validação
1. Pressione `F12` para abrir DevTools
2. Vá para a aba **Console**
3. Cole o conteúdo do arquivo [frontend/validate-videos.js](frontend/validate-videos.js)
4. Pressione `Enter`
5. Aguarde 2 segundos para os resultados

## 📊 Resultados Esperados

### ✅ SUCESSO
```
✅ SUCESSO: Elementos <video> encontrados!
   Total de <video> no DOM: 4
   Vídeos com stream: 4/4
   Vídeos reproduzindo: 4/4
🎉 TUDO OK: Vídeos renderizados e reproduzindo!
```

### ⚠️ PARCIALMENTE FUNCIONANDO
```
✅ SUCESSO: Elementos <video> encontrados!
   Total de <video> no DOM: 4
   Vídeos com stream: 0/4  ← PROBLEMA AQUI
⚠️ ATENÇÃO: Elementos <video> existem mas nenhum tem srcObject!
```
**Causa:** WebRTC não está conectando

### ❌ FALHA
```
❌ FALHA: Nenhum elemento <video> encontrado!
```
**Causa:** Modal não renderizou os vídeos (problema no Vue)

## 🔍 Diagnóstico

### Se não encontrar vídeos:
1. Verifique se o modal de mosaico está realmente aberto
2. Verifique logs do console para erros Vue
3. Verifique se `mosaicCameras.value` tem dados:
   ```javascript
   // Cole no console:
   document.querySelector('#app').__vue_app__
   ```

### Se encontrar vídeos mas sem stream:
1. Verifique logs de WebRTC no console
2. Procure por erros: `[SiteDetailsModal]`, `[useWebRTC]`
3. Verifique conectividade com MediaMTX:
   ```javascript
   fetch('http://localhost:8082/camera-stream/STATUS').then(r => console.log(r))
   ```

### Se encontrar vídeos com stream mas não reproduzindo:
1. Problema com autoplay
2. Verifique permissões do navegador
3. Verifique se vídeos estão com `muted`

## 📸 Screenshot dos Resultados

Após executar o script, tire um screenshot do console mostrando:
- Número total de vídeos encontrados
- Status de cada vídeo (srcObject, reproduzindo, dimensões)
- Mensagem final de sucesso ou erro

## 🚀 Próximos Passos

### Se SUCESSO:
✅ Validação completa! Imagens estão sendo servidas corretamente.

### Se FALHA:
1. Compartilhe o screenshot do console
2. Compartilhe logs completos (inclusive erros)
3. Informe qual etapa falhou

---

**Arquivo do script:** [frontend/validate-videos.js](frontend/validate-videos.js)
