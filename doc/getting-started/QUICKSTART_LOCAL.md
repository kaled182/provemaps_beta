# 🚀 Guia Rápido - Desenvolvimento Local

## ✅ Configuração Completa

### Credenciais de Acesso
- **URL:** http://localhost:8000
- **Admin:** http://localhost:8000/admin/
- **Usuário:** `admin`
- **Senha:** `admin123`

> 💡 **Nota:** No Docker, o superuser é criado automaticamente no primeiro deploy.  
> Para desenvolvimento local, execute: `python manage.py ensure_superuser`

### Banco de Dados
- **Tipo:** SQLite (db.sqlite3)
- **Sem necessidade de MySQL/MariaDB**

### Cache/Redis
- **Não é necessário** - health checks configurados para ignorar falhas

---

## 🔧 Comandos Úteis

### Servidor
```powershell
# Iniciar servidor
python manage.py runserver

# Iniciar em porta específica
python manage.py runserver 8080

# Acessível na rede local
python manage.py runserver 0.0.0.0:8000
```

### Banco de Dados
```powershell
# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Criar superusuário padrão (admin/admin123)
python manage.py ensure_superuser

# Criar superusuário customizado (interativo)
python manage.py createsuperuser

# Shell Django
python manage.py shell
```

### Assets Estáticos
```powershell
# Coletar arquivos estáticos
python manage.py collectstatic --noinput
```

### Testes
```powershell
# Rodar todos os testes
python -m pytest tests/ -v

# Rodar testes específicos
python -m pytest tests/test_smoke.py -v

# Com cobertura
python -m pytest --cov --cov-report=html
```

---

## 🌐 Endpoints Importantes

### Aplicação
- **Dashboard:** http://localhost:8000/maps_view/dashboard/
- **Setup:** http://localhost:8000/setup_app/
- **Route Builder:** http://localhost:8000/routes_builder/
- **Admin:** http://localhost:8000/admin/

### Health & Metrics
- **Health (completo):** http://localhost:8000/healthz
- **Readiness:** http://localhost:8000/ready
- **Liveness:** http://localhost:8000/live
- **Métricas Prometheus:** http://localhost:8000/metrics/metrics

### Documentação
- **Docs Index:** http://localhost:8000/setup_app/docs/
- **API Docs:** http://localhost:8000/setup_app/docs/reference-root/API_DOCUMENTATION.md/

---

## 🔍 Verificações Rápidas

### Health Check (modo não-estrito)
```powershell
# PowerShell
Invoke-WebRequest http://localhost:8000/healthz | Select-Object StatusCode, Content

# Ou via navegador
# http://localhost:8000/healthz
```

### Métricas
```powershell
Invoke-WebRequest http://localhost:8000/metrics/metrics
```

---

## ⚙️ Configuração Atual (.env)

### Características
- ✅ **DEBUG:** True (erros detalhados)
- ✅ **SQLite:** Banco local sem configuração
- ✅ **Health checks relaxados:** Ignora falhas de cache/Redis
- ✅ **Cache-safe:** Código tolera Redis offline gracefully
- ✅ **Sem dependências externas:** Roda standalone

### Comportamento do Cache (Redis Offline)
Quando Redis não está disponível (modo desenvolvimento):
- ✅ **Degradação graceful:** Aplicação continua funcionando sem cache
- ✅ **Logs debug:** Mensagens de cache offline em nível DEBUG
- ✅ **Sem erros:** Não gera HTTP 500, apenas opera sem cache
- ⚠️ **Performance reduzida:** Sem cache, consultas diretas ao Zabbix (mais lento)

### Modificar Configuração
Edite `.env` para ajustar:
```bash
DEBUG=True                          # Modo desenvolvimento
HEALTHCHECK_STRICT=false           # Modo relaxado
HEALTHCHECK_IGNORE_CACHE=true      # Ignora Redis offline
ENABLE_DIAGNOSTIC_ENDPOINTS=false  # Desabilita ping/telnet
```

---

## 🐛 Troubleshooting

### Porta já em uso
```powershell
# Usar outra porta
python manage.py runserver 8080
```

### Resetar banco de dados
```powershell
# Apagar banco SQLite
Remove-Item db.sqlite3

# Recriar
python manage.py migrate
python manage.py createsuperuser
```

### Limpar cache de templates
```powershell
# Reiniciar servidor (CTRL+C e rodar novamente)
python manage.py runserver
```

### Redis Offline (Normal em Dev)
**Sintoma:** Mensagens `[DEBUG] Cache offline (Redis indisponível)`

**Solução:** Isso é **normal** em desenvolvimento! A aplicação funciona sem Redis.
- ✅ Endpoints retornam HTTP 200
- ⚠️ Performance reduzida (sem cache)
- ℹ️ Para melhor performance, instale Redis (opcional):
  ```powershell
  # Windows: baixar de https://github.com/microsoftarchive/redis/releases
  # Ou usar Docker
  docker run -d -p 6379:6379 redis:alpine
  ```

Ver detalhes completos em: [`doc/reference/REDIS_GRACEFUL_DEGRADATION.md`](../reference/REDIS_GRACEFUL_DEGRADATION.md)

---

## 📚 Próximos Passos

1. **Explorar Dashboard:** http://localhost:8000/maps_view/dashboard/
2. **Configurar Zabbix (opcional):** Edite `.env` com credenciais
3. **Testar Health Endpoints:** Veja status do sistema
4. **Acessar Documentação:** http://localhost:8000/setup_app/docs/

---

## 🎯 Features Disponíveis (sem configuração adicional)

- ✅ Interface administrativa Django
- ✅ Dashboard de visualização
- ✅ Health checks operacionais
- ✅ Métricas Prometheus
- ✅ Sistema de documentação
- ✅ Route builder (sem dados de rota por enquanto)

**Para features completas (Zabbix, Maps):** Configure variáveis no `.env`

---

## 📝 Notas

- **Produção:** Use `.env.prod.backup` como referência
- **Testes:** Suite passa com 46/52 testes (88.5%)
- **Performance:** Modo dev tem observabilidade reduzida
- **Segurança:** `SECRET_KEY` é placeholder - mude em produção

---

**Desenvolvido com Django 5.2.7 + Python 3.13**
