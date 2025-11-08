# 📊 Análise de Impacto: Reorganização Backend/Frontend

## 🎯 Estrutura Proposta

```
provemaps_beta/
├── backend/                    # Django apps + Python code
│   ├── manage.py
│   ├── core/
│   ├── inventory/
│   ├── monitoring/
│   ├── maps_view/
│   ├── routes_builder/
│   ├── setup_app/
│   ├── gpon/
│   ├── dwdm/
│   ├── integrations/
│   ├── settings/
│   ├── templates/              # Django templates
│   └── tests/
├── frontend/                   # Static assets & JS
│   ├── static/
│   │   ├── js/
│   │   ├── css/
│   │   └── images/
│   ├── package.json
│   ├── babel.config.js
│   └── node_modules/
├── scripts/                    # Deployment & utility scripts
│   ├── smoke_phase5.ps1
│   ├── deploy_initial_v2.ps1
│   └── ...
├── doc/                        # Documentation
│   ├── developer/
│   ├── operations/
│   └── ...
├── database/                   # DB files & migrations
│   ├── db.sqlite3
│   └── sql/
├── docker/                     # Docker files (opcional)
│   ├── dockerfile
│   ├── docker-compose.yml
│   └── docker-entrypoint.sh
└── [root config files]
    ├── .env
    ├── .gitignore
    ├── requirements.txt
    └── README.md
```

---

## 📋 Estrutura Atual

```
provemaps_beta/
├── core/                       # Django core
├── inventory/                  # Django app
├── monitoring/                 # Django app
├── maps_view/                  # Django app (tem static/js + templates)
├── routes_builder/             # Django app (tem static/js + templates)
├── setup_app/                  # Django app (tem static/js + templates)
├── gpon/                       # Django app
├── dwdm/                       # Django app
├── integrations/               # Django integrations
├── settings/                   # Django settings
├── templates/                  # Django templates globais
├── staticfiles/                # Django collected statics
├── tests/                      # Tests
├── scripts/                    # Scripts ✅ (já OK)
├── doc/                        # Docs ✅ (já OK)
├── manage.py
├── package.json                # Frontend deps
├── babel.config.js             # Frontend config
├── node_modules/               # Frontend deps installed
├── db.sqlite3                  # Database
├── sql/                        # SQL scripts
├── dockerfile
├── docker-compose.yml
└── [outros arquivos config]
```

---

## 💥 Impactos da Mudança

### 🔴 Alto Impacto

#### 1. **Django Settings (CRITICAL)**

**Arquivos afetados:**
- `settings/base.py`
- `settings/development.py`
- `settings/production.py`

**Mudanças necessárias:**

```python
# settings/base.py (ANTES)
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# settings/base.py (DEPOIS)
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # +1 nível (backend/)
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_DIR = BASE_DIR / 'frontend'
DATABASE_DIR = BASE_DIR / 'database'

STATIC_ROOT = FRONTEND_DIR / 'staticfiles'
STATICFILES_DIRS = [
    FRONTEND_DIR / 'static',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_DIR / 'db.sqlite3',  # Mudou
    }
}

TEMPLATES[0]['DIRS'] = [
    BACKEND_DIR / 'templates',  # Global templates
]
```

#### 2. **Django Apps - STATIC_URL & Templates**

**Cada app Django que tem `static/` ou `templates/`:**
- `maps_view/`
- `routes_builder/`
- `setup_app/`

**Impacto:** Nenhum! Django usa namespacing automático:
- `{% static 'maps_view/js/dashboard.js' %}` continua funcionando
- Templates em `maps_view/templates/maps_view/` continuam funcionando

**Motivo:** Django's `STATICFILES_FINDERS` e `APP_DIRS=True` cuidam disso.

#### 3. **manage.py & WSGI/ASGI**

**manage.py (root → backend/):**
```python
# manage.py (ANTES)
sys.path.insert(0, str(Path(__file__).resolve().parent))

# manage.py (DEPOIS)
# Não precisa mudar, já está correto
```

**core/wsgi.py e core/asgi.py:**
```python
# ANTES
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.production')

# DEPOIS (sem mudança - settings é relativo ao PYTHONPATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.production')
```

#### 4. **Docker & Docker Compose**

**dockerfile (ANTES):**
```dockerfile
WORKDIR /app
COPY requirements.txt .
COPY . .
```

