# Arquivos .backup - Arquivados

**Data de Arquivamento:** 2026-02-03  
**Sprint:** Sprint 1, Week 1  
**Motivo:** Limpeza de código - arquivos backup não devem estar versionados

---

## Arquivos Arquivados

### 1. SiteDetailsModal.vue.backup
**Original:** `frontend/src/components/SiteDetailsModal.vue`  
**Data de Criação:** Estimada ~Nov-Dez 2025  
**Razão do Backup:** Provavelmente refatoração do modal de detalhes de sites

### 2. ConfigurationPage.vue.backup
**Original:** `frontend/src/views/ConfigurationPage.vue`  
**Data de Criação:** Estimada ~Nov-Dez 2025  
**Razão do Backup:** Refatoração da página de configuração

### 3. FiberRouteEditor.vue.backup
**Original:** `frontend/src/features/networkDesign/FiberRouteEditor.vue`  
**Data de Criação:** Estimada ~Nov-Dez 2025  
**Razão do Backup:** Implementação de dark mode (conforme histórico recente)

---

## ⚠️ Política de Arquivos Backup

**Não versionar arquivos .backup no Git:**
- Use Git para controle de versão (branches, commits, tags)
- Backups manuais devem ficar em diretórios locais não versionados
- Se necessário manter histórico, use `git stash` ou branches

**Recomendação:**
```bash
# Adicionar ao .gitignore:
*.backup
*.bak
*.old
```

---

## 🗑️ Cronograma de Remoção

- **Arquivamento:** 2026-02-03 (Sprint 1, Week 1)
- **Revisão:** 2026-03-03 (30 dias após arquivamento)
- **Remoção Definitiva:** 2026-04-03 (60 dias se não houver necessidade)

---

## 📋 Histórico de Mudanças

### 2026-02-03
- ✅ Movido `SiteDetailsModal.vue.backup` de `frontend/src/components/`
- ✅ Movido `ConfigurationPage.vue.backup` de `frontend/src/views/`
- ✅ Movido `FiberRouteEditor.vue.backup` de `frontend/src/features/networkDesign/`
- ✅ Criado este README

---

**Status:** 📦 Arquivado (aguardando revisão em 30 dias)
