> **📜 Histórico — arquivado em 2026-10-04 (EV-0021).** Este documento descreve um
> estado do projeto que já não existe (app `zabbix_api`, banco MariaDB/MySQL,
> sprints e fases de 2025, caminhos Windows). Fica pelo valor histórico; **não o
> uses como guia**. A fonte atual é [`CLAUDE.md`](../../../CLAUDE.md) (§3–4, §9),
> [`DEPLOY.md`](../../../DEPLOY.md) e [`doc/architecture/DATA_FLOW.md`](../../architecture/DATA_FLOW.md).

# 🚀 Como Criar o Pull Request

## Opção 1: Via GitHub Web Interface (Recomendado)

1. **Acesse o repositório no GitHub:**
   https://github.com/kaled182/provemaps_beta

2. **Clique em "Pull requests" → "New pull request"**

3. **Configure as branches:**
   - **Base:** `inicial`
   - **Compare:** `refactor/modularization`

4. **Preencha o título:**
   ```
   🚀 Phase 5 Complete: Django Modularization & Technical Hygiene [v2.0]
   ```

5. **Copie e cole o conteúdo de `doc/reports/pr/PR_PHASE5_COMPLETE.md` na descrição**

6. **Adicione labels (se disponível):**
   - `breaking-change`
   - `documentation`
   - `enhancement`
   - `refactoring`

7. **Solicite revisores** (se houver equipe)

8. **Clique em "Create pull request"**

---

## Opção 2: Via GitHub CLI (Se instalar)

### Instalar GitHub CLI:
```bash
# https://cli.github.com (apt / dnf / brew / winget)
```

### Criar PR:
```bash
gh pr create --base inicial --head refactor/modularization --title "🚀 Phase 5 Complete: Django Modularization & Technical Hygiene [v2.0]" --body-file doc/reports/pr/PR_PHASE5_COMPLETE.md
```

---

## Opção 3: Link Direto

Acesse diretamente este link (substitua os branches se necessário):

```
https://github.com/kaled182/provemaps_beta/compare/inicial...refactor/modularization?expand=1
```

---

## ✅ Checklist Pós-Criação

Depois de criar o PR, certifique-se de:

- [ ] Título claro e descritivo
- [ ] Descrição completa com breaking changes
- [ ] Labels apropriadas adicionadas
- [ ] Revisores solicitados (se aplicável)
- [ ] CI/CD passando (se configurado)
- [ ] Self-review completo

---

## 📋 Resumo do PR

**Branch origem:** `refactor/modularization`  
**Branch destino:** `inicial`  
**Tipo:** Breaking change + Documentação + Refatoração  
**Status:** Pronto para merge  
**Testes:** 199/199 passando ✅

### Arquivos Modificados: 17
- 7 arquivos novos
- 10 arquivos modificados
- +2,760 inserções
- -669 deleções

### Breaking Changes: 5 principais
1. Endpoints de API movidos
2. Estrutura de apps reorganizada
3. Migration chain modificada
4. Settings atualizadas
5. Static files com cache busting

---

## 🔗 Documentação Relacionada

- `README.md` - Guia principal (reescrito)
- `doc/archive/2025-historico/REFATORAR.md` - Estado atual (Fases 0-5) (histórico)
- `doc/developer/FUTURE_APPS.md` - Roadmap futuro (Fases 6-15)
- `doc/reports/pr/PR_PHASE5_COMPLETE.md` - Corpo completo do PR pronto para uso
- `scripts/smoke_phase5.ps1` - Smoke tests automatizados

---

**Pronto para continuar?** 🚀
