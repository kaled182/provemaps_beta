# Exemplos de API - ProVeMaps

**Versão do produto**: ver [VERSION](../../VERSION)
**Última atualização**: 2026-11-23 (EV-0033)

Exemplos que funcionam contra este código. Autenticação explicada em
[AUTHENTICATION.md](AUTHENTICATION.md). A lista de rotas e os campos exatos
estão no Swagger (`/api/schema/swagger/`, autenticado) e em
[ENDPOINTS.md](ENDPOINTS.md). Os exemplos só mostram a **forma** das respostas;
os valores dependem dos seus dados.

Variáveis usadas:

```bash
export BASE=https://SEU_HOST          # ou http://localhost:8100 no compose de dev
export PROVEMAPS_TOKEN='...'          # token de conta de serviço (mostrado uma vez no admin)
```

---

## 1. Integrações: Bearer

### Listar sites

```bash
curl -s -H "Authorization: Bearer $PROVEMAPS_TOKEN" "$BASE/api/v1/sites/"
```

Resposta paginada (`PageNumberPagination`, 100 por página): `count`, `next`,
`previous`, `results`. Página seguinte: `?page=2`. O tamanho da página não é
configurável pelo cliente.

### Detalhe e filtros que existem

```bash
curl -s -H "Authorization: Bearer $PROVEMAPS_TOKEN" "$BASE/api/v1/sites/1/"
curl -s -H "Authorization: Bearer $PROVEMAPS_TOKEN" "$BASE/api/v1/devices/?site=1"
curl -s -H "Authorization: Bearer $PROVEMAPS_TOKEN" "$BASE/api/v1/fiber-cables/"
```

`?site=` em `devices` é o único filtro que verifiquei no viewset; não há
`SearchFilter`/`DjangoFilterBackend` global.

### Python

```python
import os
import requests

BASE = os.environ["BASE"]
session = requests.Session()
session.headers["Authorization"] = f"Bearer {os.environ['PROVEMAPS_TOKEN']}"

url = f"{BASE}/api/v1/sites/"
sites = []
while url:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    page = resp.json()
    sites.extend(page["results"])
    url = page["next"]
```

### Esquema OpenAPI

```bash
curl -s -H "Authorization: Bearer $PROVEMAPS_TOKEN" "$BASE/api/schema/" -o openapi.yaml
```

### Erros de autenticação

```bash
# Sem cabeçalho -> 401, WWW-Authenticate: Bearer
curl -i "$BASE/api/v1/sites/"
# Token inválido/revogado/expirado -> 401
curl -i -H "Authorization: Bearer invalido" "$BASE/api/v1/sites/"
# Formato Token <x> não é Bearer -> tratado como sem credenciais (401)
curl -i -H "Authorization: Token $PROVEMAPS_TOKEN" "$BASE/api/v1/sites/"
```

Escrita (`POST`/`PUT`/`PATCH`/`DELETE`) com Bearer não precisa de CSRF. Os
viewsets de inventário aceitam qualquer principal autenticado, por isso um token
pode alterar dados: use com cuidado.

```bash
curl -s -X PATCH "$BASE/api/v1/sites/1/" \
  -H "Authorization: Bearer $PROVEMAPS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"city": "Belém"}'
```

Alterações a cabos/portas/rotas pela API não passam pelos usecases que
invalidam as caches do mapa (CLAUDE.md §2.4); prefira as rotas de usecase quando existirem.

---

## 2. Pessoas: sessão + CSRF (cliente de linha de comandos)

Útil para testes. O login é de formulário e, com TOTP ativo, tem um segundo
passo. Cookie CSRF: `mapsprovefiber_csrftoken`.

```bash
JAR=$(mktemp)

# 1) obter o cookie CSRF
curl -s -c "$JAR" "$BASE/accounts/login/" -o /dev/null
CSRF=$(awk '$6=="mapsprovefiber_csrftoken"{print $7}' "$JAR")

# 2) senha
curl -s -b "$JAR" -c "$JAR" -X POST "$BASE/accounts/login/" \
  -H "Referer: $BASE/accounts/login/" \
  --data-urlencode "csrfmiddlewaretoken=$CSRF" \
  --data-urlencode "username=USUARIO" \
  --data-urlencode "password=SENHA" -o /dev/null -D -
# Sem TOTP: já autenticado. Com TOTP: 302 para /accounts/otp/

# 3) só com TOTP ativo
CSRF=$(awk '$6=="mapsprovefiber_csrftoken"{print $7}' "$JAR")
curl -s -b "$JAR" -c "$JAR" -X POST "$BASE/accounts/otp/" \
  -H "Referer: $BASE/accounts/otp/" \
  --data-urlencode "csrfmiddlewaretoken=$CSRF" \
  --data-urlencode "otp=123456" -o /dev/null -D -
```

(O cookie CSRF pode rodar após o login; reler antes de cada mutação.)

```bash
# GET: só o cookie de sessão
curl -s -b "$JAR" "$BASE/api/v1/sites/"

# Mutação: X-CSRFToken obrigatório (sem ele -> 403)
CSRF=$(awk '$6=="mapsprovefiber_csrftoken"{print $7}' "$JAR")
curl -s -b "$JAR" -X PATCH "$BASE/api/v1/sites/1/" \
  -H "X-CSRFToken: $CSRF" \
  -H "Referer: $BASE/" \
  -H "Content-Type: application/json" \
  -d '{"city": "Belém"}'
```

Em HTTPS o Django valida o `Referer`/`Origin`; o `Referer` acima é necessário.

### Navegador (`fetch`)

Dentro do SPA, use `useApi()` (`frontend/src/composables/useApi.js`). Em código
avulso na mesma origem:

```js
const csrf = window.CSRF_TOKEN; // definido em base_spa.html

const res = await fetch('/api/v1/sites/1/', {
  method: 'PATCH',
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
  body: JSON.stringify({ city: 'Belém' }),
});
if (!res.ok) throw new Error(`HTTP ${res.status}`);
```

Erros DRF vêm como `{"detail": "..."}` (ou campo -> lista de mensagens em
validação, 400). Chamadas a `/api/*` legadas sem sessão: `401`
`{"detail": "Authentication required."}`.

---

## 3. Saúde (sem autenticação)

```bash
curl -s "$BASE/healthz"   # sem barra final
curl -s "$BASE/ready"
curl -s "$BASE/live"
```

Estão na whitelist do middleware (`/healthz`, `/ready`, `/live`). Use **sem**
barra final: `/healthz/` não está na whitelist e redireciona para o login
(EV-0032).

---

## O que estes exemplos não cobrem

Exemplos de rotas específicas (importar KML, monitoramento, Zabbix, rotas em
lote) foram removidos: os que existiam documentavam o prefixo
`/api/v1/inventory/sites/` e autenticação por `Token`, que não correspondem ao
código. Consulte o Swagger para o contrato real de cada rota.
