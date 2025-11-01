# 📦 Guia de Migração: zabbix_api → inventory

## Objetivo
Separar modelos de inventário (Site, Device, Port, FiberCable, FiberEvent) da app `zabbix_api` para uma nova app dedicada `inventory`, **sem alterar o schema do banco de dados**.

## Estratégia
Usar `Meta.db_table` em ambas as apps para preservar as tabelas existentes durante a transição.

---

## ✅ Passo 1: Marcar modelos antigos como "não-gerenciados" (managed=False)

Editar `zabbix_api/models.py` para adicionar `managed = False` em cada model:

```python
class Site(models.Model):
    # ... campos existentes ...
    
    class Meta:
        ordering = ["name"]
        managed = False  # ← ADICIONAR ESTA LINHA
        db_table = "zabbix_api_site"  # ← ADICIONAR ESTA LINHA
```

Repetir para: `Device`, `Port`, `FiberCable`, `FiberEvent`

**Importante:** Adicione `db_table` com o nome atual da tabela para todos os modelos.

---

## ✅ Passo 2: Criar migração fake para zabbix_api

```powershell
python manage.py makemigrations zabbix_api --name unmanage_inventory_models
```

Esta migração dirá ao Django que os modelos agora são `managed=False`.

Aplique com:
```powershell
python manage.py migrate zabbix_api
```

---

## ✅ Passo 3: Criar migração inicial para inventory

```powershell
python manage.py makemigrations inventory --name initial_from_existing_tables
```

Esta migração criará a estrutura de modelos da app `inventory` apontando para as **mesmas tabelas**.

---

## ✅ Passo 4: Aplicar migração fake do inventory

Como as tabelas já existem, aplicamos a migração como "fake":

```powershell
python manage.py migrate inventory --fake-initial
```

Isso registra que a app `inventory` agora gerencia essas tabelas **sem tentar recriá-las**.

---

## ✅ Passo 5: Atualizar imports no código

Substitua todos os imports:

**Antes:**
```python
from zabbix_api.models import Site, Device, Port, FiberCable, FiberEvent
```

**Depois:**
```python
from inventory.models import Site, Device, Port, FiberCable, FiberEvent
```

### Arquivos a verificar:
- `zabbix_api/inventory.py`
- `zabbix_api/inventory_fibers.py`
- `zabbix_api/views.py`
- `zabbix_api/admin.py` (se existir registro desses models)
- `maps_view/views.py`
- `maps_view/services_old/` (se usar esses modelos)
- `routes_builder/views.py`
- Qualquer teste que importe esses modelos

---

## ✅ Passo 6: Remover modelos antigos de zabbix_api

Após confirmar que tudo funciona, **delete** as definições dos modelos de `zabbix_api/models.py`:

```python
# REMOVER completamente as classes:
# - Site
# - Device
# - Port
# - FiberCable
# - FiberEvent
```

Crie uma migração para refletir isso:

```powershell
python manage.py makemigrations zabbix_api --name remove_inventory_models
python manage.py migrate zabbix_api
```

---

## ✅ Passo 7: Testes de validação

Execute os testes para garantir que nada quebrou:

```powershell
# Testes unitários
python manage.py test

# Verificar que as tabelas ainda existem
python manage.py dbshell
```

No shell do banco:
```sql
SHOW TABLES LIKE 'zabbix_api_%';
```

Deve listar:
- zabbix_api_site
- zabbix_api_device
- zabbix_api_port
- zabbix_api_fibercable
- zabbix_api_fiberevent

---

## 🔍 Verificação de integridade

### Comando para encontrar todos os imports:

```powershell
# Windows PowerShell
Get-ChildItem -Recurse -Include *.py | Select-String "from zabbix_api.models import.*Site|Device|Port|FiberCable|FiberEvent" | Select-Object Path, LineNumber, Line
```

### Comando alternativo com grep (Git Bash/WSL):

```bash
grep -rn "from zabbix_api.models import.*\(Site\|Device\|Port\|FiberCable\|FiberEvent\)" --include="*.py" .
```

---

## 📊 Resumo da migração

| Etapa | Comando | Efeito |
|-------|---------|--------|
| 1 | Editar `zabbix_api/models.py` | Adiciona `managed=False` e `db_table` |
| 2 | `makemigrations zabbix_api` | Cria migração indicando mudança de gerenciamento |
| 3 | `migrate zabbix_api` | Aplica mudança (sem alterar DB) |
| 4 | `makemigrations inventory` | Cria migração inicial do inventory |
| 5 | `migrate inventory --fake-initial` | Registra inventory como gerenciador sem recriar tabelas |
| 6 | Atualizar imports | Mudar código para usar `inventory.models` |
| 7 | Deletar modelos de `zabbix_api/models.py` | Limpeza final |
| 8 | `makemigrations/migrate zabbix_api` | Registra remoção dos modelos |

---

## ⚠️ Avisos importantes

1. **Backup do banco de dados antes de começar!**
2. **Não execute `migrate` sem `--fake-initial` no passo 5**
3. **As tabelas NÃO serão alteradas em nenhum momento**
4. **ForeignKeys entre apps:** Se algum modelo em `zabbix_api` referenciar `Site`, `Device`, etc., atualize para:
   ```python
   # Antes
   site = models.ForeignKey('zabbix_api.Site', ...)
   
   # Depois
   site = models.ForeignKey('inventory.Site', ...)
   ```

---

## 🎯 Resultado esperado

- ✅ App `inventory` gerencia os 5 modelos de inventário
- ✅ Tabelas do banco preservadas sem alterações
- ✅ Admin, views, e código funcionando normalmente
- ✅ App `zabbix_api` focada apenas em integração com Zabbix API
- ✅ Código mais organizado e manutenível
