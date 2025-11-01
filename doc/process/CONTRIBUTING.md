# 🧭 Contributing Guide — MapsProveFiber

Obrigado por contribuir com o **MapsProveFiber**!
Este guia explica como configurar o ambiente local, rodar testes e seguir o padrão de código do projeto.

---

## 🚀 Ambiente de Desenvolvimento

### 1. Requisitos

- **Python 3.12+**
- **Docker** e **Docker Compose**
- **Make** (Linux/macOS) ou `make` equivalente no Windows (Git Bash)
- Redis e MariaDB são iniciados automaticamente pelo Compose

### 2. Setup local

```bash
git clone https://github.com/kaled182/mapsprovefiber.git
cd mapsprovefiber
cp .env.dev.example .env.dev
make up
# ou
docker compose up --build
```

### 3. Acessar
- App: http://localhost:8000
- Admin: http://localhost:8000/admin
- Healthchecks: `/healthz`, `/ready`, `/live`

---

## 🧪 Testes

```bash
make test
pytest -v
```

### Marcadores disponíveis
| Marker | Descrição |
|---------|------------|
| `unit` | Testes rápidos e isolados |
| `integration` | Testes com banco e Redis |
| `db` | Requer acesso ao banco |
| `zabbix`, `maps`, `celery` | Testes específicos |

---

## 🧹 Lint & Formatação

```bash
make lint
black .
ruff check .
isort .
mypy .
```

---

## 🧩 Padrão de Commits

```
feat(routes): adiciona task para atualização em lote
fix(zabbix): corrige parsing de triggers
docs: atualiza guia de deploy
```

---

## 🔄 Pull Requests

1. Crie branch a partir de `main`.
2. Rode `make test` e `make lint` (e `npm test` quando alterar JS).
3. Revise a checklist de internacionalização em [`doc/reference/i18n_and_pr_guidelines.md`](../reference/i18n_and_pr_guidelines.md).
4. Preencha o template de PR (adição automática via GitHub) marcando cada item da checklist.
5. Atualize documentação ou ADRs sempre que alterar convenções ou arquitetura.

---

## ❤️ Agradecimentos

Obrigado por ajudar a evoluir o **MapsProveFiber**!
