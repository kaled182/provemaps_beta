# 🗺️ Google Maps API - Guia de Configuração

**Data:** 27 de Outubro de 2025  
**Componente:** `routes_builder/fiber-route-builder/`  
**Prioridade:** 🔴 **CRÍTICA** - Sem esta configuração, o mapa não carrega

---

## 📋 Sumário Executivo

O **Fiber Route Builder** requer uma chave válida da **Google Maps JavaScript API** para funcionar. Sem ela, você verá:

```
❌ Console Error: "Google Maps API not loaded"
❌ Mapa vazio (elemento <div id="builderMap"> sem conteúdo)
❌ TypeError: Cannot read properties of undefined (reading 'maps')
```

**Status atual:** ⚠️ `GOOGLE_MAPS_API_KEY` não configurada → Mapa não funciona

---

## 🔑 Como Obter uma Chave de API

### Passo 1: Acesse o Google Cloud Console

1. Vá para: https://console.cloud.google.com/
2. Faça login com sua conta Google (crie uma se necessário)

### Passo 2: Crie um Projeto (ou use existente)

```
1. Clique em "Select a project" (topo da página)
2. Clique em "NEW PROJECT"
3. Nome sugerido: "MapsProveFiber"
4. Clique em "CREATE"
5. Aguarde alguns segundos até o projeto ser criado
```

### Passo 3: Habilite a Google Maps JavaScript API

```
1. No menu lateral, vá em: "APIs & Services" → "Library"
2. Pesquise por: "Maps JavaScript API"
3. Clique no resultado "Maps JavaScript API"
4. Clique em "ENABLE"
5. Aguarde ativação (~10-30 segundos)
```

### Passo 4: Crie Credenciais (API Key)

```
1. No menu lateral: "APIs & Services" → "Credentials"
2. Clique em "+ CREATE CREDENTIALS" (topo)
3. Selecione: "API key"
4. Uma chave será gerada (formato: AIzaSyC-dQd3sOmeExampleKey123456789)
5. Clique em "CLOSE" ou copie a chave imediatamente
```

### Passo 5: Restrinja a Chave (Recomendado para Produção)

**⚠️ IMPORTANTE:** Sem restrições, qualquer pessoa com sua chave pode usá-la e gerar custos.

#### Restrições de Aplicação (Application restrictions):

**Para Desenvolvimento:**
```
- HTTP referrers (web sites)
- Adicione: http://localhost:8000/*
- Adicione: http://127.0.0.1:8000/*
```

**Para Produção:**
```
- HTTP referrers (web sites)
- Adicione: https://seudominio.com/*
- Adicione: https://*.seudominio.com/*
```

#### Restrições de API (API restrictions):

```
1. Selecione: "Restrict key"
2. Marque apenas: "Maps JavaScript API"
3. Clique em "SAVE"
```

---

## ⚙️ Configuração no Projeto

### Opção 1: Arquivo `.env` (Recomendado)

**Arquivo:** `d:\Gemini\Provemaps_GPT-Tier2\mapsprovefiber\.env.local`

```bash
# Adicione esta linha (substitua pela sua chave):
GOOGLE_MAPS_API_KEY=AIzaSyC-dQd3sOmeExampleKey123456789

# Exemplo completo:
SECRET_KEY=dev-local-secret-key-not-for-production-xyz789
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
DATABASE_URL=
GOOGLE_MAPS_API_KEY=AIzaSyC-dQd3sOmeExampleKey123456789  # ← ADICIONE AQUI
```

### Opção 2: Docker Compose (Produção)

**Arquivo:** `docker-compose.yml`

```yaml
services:
  web:
    environment:
      - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
```

E crie/edite `.env` na raiz do projeto:

```bash
GOOGLE_MAPS_API_KEY=AIzaSyC-dQd3sOmeExampleKey123456789
```

### Opção 3: setup_app (Configuração Dinâmica)

Use a interface administrativa:

```
1. Acesse: http://localhost:8000/setup/
2. Faça login como admin
3. Vá em "Google Maps API Key"
4. Cole sua chave
5. Clique em "Salvar"
```

