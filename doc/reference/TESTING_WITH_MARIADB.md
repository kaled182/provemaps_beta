# Guia de Testes com MariaDB no Docker

**Data:** 27 de Outubro de 2025  
**Objetivo:** Executar testes pytest usando MariaDB (Docker) ao invés de SQLite

---

## 🎯 Por que MariaDB para Testes?

### ✅ Vantagens
- **Ambiente próximo à produção:** Mesma engine de BD, mesmo dialeto SQL
- **Validação de constraints:** Testa constraints específicas do MariaDB
- **Detecção de incompatibilidades:** Descobre bugs que SQLite não detectaria
- **Testa migrations reais:** Valida migrations com MariaDB

### ⚠️ Trade-offs
- **Mais lento:** 10-15x mais lento que SQLite (0.8s → 10-15s)
- **Requer Docker:** Containers devem estar rodando
- **Setup inicial:** Requer configuração de permissões

---

## 🚀 Setup Inicial (Uma vez)

### 1. Iniciar Containers Docker

```powershell
# Na raiz do projeto
docker compose up -d

# Verificar que estão rodando
docker ps
# Deve mostrar: mapsprovefiber-db-1 e mapsprovefiber-web-1
```

### 2. Configurar Permissões do Banco

```powershell
# Executar script automatizado
.\scripts\setup_test_db.ps1
```

**O que o script faz:**
1. ✅ Verifica se containers estão rodando
2. ✅ Concede permissões CREATE/DROP DATABASE ao usuário `app`
3. ✅ Testa criação/remoção de database
4. ✅ Valida que tudo está configurado

**Saída esperada:**
```
🔧 Configurando permissões de teste no MariaDB...
═══════════════════════════════════════════════════

1️⃣  Verificando Docker...
   ✅ Docker está ativo

2️⃣  Verificando container MariaDB...
   ✅ Container encontrado: mapsprovefiber-db-1

3️⃣  Configurando permissões...
   ✅ Permissões configuradas com sucesso

4️⃣  Validando permissões...
   ✅ Usuário 'app' tem permissões corretas

5️⃣  Testando criação de database...
   ✅ Usuário 'app' pode criar/dropar databases

═══════════════════════════════════════════════════
✅ Configuração concluída com sucesso!
```

### 3. (Alternativa Manual) Configurar Permissões Manualmente

Se preferir fazer manualmente:

```powershell
# Entrar no container MariaDB como root
docker exec -it mapsprovefiber-db-1 mariadb -u root -padmin

# Executar SQL
GRANT ALL PRIVILEGES ON *.* TO 'app'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EXIT;
```

---

## 🧪 Executando Testes

### Opção 1: Script Automatizado (Recomendado)

```powershell
# Todos os testes
.\scripts\run_tests.ps1

# Testes específicos
.\scripts\run_tests.ps1 -Path tests/test_metrics.py

# Com coverage
.\scripts\run_tests.ps1 -Coverage

# Modo verbose
.\scripts\run_tests.ps1 -Verbose

# Reutilizar database (mais rápido em múltiplas execuções)
.\scripts\run_tests.ps1 -KeepDb
```

### Opção 2: Comando Docker Direto

```powershell
# Executar pytest dentro do container
docker exec -it mapsprovefiber-web-1 bash -c "DJANGO_SETTINGS_MODULE=settings.test pytest tests/ -v"

# Com coverage
docker exec -it mapsprovefiber-web-1 bash -c "DJANGO_SETTINGS_MODULE=settings.test pytest tests/ -v --cov=core --cov-report=html"
```

### Opção 3: Dentro do Container (Shell Interativo)

```powershell
# Entrar no container
docker exec -it mapsprovefiber-web-1 bash

# Dentro do container
export DJANGO_SETTINGS_MODULE=settings.test
pytest tests/ -v
pytest tests/test_metrics.py::TestMetricsInitialization::test_init_metrics_sets_application_info -vvs
exit
```

---

## 📊 Estrutura de Testes

### Database de Testes

**Banco de dados principal:** `app`  
**Banco de dados de teste:** `test_app` (criado/destruído automaticamente)

```python
# settings/test.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "app",  # BD principal
        "USER": "app",
        "PASSWORD": "app_password",
        "HOST": "db",  # Nome do serviço no docker-compose.yml
        "PORT": "3306",
        "TEST": {
            # pytest-django cria automaticamente 'test_app'
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}
```

### Ciclo de Vida do Database de Teste