**dockerfile (DEPOIS):**
```dockerfile
WORKDIR /app

# Copy backend
COPY backend/requirements.txt backend/
COPY backend/ backend/

# Copy frontend (apenas static files compilados)
COPY frontend/static frontend/static/

# Copy scripts se necessário
COPY scripts/ scripts/

# Copy database migrations
COPY database/ database/

# Set working directory to backend
WORKDIR /app/backend
```

**docker-compose.yml:**
```yaml
# ANTES
volumes:
  - .:/app

# DEPOIS
volumes:
  - ./backend:/app/backend
  - ./frontend/staticfiles:/app/frontend/staticfiles
  - ./database:/app/database
```

#### 5. **Imports Python**

**Impacto:** ZERO se PYTHONPATH correto!

**Solução:** Ajustar PYTHONPATH para apontar para `backend/`:

```bash
# .env (ANTES)
PYTHONPATH=.

# .env (DEPOIS)
PYTHONPATH=./backend
```

**Docker:**
```dockerfile
ENV PYTHONPATH=/app/backend
```

**manage.py:**
```python
# Adicionar no topo
import sys
from pathlib import Path

# Add backend dir to Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))
```

#### 6. **Celery Workers**

**celery.py:**
```python
# ANTES
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.development')

# DEPOIS (sem mudança se PYTHONPATH correto)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.development')
```

**Comando de execução:**
```bash
# ANTES
celery -A core worker

# DEPOIS (com PYTHONPATH)
cd backend && celery -A core worker
# OU
PYTHONPATH=./backend celery -A core worker
```

---

### 🟡 Médio Impacto

#### 7. **Frontend Build Pipeline**

**package.json scripts:**
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  }
}
```

**Mover para `frontend/package.json`:**
- `package.json`
- `babel.config.js`
- `node_modules/`

**Ajustar paths nos testes:**
```javascript
// ANTES
import { Dashboard } from '../maps_view/static/js/dashboard.js';

// DEPOIS
import { Dashboard } from '../static/js/maps_view/dashboard.js';
```

#### 8. **Static Files Collection**

**Comando collectstatic:**
```bash
# ANTES
python manage.py collectstatic

# DEPOIS
cd backend && python manage.py collectstatic
```

**Output:** `frontend/staticfiles/` (configurado em `STATIC_ROOT`)

#### 9. **Scripts de Deploy**

**Todos os scripts em `scripts/`:**
- `smoke_phase5.ps1`
- `deploy_initial_v2.ps1`
- `cleanup_refatorar.py`
- etc.

**Ajustar paths:**
```powershell
# ANTES
python manage.py migrate

# DEPOIS
cd backend; python manage.py migrate
# OU
python backend/manage.py migrate
```

---

### 🟢 Baixo Impacto

#### 10. **Documentação**

`doc/` → Sem mudanças (já na raiz)

#### 11. **Git & CI/CD**

**.gitignore - Ajustar paths:**
```gitignore
# ANTES
/staticfiles/
/db.sqlite3
/__pycache__/

# DEPOIS
/frontend/staticfiles/
/database/db.sqlite3
/backend/**/__pycache__/
```

**GitHub Actions (se houver):**
```yaml
# Ajustar working-directory
jobs:
  test:
    steps:
      - name: Run tests
        working-directory: ./backend
        run: pytest