---

## ✅ Validação da Configuração

### 1. Verificar se a Variável Está Definida

```bash
# PowerShell (Windows):
docker exec mapsprovefiber-web-1 python -c "from django.conf import settings; import django; django.setup(); print('GOOGLE_MAPS_API_KEY:', settings.GOOGLE_MAPS_API_KEY or 'NOT SET')"

# Bash (Linux/macOS):
docker exec mapsprovefiber-web-1 bash -c 'python -c "from django.conf import settings; import django; django.setup(); print(\"GOOGLE_MAPS_API_KEY:\", settings.GOOGLE_MAPS_API_KEY or \"NOT SET\")"'
```

**Resultado esperado:**
```
GOOGLE_MAPS_API_KEY: AIzaSyC-dQd3sOmeExampleKey123456789
```

**Se aparecer `NOT SET`:** A variável não foi carregada corretamente.

### 2. Verificar no Navegador

1. Acesse: http://localhost:8000/routes/builder/fiber-route-builder/
2. Abra o Console do navegador (F12)
3. Verifique se há erros relacionados ao Google Maps

**✅ Sucesso (deve aparecer):**
```javascript
// Nenhum erro relacionado a google.maps
// Mapa carrega com tiles visíveis
```

**❌ Erro (se configuração incorreta):**
```javascript
TypeError: Cannot read properties of undefined (reading 'maps')
    at initMap (mapCore.js:20)
```

### 3. Inspecionar HTML Renderizado

```bash
# Verificar se a chave está sendo injetada no template:
curl -s http://localhost:8000/routes/builder/fiber-route-builder/ | grep "maps.googleapis.com"
```

**Resultado esperado:**
```html
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyC-dQd3sOmeExampleKey123456789" async defer></script>
```

**Se aparecer `key=`** (vazio): A chave não está sendo passada para o template.

---

## 🐞 Troubleshooting

### Problema 1: "Google Maps API not loaded"

**Sintomas:**
- Console mostra: `TypeError: google is not defined`
- Mapa permanece em branco

**Causas possíveis:**
1. ❌ Chave não configurada no `.env`
2. ❌ Container não reiniciado após mudança no `.env`
3. ❌ API não habilitada no Google Cloud Console
4. ❌ Restrições de HTTP referrer bloqueando localhost

**Solução:**
```bash
# 1. Confirme que a chave está no .env.local
cat .env.local | grep GOOGLE_MAPS_API_KEY

# 2. Reinicie o container web:
docker compose restart web

# 3. Aguarde 10s e teste novamente
docker logs mapsprovefiber-web-1 --tail 5
```

---

### Problema 2: "This page can't load Google Maps correctly"

**Sintomas:**
- Mapa carrega mas mostra mensagem de erro
- Console mostra: `Google Maps JavaScript API error: InvalidKeyMapError`

**Causas possíveis:**
1. ❌ Chave inválida ou revogada
2. ❌ API não habilitada no projeto
3. ❌ Billing não configurado (necessário após período trial)

**Solução:**
```
1. Vá para: https://console.cloud.google.com/google/maps-apis/credentials
2. Copie a chave novamente (pode ter sido regenerada)
3. Verifique se "Maps JavaScript API" está habilitada
4. Configure billing se necessário (Google dá $200/mês de crédito grátis)
```

---

### Problema 3: Restrições Bloqueando Acesso

**Sintomas:**
- Console mostra: `Google Maps JavaScript API error: RefererNotAllowedMapError`

**Solução:**
```
1. Vá em: APIs & Services → Credentials
2. Clique na sua API key
3. Em "Application restrictions", escolha: "HTTP referrers"
4. Adicione:
   - http://localhost:8000/*
   - http://127.0.0.1:8000/*
5. Clique em "SAVE"
6. Aguarde 5 minutos para propagação
```

---

### Problema 4: Container Não Carrega Variável

