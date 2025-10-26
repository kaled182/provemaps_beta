# 📦 Legacy Code Archive

Este diretório contém código legado que foi removido do projeto principal para melhorar a manutenibilidade, reduzir confusão e manter uma base de código limpa e organizada.

---

## 📅 Histórico de Arquivamento

### **Primeira Movimentação: 26 de Outubro de 2025**
Arquivos `*_old.py` movidos das apps principais para evitar confusão sobre qual código utilizar.

### **Verificação de Segurança: 26 de Outubro de 2025**
Confirmado que todos os arquivos legados não possuem imports ativos no código de produção.

---

## 📁 Estrutura Atual

```
legacy_backup/
├── README.md (este arquivo)
├── maps_view/
│   ├── models_old.py          # Models antigos com managed=False
│   ├── views_old.py            # Views anteriores à refatoração
│   ├── urls_old.py             # URLconf antiga
│   └── services_old/
│       └── fiber_status.py     # Lógica de status de fibra (substituída por zabbix_api/services/)
└── routes_builder/
    ├── views_old.py            # Views antigas de construção de rotas
    └── urls_old.py             # URLconf antiga
```

---

## 🔍 Detalhes dos Arquivos Arquivados

### **maps_view/**

#### `models_old.py`
- **Substituído por:** `maps_view/models.py` (modelos refatorados)
- **Motivo:** Modelos com `managed=False` que não são mais utilizados
- **Última referência:** Nenhuma import ativa encontrada
- **Status:** ⚠️ Mantido para referência histórica apenas

#### `views_old.py`
- **Substituído por:** `maps_view/views.py`
- **Motivo:** Refatoração completa da lógica de views
- **Importava de:** `zabbix_api.services.fiber_status` (código legacy)
- **Última referência:** Apenas em `legacy_backup/`
- **Status:** ⚠️ Código desatualizado, não utilizar

#### `urls_old.py`
- **Substituído por:** `maps_view/urls.py`
- **Motivo:** Reestruturação de rotas
- **Status:** ⚠️ Padrões de URL desatualizados

#### `services_old/fiber_status.py`
- **Substituído por:** `zabbix_api/services/fiber_status.py`
- **Motivo:** Lógica movida para localização mais apropriada na arquitetura
- **Status:** ⚠️ Código duplicado, usar a versão em `zabbix_api/`

---

### **routes_builder/**

#### `views_old.py`
- **Substituído por:** `routes_builder/views.py`
- **Motivo:** Refatoração da lógica de construção de rotas
- **Importava de:** `zabbix_api.services.zabbix_service`
- **Status:** ⚠️ Código desatualizado

#### `urls_old.py`
- **Substituído por:** `routes_builder/urls.py`
- **Motivo:** Reorganização de endpoints
- **Status:** ⚠️ Padrões de URL desatualizados

---

## ✅ Verificações de Segurança Realizadas

### **Análise de Imports (26/10/2025)**

```bash
# Busca por imports ativos aos arquivos legados
grep -r "from.*_old" --include="*.py" --exclude-dir=legacy_backup
grep -r "import.*_old" --include="*.py" --exclude-dir=legacy_backup
```

**Resultado:** ✅ Nenhum import ativo encontrado fora de `legacy_backup/`

### **Referências em Código Ativo**

| Arquivo Legacy | Imports Ativos | Status |
|----------------|----------------|--------|
| `maps_view/views_old.py` | 0 | ✅ Seguro |
| `maps_view/urls_old.py` | 0 | ✅ Seguro |
| `maps_view/models_old.py` | 0 | ✅ Seguro |
| `services_old/fiber_status.py` | 0 | ✅ Seguro |
| `routes_builder/views_old.py` | 0 | ✅ Seguro |
| `routes_builder/urls_old.py` | 0 | ✅ Seguro |

### **Menções em Documentação**

- ✅ `AGENTS.md` - Menciona existência de arquivos `*_old.py` (precisa atualizar)
- ✅ `.github/copilot-instructions.md` - Menciona preferir arquivos principais sobre `*_old.py`

---

## 🔧 Código Ativo Correto (Usar Estes!)

### **Para Integração com Zabbix:**
```python
# ✅ CORRETO - Usar esta importação
from zabbix_api.services.zabbix_service import zabbix_request, clear_token_cache
from zabbix_api.services.fiber_status import fetch_interface_status_advanced

# ❌ ERRADO - Não usar
from zabbix_api.services.zabbix_client import ...  # Legacy, não importar diretamente
from legacy_backup.maps_view.services_old.fiber_status import ...  # Código duplicado
```

