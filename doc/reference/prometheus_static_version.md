# Cache Busting + Prometheus Integration Summary

Todas as seguintes funcionalidades foram implementadas com sucesso:

## 1. ManifestStaticFilesStorage em Dev
- Arquivo: `settings/dev.py`
- Storage: `ManifestStaticFilesStorage` para hash automático de arquivos
- Requer: `python manage.py collectstatic --noinput` após mudanças

## 2. Versão com Git SHA
- Arquivo: `settings/dev.py`
- Função: `_git_sha()` captura SHA curto do commit
- Formato: `<sha>-<timestamp>` (ex: `e90e25c-20251026200851`)
- Print no console: `[STATIC_VERSION] STATIC_ASSET_VERSION=...`

## 3. Métrica Prometheus
- Arquivos criados:
  - `core/metrics_static_version.py` (define métrica Info)
  - `core/apps.py` (CoreConfig com ready() para init)
- Métrica: `static_asset_version_info{version="...",git_sha="...",timestamp="..."}`
- Endpoint: `/metrics/metrics` (django-prometheus)

## 4. Script de Verificação
- Arquivo: `scripts/verify_asset_version.py`
- Valida se versão atual contém SHA do repo
- Uso:
  ```powershell
  $env:DJANGO_SETTINGS_MODULE = "settings.dev"
  python scripts/verify_asset_version.py
  ```

## 5. Documentação
- Arquivo: `./cache_busting.md`
- Seções:
  - Estratégias (query param, no-cache, hashing, SHA)
  - Workflow de dev
  - Verificação (script + Prometheus)
  - Troubleshooting

## Pontos de Atenção

### Encoding (Windows)
- **Issue**: Emojis (🔐, 🎛️) causam `UnicodeDecodeError` em Windows (cp1252)
- **Fix**: Substituídos por tags ASCII: `[STATIC_VERSION]`, `[DEBUG_TOOLBAR]`, etc.

### Database (Opcional)
- O servidor requer DB válido para init completo
- Métrica Prometheus é inicializada no `CoreConfig.ready()`
- Se DB falha, ready() não executa → métrica não aparece
- **Workaround**:
  - Usar SQLite em dev: `$env:DB_ENGINE="sqlite"` ou
  - Configurar credenciais MySQL/MariaDB corretas em `.env`

### Endpoint Prometheus
- URL correta: `/metrics/metrics` (não `/metrics/`)
- django-prometheus adiciona sub-rota `metrics` dentro de `metrics/`

## Validação Manual

### 1. Verificar SHA no Console
```powershell
$env:DEBUG = "True"
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
python manage.py check
# Saída esperada:
# [STATIC_VERSION] STATIC_ASSET_VERSION=abc123-YYYYMMDDHHMMSS
# System check identified no issues (0 silenced).
```

### 2. Ver Métrica no Prometheus
```powershell
# Start server (com DB válido)
python manage.py runserver 8000

# Query via browser ou curl
# http://localhost:8000/metrics/metrics
# Procurar por: static_asset_version_info{...}
```

### 3. Script de Verificação
```powershell
$env:DJANGO_SETTINGS_MODULE = "settings.dev"
python scripts/verify_asset_version.py
# Output:
# STATIC_ASSET_VERSION=abc123-20251026200851
# GIT_SHA=abc123
# OK: versão contém SHA.
```

## Próximos Passos (Opcional)

1. **Badge UI**: Adicionar badge visual com versão no rodapé ou header da aplicação
2. **Grafana Dashboard**: Criar painel mostrando histórico de versões deployadas
3. **CI/CD Integration**: Adicionar versão ao build artifact metadata
4. **Alerting**: Configurar alerta se versão não muda após N horas (indica deploy travado)

## Arquivos Modificados

- `settings/base.py`: Adicionado `core.apps.CoreConfig` em INSTALLED_APPS
- `settings/dev.py`: ManifestStaticFilesStorage, `_git_sha()`, versão com SHA, emojis removidos
- `core/apps.py`: Criado CoreConfig.ready() para init de métrica
- `core/metrics_static_version.py`: Criado módulo de métrica Prometheus
- `./cache_busting.md`: Atualizado com SHA, Prometheus, verificação
- `scripts/verify_asset_version.py`: Criado script de validação

---

**Status**: ✅ Implementação completa. Testado com `manage.py check`. Métrica exposta em `/metrics/metrics` quando servidor inicia com DB válido.