**Sintomas:**
- `docker exec ... print(settings.GOOGLE_MAPS_API_KEY)` retorna `NOT SET`
- Mas o arquivo `.env.local` contém a chave

**Causas:**
1. ❌ Docker Compose não está usando o `.env.local`
2. ❌ Variável comentada no arquivo

**Solução:**

**Verifique docker-compose.yml:**
```yaml
services:
  web:
    env_file:
      - .env.local  # ← Deve estar presente
```

**Ou adicione manualmente:**
```yaml
services:
  web:
    environment:
      - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
```

**Depois reinicie:**
```bash
docker compose down
docker compose up -d
```

---

## 💰 Custos e Limites

### Plano Gratuito (Free Tier)

Google oferece **$200 USD/mês de crédito grátis** para todos os serviços de Maps.

**Maps JavaScript API:**
- **Carga de mapa dinâmico:** $7.00 por 1.000 carregamentos
- **Crédito gratuito:** ~28.571 carregamentos/mês
- **Uso típico MapsProveFiber:** ~100-500 carregamentos/mês (muito abaixo do limite)

**Conclusão:** Para uso interno/desenvolvimento, você **não pagará nada**.

### Configurar Alertas de Billing (Recomendado)

```
1. Vá em: Billing → Budgets & alerts
2. Crie um alerta para $10 USD
3. Receba email se atingir 50% do orçamento
```

---

## 🔐 Segurança - Boas Práticas

### ✅ DO (Faça)
- ✅ Use restrições de HTTP referrer em produção
- ✅ Restrinja a chave apenas para APIs necessárias
- ✅ Armazene chaves em `.env` (nunca em código)
- ✅ Use chaves diferentes para dev/staging/prod
- ✅ Configure alertas de uso no Google Cloud Console

### ❌ DON'T (Não Faça)
- ❌ Nunca commite chaves no Git (`.env` deve estar no `.gitignore`)
- ❌ Não use a mesma chave em múltiplos ambientes
- ❌ Não deixe chaves sem restrições em produção
- ❌ Não compartilhe chaves via Slack/Email/WhatsApp

---

## 📚 Referências Oficiais

- **Maps JavaScript API Docs:** https://developers.google.com/maps/documentation/javascript
- **API Key Best Practices:** https://developers.google.com/maps/api-security-best-practices
- **Pricing Calculator:** https://mapsplatform.google.com/pricing/
- **Troubleshooting Errors:** https://developers.google.com/maps/documentation/javascript/error-messages

---

## 🎯 Checklist Rápido

- [ ] **Passo 1:** Criar projeto no Google Cloud Console
- [ ] **Passo 2:** Habilitar "Maps JavaScript API"
- [ ] **Passo 3:** Criar credencial (API Key)
- [ ] **Passo 4:** Configurar restrições (HTTP referrers)
- [ ] **Passo 5:** Adicionar `GOOGLE_MAPS_API_KEY` no `.env.local`
- [ ] **Passo 6:** Reiniciar container: `docker compose restart web`
- [ ] **Passo 7:** Validar no navegador: http://localhost:8000/routes/builder/fiber-route-builder/
- [ ] **Passo 8:** Verificar Console do navegador (F12) - sem erros
- [ ] **Passo 9:** Confirmar que mapa carrega com tiles do Google Maps

---

## ✅ Status Esperado Após Configuração

**Console do Navegador (F12):**
```
✅ Nenhum erro relacionado a google.maps
✅ Mapa renderizado com tiles do Google Maps
✅ Polylines e markers funcionando
✅ Click events capturados
```

**Visual:**
```
✅ Mapa interativo visível
✅ Botões "Route Points" e "Help" flutuantes
✅ Click no mapa adiciona pontos
✅ Menu de contexto funcional (botão direito)
```

**Logs do Container:**
```bash
docker logs mapsprovefiber-web-1 --tail 10

# Não deve mostrar erros de GOOGLE_MAPS_API_KEY
```

---

*Documento criado automaticamente*  
*Para dúvidas, consulte: https://developers.google.com/maps/documentation*
