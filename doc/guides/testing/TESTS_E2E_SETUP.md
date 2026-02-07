# Testes E2E - Configuração e Execução

## 📦 Dependências Instaladas

### Backend (requirements.txt)
- `playwright==1.49.1` - Automação de browser para testes E2E
- `pytest-playwright==0.6.2` - Integração Playwright + pytest

### Dockerfile
- Bibliotecas do sistema para Chromium (libnss3, libnspr4, etc.)
- Chromium browser instalado via `playwright install chromium`

---

## 🧪 Testes Disponíveis

### 1. **Teste HTML Standalone** (Sem instalação)
**Arquivo:** [frontend/test-mosaic-dom.html](frontend/test-mosaic-dom.html)

**Como usar:**
```powershell
# Abrir diretamente no navegador
start frontend/test-mosaic-dom.html
```

**O que testa:**
- ✓ Conexão com backend Django
- ✓ Estrutura do modal renderizada
- ✓ Elementos `<video>` presentes no DOM
- ✓ Endpoints WHEP respondendo

**Vantagens:**
- Não requer instalação de dependências
- Execução instantânea
- Interface visual para diagnóstico

---

### 2. **Teste E2E Automatizado** (Playwright)
**Arquivo:** [test_mosaic_rendering.py](test_mosaic_rendering.py)

**Como executar localmente:**
```powershell
# 1. Instalar Playwright (só na primeira vez)
cd d:\provemaps_beta
pip install playwright pytest-playwright
playwright install chromium

# 2. Garantir que o servidor está rodando
cd docker
docker compose up -d web

# 3. Executar teste
cd ..
python test_mosaic_rendering.py
```

**Como executar no Docker:**
```powershell
cd docker

# Rebuild da imagem (só necessário após mudanças no Dockerfile)
docker compose build web

# Executar teste (profile 'testing')
docker compose --profile testing run --rm test-e2e

# Ou executar manualmente dentro do container web
docker compose exec web bash
cd /app
pytest test_mosaic_rendering.py -v
```

**O que testa:**
- ✓ Navegação para o mapa
- ✓ Clique no site "TESTE - Furacão"
- ✓ Abertura do modal de câmeras
- ✓ **Validação de elementos `<video>` no DOM**
- ✓ Captura de logs do console
- ✓ Screenshots automáticos (sucesso/falha)

**Saídas geradas:**
- `test-screenshot-success.png` - Screenshot quando teste passa
- `test-screenshot-fail.png` - Screenshot quando teste falha
- `test-screenshot-error.png` - Screenshot quando ocorre erro

---

## 🔍 Interpretação dos Resultados

### ✓ PASS - Elementos `<video>` encontrados
```
=== RESULTADOS ===
Total de <video> no DOM: 4
Vídeos de mosaico: 4

✓ PASS: Elementos <video> encontrados no DOM
```
**Significado:** Modal renderizou corretamente os elementos de vídeo. Problema pode estar em:
- Conexão WebRTC não estabelecida
- `srcObject` não atribuído
- Streams não disponíveis no MediaMTX

### ✗ FAIL - Nenhum elemento encontrado
```
✗ FAIL: Nenhum elemento <video> encontrado no DOM!

Possíveis causas:
  1. Modal de mosaico não está visível (v-if/v-show)
  2. Vue não renderizou os componentes
  3. mosaicCameras.value está vazio
```
**Significado:** Problema na renderização Vue. Verificar:
- `mosaicCameras` computed está retornando dados?
- `v-if` ou `v-show` está bloqueando renderização?
- Vue refs (`mosaicVideoRefs`) estão sendo criadas?

---

## 🐛 Debug Avançado

### Ver logs completos do container de teste
```powershell
docker compose --profile testing run --rm test-e2e
```

### Executar teste com browser visível (modo headed)
```powershell
# Editar docker-compose.yml:
# command: pytest /app/test_mosaic_rendering.py -v --headed

# Ou executar manualmente:
docker compose exec web bash
cd /app
PLAYWRIGHT_HEADED=1 pytest test_mosaic_rendering.py -v
```

### Inspecionar container durante execução
```powershell
# Terminal 1: Executar teste
docker compose --profile testing run --rm test-e2e

# Terminal 2: Inspecionar logs
docker compose logs -f web

# Terminal 3: Entrar no container
docker compose exec web bash
```

---

## 📋 Checklist de Troubleshooting

Se o teste falhar, verificar em ordem:

1. **Backend está rodando?**
   ```powershell
   docker compose ps
   curl http://localhost:8000/api/v1/sites/
   ```

2. **Câmeras cadastradas?**
   ```powershell
   curl http://localhost:8000/api/v1/cameras/
   ```

3. **Frontend compilado?**
   ```powershell
   ls backend/staticfiles/vue-spa/assets/
   ```

4. **Modal de mosaico existe no código?**
   ```powershell
   grep -r "mosaic-video" frontend/src/components/
   ```

5. **Vue refs sendo criadas?**
   - Abrir DevTools no navegador
   - Console → procurar logs `[SiteDetailsModal]`
   - Verificar "mosaicVideoRefs.value keys: [...]"

---

## 🚀 Comandos Rápidos

```powershell
# Rebuild completo após mudanças
cd docker
docker compose down
docker compose build --no-cache web test-e2e
docker compose up -d

# Executar apenas teste E2E
docker compose --profile testing run --rm test-e2e

# Ver screenshot de falha
start ..\test-screenshot-fail.png

# Limpar imagens antigas
docker compose down --rmi all
docker system prune -f
```

---

## 📊 Métricas de Sucesso

| Métrica | Valor Esperado |
|---------|---------------|
| Elementos `<video>` no DOM | ≥ 4 (número de câmeras) |
| Console logs `[SiteDetailsModal]` | ≥ 10 (mostra atividade) |
| Tempo de abertura do modal | < 2s |
| Conexões WebRTC estabelecidas | 100% das câmeras |
| Screenshots geradas | 1 (sucesso) ou 2 (falha + erro) |

---

## 🔧 Manutenção

### Atualizar Playwright
```powershell
pip install --upgrade playwright pytest-playwright
playwright install chromium
```

### Adicionar novo teste
1. Criar arquivo `test_*.py` na raiz
2. Adicionar volume no `docker-compose.yml`:
   ```yaml
   volumes:
     - ../test_novo.py:/app/test_novo.py
   ```
3. Executar: `docker compose --profile testing run --rm test-e2e pytest /app/test_novo.py`

---

## 📞 Suporte

Se os testes continuarem falhando após verificar o checklist:
1. Gerar screenshot: executar teste com `--screenshot=on`
2. Coletar logs: `docker compose logs web > logs.txt`
3. Verificar console do navegador (DevTools)
4. Comparar com implementação funcional em [MosaicViewerView.vue](frontend/src/views/video/MosaicViewerView.vue)
