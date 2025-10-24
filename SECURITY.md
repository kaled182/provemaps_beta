# 🔒 Security Policy — MapsProveFiber

Este documento define as diretrizes de segurança e reporte de vulnerabilidades do projeto **MapsProveFiber**.

---

## 🧠 Política Geral

- Todo código é revisado antes de merge.
- Senhas, chaves e tokens **nunca** devem ser commitados.
- Use `.env.prod.template` para variáveis sensíveis.
- Toda comunicação em produção deve usar **HTTPS + HSTS**.

---

## 🧱 Princípios de Segurança

### Configurações
- `DEBUG=False` em produção
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `ALLOWED_HOSTS` definido explicitamente
- `SENTRY_DSN` ativo

### Senhas e Segredos
- Gere `SECRET_KEY` seguro
- Use Secret Manager
- `.env.prod` privado

### Acesso e Auditoria
- Staff com 2FA
- Logs sem IPs sensíveis
- Auditoria via `setup_app`

---

## 🚨 Reportar Vulnerabilidades

1. **Não abra um issue público.**
2. Envie para **security@mapsprovefiber.com**
3. Inclua:
   - Descrição
   - Reprodução
   - Impacto

Resposta média: 72h úteis.

---

## 🧩 Dependências
- `django>=5.2`
- `celery>=5.4`
- `django-redis`
- `psutil`

Verificações semanais via `pip-audit` e `safety`.

---

## 🧾 Última revisão
> Outubro/2025
