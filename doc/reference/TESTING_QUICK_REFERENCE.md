# Quick Reference - Testes com MariaDB

## 🚀 Setup Inicial (Uma vez)

```powershell
# 1. Iniciar Docker
docker compose up -d

# 2. Configurar permissões
.\scripts\setup_test_db.ps1
```

---

## 🧪 Executar Testes

### Modo Rápido
```powershell
.\scripts\run_tests.ps1
```

### Com Coverage
```powershell
.\scripts\run_tests.ps1 -Coverage
```

### Teste Específico
```powershell
.\scripts\run_tests.ps1 -Path tests/test_metrics.py
```

### Reutilizar DB (mais rápido)
```powershell
.\scripts\run_tests.ps1 -KeepDb
```

---

## 🔧 Comandos Úteis

### Ver containers rodando
```powershell
docker ps
```

### Logs do MariaDB
```powershell
docker logs mapsprovefiber-db-1 --tail 100 -f
```

### Logs do Web
```powershell
docker logs mapsprovefiber-web-1 --tail 100 -f
```

### Entrar no container web
```powershell
docker exec -it mapsprovefiber-web-1 bash
```

### Acessar MariaDB interativo
```powershell
docker exec -it mapsprovefiber-db-1 mariadb -u app -papp_password app
```

### Ver databases
```sql
SHOW DATABASES;
SHOW TABLES FROM test_app;
```

---

## 🔍 Troubleshooting

### Erro 1044 (Access denied)
```powershell
.\scripts\setup_test_db.ps1
```

### Erro 2002 (Can't connect)
```powershell
docker compose up -d
docker ps  # Verificar que db-1 está Up
```

### Limpar tudo e recomeçar
```powershell
docker compose down -v  # Remove volumes
docker compose up -d
.\scripts\setup_test_db.ps1
.\scripts\run_tests.ps1
```

---

## 📊 Performance

| Comando | Tempo Estimado |
|---------|----------------|
| `setup_test_db.ps1` | ~5s (uma vez) |
| `run_tests.ps1` (35 testes) | ~10-15s |
| `run_tests.ps1 -KeepDb` | ~8-10s |
| `run_tests.ps1 -Path test_metrics.py` | ~3-5s |

---

## 🎯 Workflow Recomendado

### Desenvolvimento Local (Rápido)
```powershell
# Use SQLite para iteração rápida
$env:DJANGO_SETTINGS_MODULE='settings.test_sqlite'
pytest tests/test_metrics.py -vvs
```

### Antes de Commit (Completo)
```powershell
# Valide com MariaDB
.\scripts\run_tests.ps1 -Coverage
```

### CI/CD
```yaml
# .github/workflows/tests.yml
services:
  mariadb:
    image: mariadb:10.11
    env:
      MYSQL_ROOT_PASSWORD: admin
      MYSQL_DATABASE: app
      MYSQL_USER: app
      MYSQL_PASSWORD: app_password
```

---

**Documentação completa:** `./TESTING_WITH_MARIADB.md`
