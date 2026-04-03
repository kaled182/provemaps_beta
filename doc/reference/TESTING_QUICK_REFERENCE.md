# Quick Reference – Testing with MariaDB

## 🚀 Initial Setup (one time)

```powershell
# 1. Start Docker
docker compose up -d

# 2. Grant permissions
.\scripts\setup_test_db.ps1
```

---

## 🧪 Run Tests

### Fast mode
```powershell
.\scripts\run_tests.ps1
```

### With coverage
```powershell
.\scripts\run_tests.ps1 -Coverage
```

### Specific test
```powershell
.\scripts\run_tests.ps1 -Path tests/test_metrics.py
```

### Reuse database (faster)
```powershell
.\scripts\run_tests.ps1 -KeepDb
```

---

## 🔧 Useful Commands

### Check running containers
```powershell
docker compose ps
```

### MariaDB logs
```powershell
docker compose logs db --tail 100 -f
```

### Web service logs
```powershell
docker compose logs web --tail 100 -f
```

### Enter the web container
```powershell
docker compose exec web bash
```

### Access MariaDB interactively
```powershell
docker compose exec db mariadb -u app -papp app
```

### List databases
```sql
SHOW DATABASES;
SHOW TABLES FROM test_app;
```

---

## 🔍 Troubleshooting

### Error 1044 (Access denied)
```powershell
.\scripts\setup_test_db.ps1
```

### Error 2002 (Can't connect)
```powershell
docker compose up -d
docker compose ps  # Ensure the db service is Up
```

### Reset everything
```powershell
docker compose down -v  # Remove volumes
docker compose up -d
.\scripts\setup_test_db.ps1
.\scripts\run_tests.ps1
```

---

## 📊 Performance

| Command | Estimated Time |
|---------|----------------|
| `setup_test_db.ps1` | ~5s (one time) |
| `run_tests.ps1` (35 tests) | ~10–15s |
| `run_tests.ps1 -KeepDb` | ~8–10s |
| `run_tests.ps1 -Path test_metrics.py` | ~3–5s |

---

## 🎯 Recommended Workflow

### Local development (fast)
```powershell
# Use SQLite for quick iteration
$env:DJANGO_SETTINGS_MODULE='settings.test_sqlite'
pytest tests/test_metrics.py -vvs
```

### Before commit (full run)
```powershell
# Validate with MariaDB
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
      MYSQL_PASSWORD: app
```

---

**Full documentation:** `./TESTING_WITH_MARIADB.md`
