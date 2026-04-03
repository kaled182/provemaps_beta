# Security Policy - MapsProveFiber

This document outlines the security guidelines and vulnerability reporting process for **MapsProveFiber**.

---

## General policy

- Every change must be reviewed before merge.
- Passwords, keys, and tokens must never be committed to the repository.
- Use `.env.prod.template` as the source of sensitive variables.
- All production communication must enforce **HTTPS + HSTS**.

---

## Security principles

### Configuration
- Ensure `DEBUG=False` in production.
- Enable `SECURE_SSL_REDIRECT=True`.
- Configure `SESSION_COOKIE_SECURE=True`.
- Configure `CSRF_COOKIE_SECURE=True`.
- Maintain an explicit `ALLOWED_HOSTS` list.
- Keep `SENTRY_DSN` active for error capture.

### Secrets
- Generate a strong `SECRET_KEY` for each environment.
- Store secrets in a managed secret vault.
- Keep `.env.prod` private and off source control.

### Access and auditing
- Enforce two-factor authentication for staff.
- Avoid logging sensitive IP information.
- Use the `setup_app` audit utilities.

---

## Vulnerability disclosure

1. **Do not open a public issue.**
2. Send the report to **security@mapsprovefiber.com**.
3. Include the following information:
   - Description
   - Reproduction steps
   - Impact assessment

Average response time: 72 business hours.

---

## Dependencies
- `django>=5.2`
- `celery>=5.4`
- `django-redis`
- `psutil`

Run weekly checks with `pip-audit` and `safety`.

---

## Last review
> October 2025
