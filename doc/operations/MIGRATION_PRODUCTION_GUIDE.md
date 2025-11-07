# Guia de Aplicação da Migração em Produção

> **Data:** 2025-11-07  
> **Objetivo:** Aplicar migração `inventory.0003_route_models_relocation` em ambiente de produção  
> **Tempo estimado:** 15-30 minutos  
> **Risco:** Baixo (migração apenas atualiza metadados, sem alteração de dados)

---

## ⚠️ Pré-requisitos OBRIGATÓRIOS

### 1. Backup do Banco de Dados

**MySQL/MariaDB:**
```bash
# Backup completo
mysqldump -u root -p mapspro_db > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Ou backup apenas das tabelas críticas
mysqldump -u root -p mapspro_db \
  routes_builder_route \
  routes_builder_routesegment \
  routes_builder_routeevent \
  django_content_type \
  django_migrations \
  > backup_route_models_$(date +%Y%m%d_%H%M%S).sql
```

**Validar backup:**
```bash
# Verificar tamanho do arquivo
ls -lh backup_*.sql

# Verificar conteúdo (primeiras linhas)
head -50 backup_*.sql
```

### 2. Verificar Estado Atual

```bash
# Conectar ao servidor de produção
ssh user@production-server

# Ativar ambiente virtual
cd /path/to/provemaps_beta
source venv/bin/activate

# Verificar migrações aplicadas
python manage.py showmigrations inventory routes_builder

# Esperado:
# inventory
#  [X] 0001_initial_from_existing_tables
#  [X] 0002_alter_port_zabbix_item_id_trafego_in_and_more
#  [ ] 0003_route_models_relocation
# routes_builder
#  [X] 0001_initial
#  [ ] 0002_move_route_models_to_inventory
```

### 3. Verificar Logs de Acesso

```bash
# Verificar se há chamadas aos endpoints legados (últimos 7 dias)
grep -E "/zabbix_api/inventory|/routes_builder/" /var/log/nginx/access.log* | wc -l

# Se houver muitas chamadas, investigar origem antes de prosseguir
```

---

## 🚀 Procedimento de Aplicação

### Passo 1: Janela de Manutenção (Opcional)

Se preferir aplicar sem risco de requisições simultâneas:

```bash
# Colocar aplicação em modo manutenção
touch /var/www/provemaps/maintenance.flag

# Ou parar servidor temporariamente
sudo systemctl stop gunicorn-provemaps
```

### Passo 2: Aplicar Migrações

```bash
# Migração do inventory (atualiza ContentTypes)
python manage.py migrate inventory 0003_route_models_relocation

# Esperado:
# Operations to perform:
#   Apply all migrations: inventory
# Running migrations:
#   Applying inventory.0003_route_models_relocation... OK

# Migração do routes_builder (fake migration, só metadados)
python manage.py migrate routes_builder 0002_move_route_models_to_inventory

# Esperado:
# Operations to perform:
#   Apply all migrations: routes_builder
# Running migrations:
#   Applying routes_builder.0002_move_route_models_to_inventory... OK
```

### Passo 3: Validar Migração

```bash
# Executar script de validação
python scripts/validate_migration_staging.py

# Esperado: todos os checks ✅

# Ou validação manual rápida
python manage.py shell
```

```python
# No shell Django:
from inventory.models import Route
from django.contrib.contenttypes.models import ContentType

# Verificar ContentType
ct = ContentType.objects.get_for_model(Route)
print(f"Route ContentType: app={ct.app_label}, model={ct.model}")
# Esperado: app=inventory, model=route

# Verificar que queries funcionam
print(f"Total de rotas: {Route.objects.count()}")

# Testar CRUD básico
test = Route.objects.create(
    name=f"TEST_PROD_VALIDATION",
    description="Teste pós-migração",
    status="planned"
)
print(f"Rota teste criada: id={test.id}")
test.delete()
print("Rota teste deletada com sucesso")

exit()
```

### Passo 4: Restaurar Serviço

```bash
# Remover flag de manutenção
rm /var/www/provemaps/maintenance.flag

# Ou reiniciar servidor
sudo systemctl start gunicorn-provemaps
sudo systemctl status gunicorn-provemaps
```

### Passo 5: Smoke Test

```bash
# Verificar health checks
curl https://seu-dominio.com/healthz
curl https://seu-dominio.com/ready

# Testar endpoint de rotas
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://seu-dominio.com/api/v1/inventory/fibers/

# Verificar dashboard
# Abrir no browser: https://seu-dominio.com/maps_view/dashboard/
```

---

## 🔄 Plano de Rollback

Se algo der errado:

### Opção 1: Reverter Migrações (Rápido)

```bash
# Reverter inventory para 0002
python manage.py migrate inventory 0002_alter_port_zabbix_item_id_trafego_in_and_more

# Reverter routes_builder para 0001
python manage.py migrate routes_builder 0001_initial
```

### Opção 2: Restaurar Backup Completo

```bash
# Parar aplicação
sudo systemctl stop gunicorn-provemaps

# Restaurar banco
mysql -u root -p mapspro_db < backup_pre_migration_YYYYMMDD_HHMMSS.sql

# Reiniciar aplicação
sudo systemctl start gunicorn-provemaps
```

---

## ✅ Checklist de Validação Pós-Migração

- [ ] Backup criado e validado
- [ ] Migrações aplicadas sem erros
- [ ] ContentTypes atualizados (app_label=inventory)
- [ ] Queries de Route funcionando
- [ ] Health checks OK
- [ ] Dashboard carregando corretamente
- [ ] Endpoints `/api/v1/inventory/*` respondendo
- [ ] Logs sem erros críticos
- [ ] Testes automatizados passando (opcional): `pytest -q`

---

## 📊 Métricas de Sucesso

- **Tempo total:** < 30 minutos
- **Downtime:** 0 minutos (ou < 5 min se usar janela de manutenção)
- **Erros:** 0
- **Queries afetadas:** 0 (migração apenas metadados)

---

## 📝 Notas Importantes

1. **Sem perda de dados:** A migração usa `SeparateDatabaseAndState`, então não altera estrutura de tabelas nem dados.

2. **ContentTypes:** A migração atualiza apenas a tabela `django_content_type`, mudando `app_label` de `routes_builder` para `inventory` para os modelos Route, RouteSegment, RouteEvent.

3. **Tabelas mantidas:** As tabelas `routes_builder_*` continuam existindo e funcionando normalmente. A única mudança é que o Django agora sabe que elas pertencem ao app `inventory`.

4. **Compatibilidade:** Shims em `routes_builder/models.py` garantem que código antigo continua funcionando.

---

## 🆘 Contatos de Emergência

- **Backend Lead:** [seu contato]
- **DBA:** [contato DBA]
- **DevOps:** [contato DevOps]

---

## 📅 Histórico de Aplicação

| Ambiente | Data | Responsável | Status | Observações |
|----------|------|-------------|--------|-------------|
| Local (SQLite) | 2025-11-07 | Paulo | ✅ OK | Validação inicial |
| Test (SQLite) | 2025-11-07 | Paulo | ✅ OK | 14/14 testes passando |
| Staging | - | - | ⏳ Pendente | - |
| Production | - | - | ⏳ Pendente | - |
