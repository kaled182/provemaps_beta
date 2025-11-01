# Configuração Persistente - Guia de Uso

## 📋 Visão Geral

O sistema agora salva as configurações do Zabbix e Google Maps **diretamente no banco de dados**, garantindo que elas persistam após reiniciar os containers Docker.

## ✅ Como Funciona

### 1. **Prioridade de Configurações**

O sistema busca configurações na seguinte ordem:

1. **Variáveis de ambiente** (docker-compose.yml ou .env)
2. **Banco de dados** (tabela `setup_app_firsttimesetup`)
3. **Valores default** (vazios)

### 2. **Primeiro Acesso**

Na primeira vez que você acessar o sistema:

1. Acesse: http://localhost:8000/setup_app/config/
2. Preencha o formulário com suas configurações:
   - **Zabbix API URL**: Ex: `http://seu-servidor-zabbix:8080/api_jsonrpc.php`
   - **Zabbix User** ou **Zabbix API Key**
   - **Zabbix Password** (se usar usuário/senha)
   - **Google Maps API Key**
3. Clique em **"Save"**
4. As configurações são salvas no banco de dados **imediatamente**
5. **Não precisa reiniciar** - as mudanças são aplicadas instantaneamente

### 3. **Após Reiniciar**

Quando você reiniciar os containers (`docker-compose restart`):

- ✅ As configurações do banco de dados são carregadas automaticamente
- ✅ O mapa e a API do Zabbix funcionam com os dados salvos
- ✅ Não precisa preencher novamente

## 🔧 Arquivos Modificados

### Novos Arquivos

1. **`setup_app/services/config_loader.py`**
   - Carrega configurações do banco de dados
   - Cache de 5 minutos para performance
   - SQL direto para evitar import circular

2. **`setup_app/runtime_settings.py`** (já existia, documentado)
   - Wrapper para acessar configurações com fallback
   - Integrado com Django settings

### Arquivos Alterados

1. **`setup_app/views.py`** - função `manage_environment()`
   - Agora salva em 2 lugares:
     - Arquivo `.env` (para desenvolvimento local)
     - Banco de dados `FirstTimeSetup` (para Docker/produção)
   - Limpa cache após salvar
   - Mensagem de sucesso atualizada: "Configuration saved successfully. Changes are now active!"

2. **`docker-entrypoint.sh`**
   - Adicionado default para `INIT_ENSURE_SUPERUSER=${INIT_ENSURE_SUPERUSER:-false}`
   - Corrigido erro de "unbound variable"

## 📊 Estrutura do Banco

### Tabela: `setup_app_firsttimesetup`

```sql
CREATE TABLE setup_app_firsttimesetup (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255),
    logo VARCHAR(100) NULL,
    zabbix_url VARCHAR(255),
    auth_type VARCHAR(10),  -- 'token' ou 'login'
    zabbix_api_key VARCHAR(512) NULL,  -- criptografado
    zabbix_user VARCHAR(512) NULL,     -- criptografado
    zabbix_password VARCHAR(512) NULL, -- criptografado
    maps_api_key VARCHAR(512) NULL,    -- criptografado
    unique_licence VARCHAR(512) NULL,
    configured BOOLEAN DEFAULT FALSE,
    configured_at DATETIME
);
```

## 🔐 Segurança

- ✅ Senhas e chaves API são criptografadas com Fernet (campo `EncryptedCharField`)
- ✅ Cache de configuração por 5 minutos (reduz queries ao banco)
- ✅ Fallback seguro para variáveis de ambiente

## 🧪 Testes

### Verificar se há configurações salvas:

```bash
docker exec mapsprovefiber-web-1 python manage.py shell -c \
  "from setup_app.models import FirstTimeSetup; \
   config = FirstTimeSetup.objects.filter(configured=True).first(); \
   print(f'Zabbix URL: {config.zabbix_url}' if config else 'Nenhuma configuração')"
```

### Verificar configuração em runtime:

```bash
docker exec mapsprovefiber-web-1 python manage.py shell -c \
  "from setup_app.services import runtime_settings; \
   config = runtime_settings.get_runtime_config(); \
   print(f'Zabbix: {config.zabbix_api_url}')"
```

### Limpar cache manualmente:

```bash
docker exec mapsprovefiber-web-1 python manage.py shell -c \
  "from setup_app.services import runtime_settings; \
   runtime_settings.reload_config(); \
   print('Cache limpo!')"
```

## 🚀 Uso Diário

### Alterar Configurações

1. Acesse http://localhost:8000/setup_app/config/
2. Faça as mudanças desejadas
3. Clique em "Save"
4. **Pronto!** Não precisa reiniciar

### Deploy em Produção

As configurações são **persistentes no banco de dados**. Ao fazer deploy:

1. Faça backup do banco de dados MariaDB
2. As configurações vão junto com o backup
3. Restaure o banco na nova instância
4. As configurações estarão disponíveis automaticamente

## 📝 Notas

- O cache é limpo automaticamente após salvar configurações
- O token do Zabbix é invalidado ao alterar credenciais
- A flag de diagnósticos também é recarregada
- Sistema compatível com Docker e desenvolvimento local

## ⚠️ Troubleshooting

### Configurações não aparecem após reiniciar

```bash
# 1. Verificar se foram salvas no banco
docker exec mapsprovefiber-web-1 python manage.py shell -c \
  "from setup_app.models import FirstTimeSetup; print(FirstTimeSetup.objects.all().count())"

# 2. Se retornar 0, preencha novamente em /setup_app/config/
```

### Cache não está sendo limpo

```bash
# Limpar manualmente
docker exec mapsprovefiber-web-1 python manage.py shell -c \
  "from django.core.cache import cache; cache.clear(); print('Cache Redis limpo')"
```

### Mapa não carrega após configurar

```bash
# 1. Verificar logs
docker logs mapsprovefiber-web-1 --tail 50

# 2. Testar conexão com Zabbix
docker exec mapsprovefiber-web-1 python manage.py shell -c \
  "from zabbix_api.services.zabbix_client import ZabbixClient; \
   client = ZabbixClient(); \
   result = client.login(); \
   print(f'Login OK: {bool(result)}')"
```

## 🎯 Próximos Passos

Agora você pode:

1. ✅ Preencher as configurações em http://localhost:8000/setup_app/config/
2. ✅ Acessar o mapa em http://localhost:8000/maps_view/dashboard/
3. ✅ As configurações vão persistir após `docker-compose restart`
4. ✅ Não precisa editar docker-compose.yml manualmente

---

**Status**: ✅ Sistema pronto para uso!

## 🔄 Automa��o de rein�cio de servi�os

- Utilize `SERVICE_RESTART_COMMANDS` para executar comandos imediatos ap�s salvar credenciais pelo painel ou via `sync_env_from_setup`.
- Inclua todos os servi�os relevantes (por exemplo: web, celery, beat) na mesma linha separados por ponto e v�rgula.
- Em ambientes Docker, defina no `.env`:

  ```
  SERVICE_RESTART_COMMANDS="docker compose restart web; docker compose restart celery; docker compose restart beat"
  ```

- Para systemd/supervisord, liste os comandos equivalentes, por exemplo:

  ```
  SERVICE_RESTART_COMMANDS="systemctl restart mapsprovefiber-web; systemctl restart mapsprovefiber-worker; systemctl restart mapsprovefiber-beat"
  ```

- O campo aparece em **Setup → Manage Environment** e aceita m�ltiplos comandos separados por `;`. Falhas de execu��o s�o registradas nos logs do aplicativo.