### **Para Views de Mapas:**
```python
# ✅ CORRETO
from maps_view.views import (
    index, network_map, device_map, host_fiber_status, 
    cable_events, sites_list, devices_list
)

# ❌ ERRADO
from maps_view.views_old import ...  # Não existe mais no código ativo
```

### **Para Construção de Rotas:**
```python
# ✅ CORRETO
from routes_builder.views import (
    route_map, fiber_route_builder, get_fibers,
    create_fiber, update_fiber
)

# ❌ ERRADO
from routes_builder.views_old import ...  # Não existe mais no código ativo
```

---

## 🚨 Avisos Importantes

### ⚠️ **NÃO UTILIZAR CÓDIGO LEGACY EM PRODUÇÃO**

Os arquivos neste diretório são mantidos **apenas para referência histórica**. Eles:

- ❌ Não são testados
- ❌ Podem conter bugs corrigidos nas versões atuais
- ❌ Não seguem a arquitetura atual do projeto
- ❌ Não recebem atualizações de segurança
- ❌ Podem causar conflitos com código ativo

### ⚠️ **Imports Circulares e Conflitos**

Se você mover arquivos de volta para as pastas principais:
- Podem ocorrer imports circulares
- Duplicação de lógica com código ativo
- Confusão sobre qual versão utilizar

---

## 🔄 Como Restaurar (Apenas para Referência)

Se você precisar **consultar** (não usar em produção) algum arquivo:

### **Opção 1: Consultar Arquivo Específico**
```powershell
# Windows PowerShell
Get-Content legacy_backup\maps_view\views_old.py | Select-String "função_especifica"
```

### **Opção 2: Comparar com Versão Atual**
```powershell
# Comparar versões old vs atual
code --diff legacy_backup\maps_view\views_old.py maps_view\views.py
```

### **⚠️ Restauração Completa (NÃO RECOMENDADO)**
```powershell
# ⚠️ CUIDADO: Pode quebrar a aplicação!
Copy-Item legacy_backup\maps_view\views_old.py maps_view\

# Após copiar, você DEVE:
# 1. Renomear imports no código que o utiliza
# 2. Resolver conflitos com código atual
# 3. Executar todos os testes
# 4. Verificar se não há duplicação de lógica
```

---

## 📚 Documentação Relacionada

- **AGENTS.md** - Guia de desenvolvimento (menciona arquivos legacy)
- **.github/copilot-instructions.md** - Instruções de preferência de código
- **zabbix_api/services/** - Localização correta dos services refatorados
- **CHANGELOG_*.md** - Histórico de mudanças no projeto

---

## 🗑️ Plano de Remoção Definitiva

### **Critérios para Deleção:**
1. ✅ Código ativo funcionando sem problemas por 30+ dias
2. ✅ Nenhum import ativo encontrado
3. ✅ Todos os testes passando
4. ✅ Documentação atualizada
5. ✅ Equipe ciente das mudanças

### **Próximos Passos:**
- [ ] **30 dias após arquivamento (25/11/2025):** Revisar se arquivos são necessários
- [ ] Atualizar `AGENTS.md` removendo menções a `*_old.py`
- [ ] Atualizar `.github/copilot-instructions.md`
- [ ] **60 dias após arquivamento (25/12/2025):** Considerar remoção permanente
- [ ] Fazer commit final antes de deletar: `git add legacy_backup/ && git commit -m "chore: remove legacy backup after 60 days validation"`

---

## 🆘 Suporte e Dúvidas

Se você precisar de algum código que estava nos arquivos legacy:

1. **Primeiro:** Verifique se a funcionalidade já existe no código ativo
2. **Segundo:** Consulte este README para entender onde o código foi movido
3. **Terceiro:** Compare as versões (old vs atual) para entender as mudanças
4. **Último recurso:** Consulte o histórico do Git antes do arquivamento

---

**Última Atualização:** 26 de Outubro de 2025  
**Responsável:** Copilot Assistant  
**Status:** ✅ Arquivos seguros para remoção futura
3. Manter focus na arquitetura limpa e sem duplicação

---
**Nota**: Este backup é temporário. Se não houver necessidade de restauração em 30 dias, pode ser deletado permanentemente.
