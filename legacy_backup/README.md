# Legacy Code Backup

Este diretório contém código legado que foi removido do projeto principal para melhorar a manutenibilidade e reduzir confusão.

## Data da Remoção
**26 de Outubro de 2025**

## Arquivos Movidos

### maps_view/
- `views_old.py` - Views antigas substituídas por `views.py`
- `urls_old.py` - URLs antigas substituídas por `urls.py`
- `models_old.py` - Models antigos (managed=False) 
- `services_old/` - Services legados substituídos pela arquitetura atual

### routes_builder/
- `views_old.py` - Views antigas substituídas por `views.py`
- `urls_old.py` - URLs antigas substituídas por `urls.py`

## Motivo da Remoção

1. **Redução de Confusão**: Arquivos `*_old.py` causavam confusão sobre qual código usar
2. **Manutenibilidade**: Código duplicado dificulta manutenção e debugging
3. **Código Limpo**: Nenhum import ativo estava referenciando estes arquivos
4. **Arquitetura Clara**: Facilita entendimento da estrutura do projeto

## Verificações Realizadas

- ✅ Nenhum import ativo encontrado nos arquivos do projeto
- ✅ Apenas mencionados em documentação (AGENTS.md, copilot-instructions.md)
- ✅ Backup completo criado antes da remoção
- ✅ Teste de funcionamento após remoção

## Como Restaurar (se necessário)

Se por algum motivo você precisar restaurar algum arquivo:

```bash
# Para restaurar um arquivo específico
Copy-Item legacy_backup\maps_view\views_old.py maps_view\

# Para restaurar todos os arquivos do maps_view
Copy-Item legacy_backup\maps_view\* maps_view\ -Recurse
```

## Próximos Passos

Após confirmar que tudo funciona sem os arquivos legacy:
1. Atualizar documentação (AGENTS.md, copilot-instructions.md) removendo menções aos arquivos old
2. Após 30 dias sem problemas, considerar deletar este backup
3. Manter focus na arquitetura limpa e sem duplicação

---
**Nota**: Este backup é temporário. Se não houver necessidade de restauração em 30 dias, pode ser deletado permanentemente.
