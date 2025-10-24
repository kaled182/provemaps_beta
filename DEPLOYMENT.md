# 🚀 Deployment Guide — MapsProveFiber

Guia para implantar o **MapsProveFiber** em produção.

---

## 🧩 Estrutura dos serviços

| Serviço | Porta | Descrição |
|----------|--------|------------|
| web | 8000 | Django + Gunicorn |
| celery | - | Worker de tarefas |
| beat | - | Scheduler Celery |
| redis | 6379 | Cache e filas |
| db | 3306 | MariaDB/MySQL |

---

## ⚙️ Setup

```bash
cp .env.prod.template .env.prod
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

---

## 🌐 Health

| Endpoint | Descrição |
|-----------|------------|
| `/healthz` | Status completo |
| `/ready` | Pronto para tráfego |
| `/live` | Processo ativo |
| `/metrics` | Prometheus |

---

## 🧱 Backup

```bash
docker compose exec db sh -c 'mysqldump -u root -p$MYSQL_ROOT_PASSWORD mapsprovefiber_prod > /backups/db.sql'
```

## 🔄 Rollback

```bash
git checkout <tag>
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 🧰 Troubleshooting

| Problema | Solução |
|-----------|----------|
| DB não sobe | Verifique volume ou `.env` |
| Celery parado | `docker compose restart celery beat` |
| Health 503 | Verifique Redis/DB |
| Static 404 | `python manage.py collectstatic --noinput` |

---

**MapsProveFiber — 2025**
