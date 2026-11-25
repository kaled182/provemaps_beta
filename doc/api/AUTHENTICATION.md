# Autenticação da API - ProVeMaps

**Versão do produto**: ver [VERSION](../../VERSION)
**Última atualização**: 2026-11-23 (EV-0033: reescrito a partir do código)
**Público**: integradores e desenvolvedores de cliente

> Este documento descreve só o que o código faz. O que não existe está
> listado na secção [O que não existe](#o-que-não-existe).

---

## Visão geral

Existem **dois** mecanismos de autenticação, ambos configurados em
`REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` (`backend/settings/base.py`):

| Quem | Mecanismo | CSRF | Principal |
|------|-----------|------|-----------|
| Pessoas (navegador/SPA) | Sessão Django + login em dois passos (senha, depois TOTP se ativo) | Exigido em POST/PUT/PATCH/DELETE | `User` do Django |
| Integrações (scripts, Zabbix, CRM) | `Authorization: Bearer <token>` de conta de serviço (ADR 0008) | Não se aplica | `ServiceAccountPrincipal` (não é `User`) |

A ordem das classes é: `ServiceAccountTokenAuthentication`, depois
`SessionAuthentication`. A permissão por omissão é `IsAuthenticated`: toda a
API exige autenticação. Um endpoint sem login é exceção escrita (CLAUDE.md §2.6).

Respostas sem credenciais:

- `/api/v1/...` (DRF): **401** com `WWW-Authenticate: Bearer` (a primeira classe
  de autenticação define o cabeçalho).
- Outros `/api/*` (rotas legadas, por exemplo `/api/users/`, `/api/config/`):
  **401** `{"detail": "Authentication required."}` do `AuthRequiredMiddleware`.
- Páginas fora de `/api/`: redirecionamento 302 para `/accounts/login/?next=...`.

---

## 1. Sessão (pessoas)

### Login em dois passos

1. `GET /accounts/login/` devolve a página e o cookie CSRF.
2. `POST /accounts/login/` (formulário, `application/x-www-form-urlencoded`)
   com `username`, `password` e `csrfmiddlewaretoken`.
   - Utilizador **sem** TOTP ativo: a sessão fica autenticada e há redirecionamento
     para o destino (`next` ou `LOGIN_REDIRECT_URL`).
   - Utilizador **com** TOTP ativo (`profile.totp_enabled`): a sessão guarda
     apenas `pending_2fa_user_id` e o redirecionamento vai para
     `/accounts/otp/`.
3. `POST /accounts/otp/` com o campo `otp` (código TOTP, RFC 6238 via `pyotp`) e
   `csrfmiddlewaretoken`. Só neste passo o utilizador fica autenticado.

Bloqueio de TOTP: 3 falhas seguidas bloqueiam o utilizador por 300 s
(contador na cache, por utilizador, não na sessão); o redirecionamento volta ao
login com `?otp=locked` (`backend/core/views_auth.py`).

Estes endpoints são formulários HTML, não uma API JSON. Para automação sem
pessoa, use contas de serviço (secção 2).

### Cookies e CSRF

| Item | Valor | Origem |
|------|-------|--------|
| Cookie de sessão | `mapsprovefiber_sessionid`, `HttpOnly`, `SameSite=Lax`, 2 semanas por omissão (`SESSION_COOKIE_AGE`) | `settings/base.py` |
| Cookie CSRF | `mapsprovefiber_csrftoken`, legível por JavaScript (`CSRF_COOKIE_HTTPONLY = False`) | `settings/base.py` |
| Cabeçalho CSRF | `X-CSRFToken` | padrão do Django |

Em `POST`, `PUT`, `PATCH` e `DELETE` com sessão, o `SessionAuthentication` do DRF
exige o cabeçalho `X-CSRFToken` igual ao cookie; sem ele a resposta é **403**.
`GET` não precisa. Em produção os cookies são `Secure` (`SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`); atrás de outro domínio/porta, o `Origin` tem de constar em
`CSRF_TRUSTED_ORIGINS`.

O padrão do frontend (`frontend/src/composables/useApi.js`): `fetch` com
`credentials: 'same-origin'` e `X-CSRFToken` vindo de `window.CSRF_TOKEN`
(injetado em `base_spa.html`). Mutações no SPA passam sempre por `useApi()`.

---

## 2. Token Bearer (contas de serviço, integrações)

```
Authorization: Bearer <token>
```

- Esquema único: `Bearer`. `Token <x>` **não** é aceito.
- O token é opaco (`secrets.token_urlsafe(32)`); no servidor só se guarda o
  SHA-256 e os 4 últimos caracteres. O valor em claro aparece **uma vez**, ao
  ser gerado.
- Cabeçalho Bearer com token desconhecido, revogado, expirado ou de conta
  inativa devolve **401** (nunca cai para anónimo).
- Sem CSRF: a classe de token vem antes da sessão, por isso um cliente com token
  não passa pelo CSRF.
- Também vale nas rotas `/api/*` guardadas pelo `AuthRequiredMiddleware` (o
  mesmo cabeçalho é aceito e o principal é reaproveitado pelo DRF).
- `ServiceAccountToken.last_used_at` regista a última autenticação (no máximo
  uma escrita por minuto).

### O que o principal pode fazer

O principal **não é um `User`**: `is_staff = False`, `is_superuser = False`,
`has_perm()` devolve sempre `False`. Só satisfaz `is_authenticated`. Na
prática passa em `IsAuthenticated` (todos os viewsets de inventário, por
exemplo `/api/v1/sites/`) e em `@login_required`, mas **não** passa em endpoints
que exigem `is_staff` ou permissões de modelo. Não há escopos por conta nem
throttling por token (ADR 0008).

### Como se cria, roda e revoga um token

Só há duas vias (nenhum comando `manage.py` nem endpoint de API existe para isto):

1. **Django admin** (`/admin/`, app *Service accounts*): criar a conta
   (`ServiceAccount`: nome, e-mail, `auto_rotate_days`, `notify_before_days`,
   `notification_webhook_url`) e usar a ação *Gerar token* (`generate-token/`),
   com expiração e observação opcionais. O token em claro é mostrado numa
   mensagem, uma só vez. Exige superutilizador ou a permissão
   `service_accounts.manage_tokens`. Cada evento fica em
   `ServiceAccountAuditLog`.
2. **Rotação automática**: a tarefa Celery
   `service_accounts.enforce_rotation_policies_task` corre a cada 3600 s
   (`SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS`). Para contas com
   `auto_rotate_days`, cria um token novo, revoga o anterior e, se houver
   `notification_webhook_url`, envia o novo token por webhook; com
   `notify_before_days` envia também um aviso antes do prazo. O integrador tem
   de receber o token novo (webhook ou fora de banda) antes de o antigo expirar.

Revogação manual: `ServiceAccountToken.revoke()` existe no modelo, mas o admin
não tem ação nem botão para isso (o inline de tokens é só de leitura; só há
`generate-token/`). Na prática um token deixa de valer por expiração, por
rotação automática, ou ao desativar a conta (`is_active = False`), que o
invalida de imediato.

### Uso

```bash
curl -H "Authorization: Bearer $PROVEMAPS_TOKEN" \
  https://SEU_HOST/api/v1/sites/
```

Mais exemplos em [EXAMPLES.md](EXAMPLES.md).

---

## Versionamento

Só existe `v1`, lido do prefixo do caminho (`/api/v1/`) por
`core.api_versioning.PathPrefixVersioning`. Rotas legadas sem prefixo
(`/api/users/`, `/api/config/`) contam como `v1`. Qualquer outra versão
(`/api/v2/...`) devolve **404**.

## Esquema OpenAPI

- `GET /api/schema/` — esquema OpenAPI 3 (drf-spectacular).
- `GET /api/schema/swagger/` — Swagger UI auto-hospedado (sem CDN).

Ambos exigem autenticação (`SERVE_PERMISSIONS = IsAuthenticated`), sessão ou
Bearer. Cobrem as views DRF; as function views Django (`/api/v1/inventory/*`,
`/api/users/*`, `/setup_app/api/*`) ainda não aparecem no esquema (EV-0030).
Os esquemas de segurança declarados são `cookieAuth` e `bearerAuth`.

## Permissões

- Padrão DRF: `IsAuthenticated`.
- Os viewsets de inventário (`sites`, `devices`, `device-groups`, `ports`,
  `fiber-cables`, `import-rules`) usam `IsAuthenticated` apenas: qualquer
  sessão autenticada ou conta de serviço lê **e escreve**.
- Endpoints marcados como `staff_required` ou com permissões de modelo exigem
  uma pessoa com os flags correspondentes; contas de serviço ficam de fora.
- Rotas de diagnóstico só existem com `ENABLE_DIAGNOSTIC_ENDPOINTS=true`.

## Limitação de taxa

Não há throttling configurado no `REST_FRAMEWORK` (sem `DEFAULT_THROTTLE_*`).

## CORS

Não há CORS: `corsheaders` não está em `INSTALLED_APPS` nem no middleware. A API
é pensada para o mesmo domínio do SPA ou para clientes que não são navegadores.
Um navegador noutro domínio não consegue chamá-la com credenciais.

## O que não existe

Documentação anterior descrevia estas funcionalidades; **não existem** neste
código:

- `rest_framework.authtoken`, `Authorization: Token <x>`, `POST /api/token/`.
- Basic Auth (`BasicAuthentication` não está em `DEFAULT_AUTHENTICATION_CLASSES`).
- JWT/OAuth.
- CORS e throttling.
- Comandos `manage.py` para criar contas de serviço ou tokens.
- Login por API JSON (o login é de formulário, em dois passos).

## Boas práticas

- Guarde o token em cofre/variável de ambiente, nunca em código, HTML de teste
  ou repositório (CLAUDE.md §2.5). Tokens que vazaram rodam-se.
- Use HTTPS em produção.
- Dê a cada integração a sua conta de serviço e use `auto_rotate_days`.
- Verifique `last_used_at` para detetar tokens mortos.
