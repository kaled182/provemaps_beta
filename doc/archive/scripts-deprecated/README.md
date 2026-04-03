# Scripts Deprecados - Arquivo

**Data de arquivamento:** 2026-02-03  
**Motivo:** Sprint 1, Semana 1 - Limpeza de código legado  
**Quantidade:** 25 arquivos

## Origem

Estes scripts estavam localizados em `scripts/scripts_old/` e foram identificados como obsoletos ou duplicados durante a auditoria de código legado.

## Conteúdo Arquivado

### Diretório `scripts_old/` (25 arquivos)

Scripts de manutenção, deployment e troubleshooting antigos que foram substituídos por versões mais recentes ou tornaram-se obsoletos com mudanças na arquitetura.

**Categorias esperadas:**
- Scripts de deploy antigos
- Ferramentas de debug descontinuadas  
- Utilitários de migração já executados
- Scripts de teste manuais substituídos por testes automatizados

## Política de Retenção

- **Período de retenção:** 60 dias (até ~2026-04-04)
- **Revisão necessária:** Não (scripts claramente obsoletos)
- **Backup externo:** Mantido em Git history

## Critérios para Remoção Permanente

Após o período de retenção, estes scripts podem ser removidos permanentemente se:

1. ✅ Nenhuma referência encontrada no código ativo durante 60 dias
2. ✅ Nenhum ticket/issue mencionar necessidade destes scripts
3. ✅ Versões substitutas funcionando adequadamente em produção

## Restauração

Se necessário restaurar algum script:

```bash
# Copiar script específico de volta
cp doc/archive/scripts-deprecated/scripts_old/<script_name> scripts/

# Ou restaurar via git (se houver hash conhecido)
git show <commit_hash>:scripts/scripts_old/<script_name> > scripts/<script_name>
```

## Verificação Pré-Arquivamento

- ✅ Auditoria de referências no codebase realizada
- ✅ Diretório scripts/ principal limpo e organizado
- ✅ Scripts ativos mantidos em scripts/ raiz
- ✅ Documentação atualizada

## Contexto da Remoção

Parte do plano sistemático de remoção de código legado documentado em:
- `doc/roadmap/LEGACY_CODE_REMOVAL_SCHEDULE.md`
- `doc/reports/LEGACY_CODE_ANALYSIS_2026-02-02.md`

---

**Próxima revisão:** 2026-04-04  
**Responsável:** Equipe de DevOps
