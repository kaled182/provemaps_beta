# API - ProVeMaps

Referência da API HTTP do ProVeMaps.

**Versão do produto**: ver [VERSION](../../VERSION)
**Última atualização**: 2026-11-23 (EV-0033: reescrito a partir do código)

---

## Documentos

| Documento | Conteúdo |
|-----------|----------|
| [AUTHENTICATION.md](AUTHENTICATION.md) | Sessão + CSRF (pessoas), Bearer de conta de serviço (integrações), o que não existe |
| [EXAMPLES.md](EXAMPLES.md) | Exemplos `curl`, Python e `fetch` que funcionam contra este código |
| [ENDPOINTS.md](ENDPOINTS.md) | Referência de rotas (confirmar caminhos no Swagger em caso de dúvida) |

A referência viva e autoritativa é o esquema OpenAPI 3, **só para autenticados**:

- `GET /api/schema/` - esquema (drf-spectacular)
- `GET /api/schema/swagger/` - Swagger UI auto-hospedado

Cobre as views DRF. As function views Django (`/api/v1/inventory/*`,
`/api/users/*`, `/setup_app/api/*`) ainda não aparecem nele (EV-0030).

---

## Início rápido

```bash
export BASE=https://SEU_HOST
export PROVEMAPS_TOKEN='...'   # token de conta de serviço (admin, mostrado uma vez)

curl -s -H "Authorization: Bearer $PROVEMAPS_TOKEN" "$BASE/api/v1/sites/"
```

Pessoas autenticam por sessão (login em dois passos, `/accounts/login/` e, com
TOTP, `/accounts/otp/`) e enviam `X-CSRFToken` nas mutações. Detalhes e exemplos
em [AUTHENTICATION.md](AUTHENTICATION.md) e [EXAMPLES.md](EXAMPLES.md).

---

## Autenticação em resumo

| Quem | Como | CSRF |
|------|------|------|
| Pessoa | Cookie `mapsprovefiber_sessionid` após login + TOTP | `X-CSRFToken` em POST/PUT/PATCH/DELETE |
| Integração | `Authorization: Bearer <token>` (ADR 0008) | Não |

- Tudo exige autenticação (`IsAuthenticated` por omissão).
- Sem credenciais: `/api/v1/` responde 401 com `WWW-Authenticate: Bearer`;
  outras `/api/*` respondem 401 `{"detail": "Authentication required."}`.
- Contas de serviço não são `User`: sem `is_staff` nem permissões de modelo.
- Não existem `Authorization: Token`, `/api/token/`, Basic Auth, JWT, CORS nem
  throttling.

---

## Versionamento

Só `v1`, lido do prefixo `/api/v1/` (`core/api_versioning.py`). Rotas legadas
sem prefixo contam como `v1`; outra versão devolve 404.

## Estrutura das rotas (confirmada em `backend/core/urls.py`)

| Prefixo | Conteúdo |
|---------|----------|
| `/api/v1/` | Router DRF do inventário (`inventory/urls_rest.py`): `sites`, `devices`, `device-groups`, `ports`, `fiber-cables`, `import-rules` |
| `/api/v1/inventory/` | Function views de inventário (`inventory/urls_api.py`): busca, sistema, pastas de cabos, tipos de cabo, etc. |
| `/api/v1/monitoring/` | Estado agregado Zabbix + inventário |
| `/api/v1/evolucao/` | Central de Evolução (ADR 0006) |
| `/api/v1/telemetry/` | Telemetria |
| `/api/v1/cameras/` | Lista de câmeras |
| `/api/users/`, `/api/groups/`, `/api/departments/`, `/api/config/` | Rotas legadas (sem prefixo de versão) |
| `/api/schema/`, `/api/schema/swagger/` | OpenAPI |
| `/healthz`, `/ready`, `/live` | Saúde, sem autenticação, **sem barra final** |

Atenção: o router DRF fica em `/api/v1/sites/`, **não** em
`/api/v1/inventory/sites/`.

## Paginação

`PageNumberPagination` com `PAGE_SIZE = 100` (`settings/base.py`). Parâmetro
`?page=N`; resposta com `count`, `next`, `previous`, `results`. O cliente não
escolhe o tamanho da página. `fiber-cables` também envia `ETag` e responde 304
a `If-None-Match`.

## Erros

DRF devolve `{"detail": "..."}` (401/403/404) e, em validação, 400 com campo ->
lista de mensagens. 403 em mutação com sessão e sem `X-CSRFToken` válido.

## Limites conhecidos

- Os viewsets de inventário só pedem `IsAuthenticated`: qualquer principal
  autenticado, inclusive um token de serviço, pode escrever.
- Sem rate limiting.
- Mutar cabos/portas/rotas fora dos usecases não invalida as caches do mapa
  (CLAUDE.md §2.4).

## Documentação relacionada

- [ADR 0008 - tokens Bearer de contas de serviço](../adr/0008-autenticacao-de-contas-de-servico-por-token-bearer.md)
- [Arquitetura](../architecture/)
- [Guia de desenvolvimento](../guides/DEVELOPMENT.md)