```
pytest inicia
   ↓
Conecta ao MariaDB (host='db', database='app')
   ↓
Cria 'test_app' (DROP IF EXISTS + CREATE)
   ↓
Executa migrations em 'test_app'
   ↓
Executa testes
   ↓
Destrói 'test_app' (DROP DATABASE)
   ↓
pytest finaliza
```

---

## 🔍 Troubleshooting

### Erro: Access denied (1044)

```
E   django.db.utils.OperationalError: (1044, "Access denied for user 'app'@'%' to database 'test_app'")
```

**Causa:** Usuário `app` não tem permissão para criar databases.

**Solução:**
```powershell
.\scripts\setup_test_db.ps1
```

---

### Erro: Can't connect to MySQL server (2002)

```
E   django.db.utils.OperationalError: (2002, "Can't connect to server on 'db' (115)")
```

**Causa:** Container MariaDB não está rodando.

**Solução:**
```powershell
docker compose up -d
docker ps  # Verificar que db-1 está Up
```

---

### Erro: Access denied (1045)

```
E   pymysql.err.OperationalError: (1045, "Access denied for user 'app'@'%' (using password: YES)")
```

**Causa:** Senha incorreta.

**Solução:** Verificar variáveis de ambiente no docker-compose.yml
```yaml
environment:
  - DB_PASSWORD=app_password  # Deve ser a mesma em settings/test.py
```

---

### Testes muito lentos

**Causa:** MariaDB é mais lento que SQLite.

**Soluções:**

1. **Usar `--reuse-db`** (não destrói DB entre execuções):
```powershell
.\scripts\run_tests.ps1 -KeepDb
```

2. **Executar apenas testes modificados:**
```powershell
.\scripts\run_tests.ps1 -Path tests/test_metrics.py
```

3. **Para desenvolvimento rápido, use SQLite:**
```powershell
# Criar settings/test_sqlite.py (cópia do antigo test.py)
$env:DJANGO_SETTINGS_MODULE='settings.test_sqlite'
pytest tests/
```

---

## 📈 Comparação: MariaDB vs SQLite

| Aspecto | MariaDB (Docker) | SQLite (in-memory) |
|---------|------------------|-------------------|
| **Velocidade** | ~10-15s (35 testes) | ~0.8s (35 testes) |
| **Setup** | Docker + permissões | Zero config |
| **Produção-like** | ✅ Idêntico | ⚠️ Diferente |
| **CI/CD** | ⚠️ Requer Docker | ✅ Simples |
| **Isolamento** | ✅ Bom (test_app) | ✅ Perfeito (:memory:) |
| **Uso** | ✅ Testes de integração | ✅ Testes unitários rápidos |

### Recomendação Híbrida

```powershell
# Desenvolvimento local (rápido)
$env:DJANGO_SETTINGS_MODULE='settings.test_sqlite'
pytest tests/

# Antes de commit (validação completa)
.\scripts\run_tests.ps1 -Coverage

# CI/CD (GitHub Actions)
# Usar MariaDB via services
```

---

## 🎯 Boas Práticas

### 1. Separar Testes por Tipo

```
tests/
├── unit/              # Rápidos, sem BD (use SQLite)
├── integration/       # Lentos, com BD (use MariaDB)
└── e2e/              # Muito lentos (Selenium, etc.)
```

### 2. Usar Fixtures Eficientes

```python
# conftest.py
import pytest

@pytest.fixture(scope="session")
def django_db_setup():
    """Configuração do BD uma vez por sessão."""
    pass

@pytest.fixture
def sample_device(db):
    """Fixture reutilizável para criar dispositivo."""
    from inventory.models import Device
    return Device.objects.create(name="Test Device")
```

### 3. Usar Transações

```python
@pytest.mark.django_db(transaction=True)
def test_with_transaction():
    # Cada teste roda em uma transação isolada
    # Rollback automático após o teste
    pass
```

### 4. Mockar Chamadas Externas

```python
from unittest.mock import patch

@patch('zabbix_api.client.ZabbixAPIClient.request')
def test_zabbix_integration(mock_request):
    mock_request.return_value = {"result": []}
    # Teste não faz chamada real à API Zabbix
```

---

## 📚 Referências

- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [Django Test Database](https://docs.djangoproject.com/en/5.0/topics/testing/overview/#the-test-database)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**Criado em:** 27/10/2025  
**Autor:** GitHub Copilot  
**Versão:** 2.0 - MariaDB Integration
