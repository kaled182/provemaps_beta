# ADR 0008 — Contas de serviço autenticam a API por `Authorization: Bearer`

| Campo            | Valor                                                       |
|------------------|-------------------------------------------------------------|
| Estado           | **Aceito** (implementado em EV-0023, 2026-10-04)            |
| Data             | 2026-10-04                                                  |
| Decisores        | Equipe Técnica Simples Internet — Paulo Marcelino           |
| Tags             | `segurança`, `autenticação`, `api`, `integrações`           |
| Substitui        | —                                                           |
| Substituído por  | —                                                           |

---

## 1. Contexto e Problema

A app `service_accounts` existe desde 2025: emite tokens (SHA-256 em repouso,
só os quatro últimos caracteres visíveis), roda-os por política no Celery,
avisa por webhook e audita tudo. Mas **nenhum caminho de código os
consumia**: o `REST_FRAMEWORK` só tinha `SessionAuthentication` e o
middleware `AuthRequiredMiddleware` (EV-0002) devolve 401 a qualquer `/api/*`
sem sessão. Um integrador (Zabbix, scripts de inventário, o CRM) não tinha
forma de chamar a API sem um utilizador humano e um cookie de sessão. A
documentação de API, por sua vez, descrevia `rest_framework.authtoken` e
`/api/token/`, que nunca existiram (EV-0033).

## 2. Drivers da Decisão

- **D-1 — Aproveitar o que existe.** Modelos, admin, rotação e auditoria estão
  feitos e testados; falta só o consumidor.
- **D-2 — Princípio §2.6 do `CLAUDE.md`:** tudo autenticado por omissão. A
  solução não pode abrir caminhos anónimos nem fragilizar a sessão humana.
- **D-3 — Menor privilégio.** Uma conta de serviço não é uma pessoa: não entra
  no admin, não tem `is_staff`, não herda permissões de modelo.
- **D-4 — Uma só verificação por pedido.** Middleware e DRF não devem validar
  o mesmo token duas vezes.

## 3. Opções Consideradas

### Opção A — `rest_framework.authtoken` (um token por `User`)

**Prós:** padrão DRF, documentação abundante.
**Contras:** obriga a criar um `User` por integração (com password, grupos,
admin); deita fora a rotação/auditoria já construída; tokens sem expiração.

### Opção B — Classe de autenticação própria sobre `service_accounts` ✅

**Prós:** reutiliza rotação, expiração, revogação e auditoria; o principal é
um objeto mínimo que satisfaz `is_authenticated` e nada mais; uma função
(`authenticate_bearer`) serve o DRF e o middleware.
**Contras:** código próprio a manter (≈150 linhas, 10 testes).

### Opção C — Apagar a app

**Prós:** menos código.
**Contras:** o produto fica sem forma de integração máquina-a-máquina; a
necessidade existe (Zabbix, CRM, scripts).

## 4. Decisão

**Opção B.** `service_accounts/authentication.py` expõe:

- `authenticate_bearer(header)` → `(ServiceAccountPrincipal, token)` para um
  `Authorization: Bearer <token>` válido; `None` se o cabeçalho não é Bearer;
  `AuthenticationFailed` se é Bearer mas o token é desconhecido, revogado,
  expirado ou a conta está inativa (uma credencial errada nunca vira anónimo).
- `ServiceAccountTokenAuthentication` (DRF), **primeira** em
  `DEFAULT_AUTHENTICATION_CLASSES`, antes de `SessionAuthentication`: um
  cliente com token não passa pelo CSRF, que é preocupação de sessão.
- O `AuthRequiredMiddleware` aceita o mesmo cabeçalho nas rotas que guarda
  (`/api/*` fora do router DRF), põe o principal em `request.user` e em
  `request.service_account_principal`; o DRF reaproveita-o (D-4).
- `ServiceAccountToken.last_used_at` regista a última autenticação (escrita
  no máximo uma vez por minuto) — informa a rotação e detecta tokens mortos.

O principal **não é um `User`**: `is_staff`/`is_superuser` são `False`,
`has_perm()` devolve sempre `False`. Endpoints que exigem permissões de modelo
ou `is_staff` continuam fechados a contas de serviço; abrir um deles é decisão
explícita por endpoint, não desta ADR.

## 5. Consequências

### Positivas

- Integrações passam a autenticar sem utilizador humano nem cookie.
- Tokens têm ciclo de vida completo: emitir (admin), usar, rodar, revogar,
  auditar, ver quando foram usados pela última vez.
- A doc de API tem agora um mecanismo real para descrever (EV-0033).

### Negativas

- Mais uma superfície de autenticação a proteger: o token vale o que vale a
  conta; quem o rodar no admin tem de o entregar ao integrador fora de banda
  (o webhook de rotação já envia o novo token quando configurado).
- Sem *rate limiting* dedicado por token (o DRF não tem throttling ligado —
  EV-0030 / levantamento §5.6).

### Neutras

- Esquema único `Bearer`. `Token <x>` (estilo DRF authtoken) não é aceito, de
  propósito: um só formato a documentar.
- Permissões por conta de serviço (escopos) ficam para quando houver um caso
  real; hoje o principal só «existe» e os endpoints decidem.