```

---

## 📊 Resumo de Arquivos a Mover

### Backend (para `backend/`)
- ✅ `manage.py`
- ✅ `core/`
- ✅ `inventory/`
- ✅ `monitoring/`
- ✅ `maps_view/`
- ✅ `routes_builder/`
- ✅ `setup_app/`
- ✅ `gpon/`
- ✅ `dwdm/`
- ✅ `integrations/`
- ✅ `settings/`
- ✅ `templates/` (global)
- ✅ `tests/`
- ✅ `conftest.py`
- ✅ `pytest.ini`
- ✅ `pyproject.toml`
- ✅ `requirements.txt`
- ✅ `requirements_full.txt`

### Frontend (para `frontend/`)
- ✅ `package.json`
- ✅ `babel.config.js`
- ✅ `node_modules/`
- ✅ Consolidar todos os `static/` de apps em `frontend/static/`
- ✅ `staticfiles/` → `frontend/staticfiles/`

### Database (para `database/`)
- ✅ `db.sqlite3`
- ✅ `test_db.sqlite3`
- ✅ `sql/`

### Docker (opcional: para `docker/`)
- ✅ `dockerfile`
- ✅ `docker-compose.yml`
- ✅ `docker-compose.test.yml`
- ✅ `docker-entrypoint.sh`

### Scripts (já OK)
- ✅ `scripts/` (já separado)

### Doc (já OK)
- ✅ `doc/` (já separado)

### Root (manter na raiz)
- ✅ `.env`
- ✅ `.env.example`
- ✅ `.gitignore`
- ✅ `.gitattributes`
- ✅ `README.md`
- ✅ `makefile`
- ✅ `.github/`
- ✅ `.vscode/`

---

## ⚠️ Riscos & Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Quebra de imports** | Alta | Alto | Testar localmente antes de commit |
| **Docker build falha** | Média | Alto | Atualizar Dockerfile incrementalmente |
| **Static files não encontrados** | Média | Médio | Rodar collectstatic e testar |
| **Celery workers não iniciam** | Baixa | Alto | Verificar PYTHONPATH |
| **Migrations não aplicam** | Baixa | Alto | Testar em DB limpo |
| **CI/CD quebra** | Alta | Médio | Atualizar workflows GitHub Actions |

---

## 🚀 Estratégia de Migração Recomendada

### Opção 1: Big Bang (1 commit, alto risco)
**Prós:** Rápido  
**Contras:** Difícil debug se algo quebrar  
**Recomendação:** ❌ NÃO recomendado

### Opção 2: Incremental (múltiplos commits, baixo risco) ✅
**Prós:** Seguro, testável  
**Contras:** Mais demorado  
**Recomendação:** ✅ **RECOMENDADO**

**Fases:**
1. **Fase A:** Criar estrutura de diretórios
2. **Fase B:** Mover backend (Django apps)
3. **Fase C:** Ajustar settings & paths
4. **Fase D:** Mover frontend (static files)
5. **Fase E:** Mover database files
6. **Fase F:** Atualizar Docker
7. **Fase G:** Atualizar scripts
8. **Fase H:** Testar tudo

### Opção 3: Branch paralela (safest) 🏆
**Criar branch `refactor/folder-structure`:**
- Fazer toda reorganização
- Testar extensivamente
- Merge só quando 100% funcional

---

## 📋 Checklist de Validação Pós-Migração

- [ ] **Django:**
  - [ ] `python manage.py check`
  - [ ] `python manage.py migrate`
  - [ ] `python manage.py collectstatic`
  - [ ] `python manage.py runserver` (inicia OK)

- [ ] **Testes:**
  - [ ] `pytest -q` (199/199 passando)
  - [ ] `npm test` (frontend tests)

- [ ] **Static Files:**
  - [ ] CSS carrega corretamente
  - [ ] JS carrega corretamente
  - [ ] Imagens carregam

- [ ] **Celery:**
  - [ ] `celery -A core worker` (inicia OK)
  - [ ] `celery -A core beat` (inicia OK)

- [ ] **Docker:**
  - [ ] `docker-compose build` (sucesso)
  - [ ] `docker-compose up` (todos serviços sobem)

- [ ] **Smoke Tests:**
  - [ ] `scripts/smoke_phase5.ps1` (todos passam)

---

## 💡 Recomendação Final

### ✅ **FAZER DEPOIS DO MERGE DA FASE 5**

**Por quê?**
1. Fase 5 já está pronta para merge (PR aberto)
2. Essa reorganização é uma mudança estrutural grande
3. Melhor fazer em PR separado para facilitar review
4. Menos risco de conflitos

### 📅 **Timeline Sugerido:**

1. **Agora:** Merge Fase 5 (PR atual)
2. **Próximo:** Criar nova branch `refactor/folder-structure`
3. **Depois:** Implementar reorganização incremental
4. **Por último:** Merge reorganização após testes completos

### 🎯 **Como Fazer:**

```bash
# 1. Merge Fase 5 primeiro
git checkout inicial
git merge refactor/modularization

# 2. Criar nova branch para reorganização
git checkout -b refactor/folder-structure

# 3. Executar script de reorganização (vou criar)
python scripts/reorganize_structure.py

# 4. Testar tudo
pytest -q
npm test
docker-compose up

# 5. Commit e PR
git add .
git commit -m "refactor: reorganize project structure (backend/frontend/database)"
gh pr create --base inicial
```

---

## 🤔 Decisão

**Você quer:**

**A)** Fazer essa reorganização **AGORA** (antes de merge da Fase 5)?  
   - ⚠️ Maior risco, PR mais complexo

**B)** Fazer **DEPOIS** do merge da Fase 5? ✅ **RECOMENDADO**  
   - ✅ Menor risco, PRs menores, mais fácil review

**C)** **NÃO FAZER** (manter estrutura atual)?  
   - Continuar com estrutura Django tradicional

**Qual opção prefere?**
