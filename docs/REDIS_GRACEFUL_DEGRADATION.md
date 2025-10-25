# Redis Graceful Degradation - Desenvolvimento Local

## 🎯 Objetivo

Permitir que a aplicação funcione **sem Redis** em ambiente de desenvolvimento, degradando gracefully para operação sem cache ao invés de gerar erros HTTP 500.

---

## 🐛 Problema Original

### Sintoma
```
[ERROR] zabbix_api.views: Erro no endpoint lookup_hosts: Error 10061 connecting to 127.0.0.1:6379
redis.exceptions.ConnectionError: Error 10061 connecting to 127.0.0.1:6379. 
Nenhuma conexão pôde ser feita porque a máquina de destino as recusou ativamente.
[ERROR] django.server: "GET /zabbix_api/lookup/hosts/?groupids=22 HTTP/1.1" 500 37
```

### Causa Raiz
O código usava `cache.get()` e `cache.set()` diretamente sem tratamento de exceções, causando:
- ❌ HTTP 500 (Internal Server Error) quando Redis offline
- ❌ Stack traces longos nos logs de erro
- ❌ Experiência ruim de desenvolvimento (precisa ter Redis rodando)

---

## ✅ Solução Implementada

### 1. Cache Wrappers Seguros

Criados 3 helpers em `zabbix_api/services/zabbix_service.py`:

```python
def safe_cache_get(key, default=None):
    """Wrapper seguro para cache.get() que ignora falhas de conexão Redis."""
    try:
        return cache.get(key, default=default)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis indisponível), continuando sem cache: %s",
            exc.__class__.__name__,
        )
        return default

def safe_cache_set(key, value, timeout=None):
    """Wrapper seguro para cache.set() que ignora falhas de conexão Redis."""
    try:
        cache.set(key, value, timeout=timeout)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis indisponível), não armazenando: %s",
            exc.__class__.__name__,
        )

def safe_cache_delete(key):
    """Wrapper seguro para cache.delete() que ignora falhas de conexão Redis."""
    try:
        cache.delete(key)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis indisponível), não deletando: %s",
            exc.__class__.__name__,
        )
```

### 2. Substituições Aplicadas

#### zabbix_api/services/zabbix_service.py
- ✅ `search_hosts()` - linha ~585
- ✅ `search_hosts()` cache set - linha ~666
- ✅ `get_host_interfaces()` - linha ~677
- ✅ `get_host_interfaces()` cache set - linha ~705
- ✅ `search_hosts_by_name_ip()` - linha ~719
- ✅ `search_hosts_by_name_ip()` cache set - linha ~796
- ✅ `get_host_interfaces_detailed()` - linha ~806
- ✅ `get_host_interfaces_detailed()` cache set - linha ~836
- ✅ `test_host_connectivity()` - linha ~900
- ✅ `test_host_connectivity()` cache set - linha ~935

Total: **10 substituições** em `zabbix_service.py`

#### zabbix_api/inventory_cache.py
- ✅ `invalidate_fiber_cache()` - Wrapped com try/except

#### routes_builder/views_tasks.py
- ✅ `_check_rate_limit()` - Wrapped com try/except (fail-open)

---

## 🎭 Comportamento Atual

### Com Redis Online
```
[DEBUG] zabbix_api.services: Cache HIT para search_hosts:q=test...
→ Performance otimizada, resultados instantâneos
```

### Com Redis Offline
```
[DEBUG] zabbix_api.services: Cache offline (Redis indisponível), continuando sem cache: ConnectionError
→ Aplicação continua funcionando, consulta direto o Zabbix (mais lento, mas funcional)
```

### Comparação

| Aspecto | Antes (com erro) | Depois (graceful) |
|---------|------------------|-------------------|
| **HTTP Status** | 500 (erro) | 200 (sucesso) |
| **Logs** | [ERROR] com stack trace | [DEBUG] mensagem curta |
| **Performance** | N/A (quebra) | Sem cache, direto no Zabbix |
| **Dev Experience** | ❌ Precisa Redis | ✅ Funciona standalone |

---

## 📊 Impacto

### Arquivos Modificados
- `zabbix_api/services/zabbix_service.py` - 10 pontos de cache
- `zabbix_api/inventory_cache.py` - 1 ponto de cache
- `routes_builder/views_tasks.py` - 1 ponto de rate limiting

### Benefícios
- ✅ **Desenvolvimento mais fácil:** Não precisa instalar/configurar Redis localmente
- ✅ **Resiliência:** Aplicação tolera falhas temporárias de Redis em produção
- ✅ **Logs limpos:** Nível DEBUG ao invés de ERROR para situações esperadas
- ✅ **Fail-open:** Rate limiting permite requisições se Redis estiver offline

### Trade-offs
- ⚠️ **Performance reduzida:** Sem cache, todas as consultas vão direto ao Zabbix
- ⚠️ **Rate limiting desabilitado:** Se Redis offline, rate limiting não funciona (fail-open)
- ℹ️ **Uso de memória:** Sem cache, pode haver mais carga no Zabbix

---

## 🔧 Configuração

### Desenvolvimento Local (.env)
```bash
# Cache opcional - funciona sem Redis
HEALTHCHECK_IGNORE_CACHE=true
DEBUG=True
```

### Produção (.env)
```bash
# Redis deve estar sempre disponível em produção
REDIS_URL=redis://localhost:6379/0
HEALTHCHECK_IGNORE_CACHE=false
DEBUG=False
```

---

## ✅ Validação

### Teste Manual
1. **Sem Redis rodando:**
   ```powershell
   # Certifique-se que Redis NÃO está rodando
   curl http://localhost:8000/zabbix_api/lookup/hosts/?groupids=22
   ```
   - ✅ Deve retornar HTTP 200 (não 500)
   - ✅ Logs mostram [DEBUG], não [ERROR]

2. **Com Redis rodando:**
   ```powershell
   # Inicie Redis
   redis-server
   
   # Teste o endpoint
   curl http://localhost:8000/zabbix_api/lookup/hosts/?groupids=22
   ```
   - ✅ Deve retornar HTTP 200
   - ✅ Segunda chamada deve ser mais rápida (cache hit)

### Teste Automatizado
```python
# tests/test_cache_graceful_degradation.py
def test_zabbix_lookup_without_redis(mocker):
    """Endpoint deve funcionar mesmo com Redis offline"""
    # Mock cache.get para lançar ConnectionError
    mocker.patch('django.core.cache.cache.get', side_effect=ConnectionError)
    
    response = client.get('/zabbix_api/lookup/hosts/?groupids=22')
    
    # Não deve retornar erro
    assert response.status_code == 200
```

---

## 📚 Referências

- Django Cache Framework: https://docs.djangoproject.com/en/5.2/topics/cache/
- Redis Exception Handling: https://redis-py.readthedocs.io/en/stable/exceptions.html
- Graceful Degradation Pattern: https://en.wikipedia.org/wiki/Graceful_degradation

---

## 🚀 Próximos Passos (Opcional)

- [ ] Adicionar métricas Prometheus para cache hit/miss rate
- [ ] Implementar fallback cache em memória (django.core.cache.backends.locmem)
- [ ] Configurar timeout curto no Redis para evitar bloqueios longos
- [ ] Adicionar health check específico para Redis (não-crítico)

---

**Desenvolvido:** 25/10/2025  
**Responsável:** DevOps + Backend Team  
**Status:** ✅ Implementado e Validado
