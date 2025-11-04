# 🧭 Contributing Guide — MapsProveFiber

Thank you for contributing to **MapsProveFiber**!
This guide explains how to set up the local environment, run tests, and follow the project coding standards.

---

## 🚀 Development Environment

### 1. Requirements

- **Python 3.12+**
- **Docker** and **Docker Compose**
- **Make** (Linux/macOS) or an equivalent `make` for Windows (Git Bash)
- Redis and MariaDB are started automatically by Docker Compose

### 2. Local setup

```bash
git clone https://github.com/kaled182/provemaps_beta.git
cd mapsprovefiber
cp .env.dev.example .env.dev
make up
# or
docker compose up --build
```

### 3. Access
- App: http://localhost:8000
- Admin: http://localhost:8000/admin
- Health checks: `/healthz`, `/ready`, `/live`

---

## 🧪 Testing

```bash
make test
pytest -v
```

### Available markers
| Marker | Description |
|---------|------------|
| `unit` | Fast, isolated tests |
| `integration` | Requires database and Redis |
| `db` | Database access required |
| `zabbix`, `maps`, `celery` | Domain-specific suites |

---

## 🧹 Lint & Formatting

```bash
make lint
black .
ruff check .
isort .
mypy .
```

---

## 🧩 Commit Convention

docs: atualiza guia de deploy
```
feat(routes): add batch update task
fix(zabbix): fix trigger parsing
docs: update deployment guide
```

---

## 🔄 Pull Requests

1. Create a branch from `main`.
2. Run `make test` and `make lint` (and `npm test` when changing JS).
3. Review the internationalisation checklist in [`doc/reference/i18n_and_pr_guidelines.md`](../reference/i18n_and_pr_guidelines.md).
4. Fill out the PR template (auto-added by GitHub) and tick every checklist item.
5. Update documentation or ADRs whenever you modify conventions or architecture.

---

## ❤️ Thank You

Thanks for helping improve **MapsProveFiber**!
