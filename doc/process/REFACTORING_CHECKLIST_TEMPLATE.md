# Template: Checklist de Refatoração

**Componente**: _______________  
**Responsável**: _______________  
**Data Início**: _______________  
**Data Fim**: _______________

---

## ✅ Pré-Refatoração

### Preparação
- [ ] Branch criada: `refactor/_______________`
- [ ] Backup do código original: `_______________.backup`
- [ ] Análise de dependências feita
- [ ] Testes existentes rodando (se houver)
- [ ] Equipe comunicada sobre refatoração

### Análise
- [ ] Responsabilidades identificadas (listar):
  - 1. _______________
  - 2. _______________
  - 3. _______________
- [ ] Dependências mapeadas
- [ ] Tamanho atual: _______ linhas
- [ ] Meta de tamanho: _______ linhas

---

## 🔨 Durante Refatoração

### Composables Criados
- [ ] `_______________` - _______ linhas
  - [ ] Testes unitários escritos
  - [ ] Coverage > 80%
  - [ ] Documentado

- [ ] `_______________` - _______ linhas
  - [ ] Testes unitários escritos
  - [ ] Coverage > 80%
  - [ ] Documentado

### Sub-componentes Criados
- [ ] `_______________` - _______ linhas
  - [ ] Props documentados
  - [ ] Emits documentados
  - [ ] Testes de componente escritos

- [ ] `_______________` - _______ linhas
  - [ ] Props documentados
  - [ ] Emits documentados
  - [ ] Testes de componente escritos

### Integração
- [ ] Componente principal refatorado
- [ ] Imports atualizados
- [ ] Props/emits mantidos (compatibilidade)
- [ ] Código morto removido

---

## 🧪 Testes

### Testes Unitários (Composables)
- [ ] `_______________` - ✅ PASS
- [ ] `_______________` - ✅ PASS
- [ ] Coverage geral: _____%

### Testes de Componente
- [ ] `_______________` - ✅ PASS
- [ ] `_______________` - ✅ PASS

### Testes E2E
- [ ] Cenário 1: _______________  - ✅ PASS
- [ ] Cenário 2: _______________  - ✅ PASS
- [ ] Cenário 3: _______________  - ✅ PASS

### Testes de Regressão
- [ ] Funcionalidade A: _______________  - ✅ SEM REGRESSÃO
- [ ] Funcionalidade B: _______________  - ✅ SEM REGRESSÃO
- [ ] Funcionalidade C: _______________  - ✅ SEM REGRESSÃO

### Testes Manuais
- [ ] Teste em desenvolvimento
- [ ] Teste em staging
- [ ] Teste em diferentes navegadores (Chrome, Firefox, Safari)
- [ ] Teste em mobile

---

## 📊 Performance

### Métricas
| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Linhas de código | _____ | _____ | ____% |
| Tempo de renderização | _____ms | _____ms | ____% |
| Tamanho do bundle | _____KB | _____KB | ____% |
| Lighthouse Performance | _____ | _____ | ____pts |

### Lighthouse Report
- [ ] Performance > 90
- [ ] Accessibility > 90
- [ ] Best Practices > 90
- [ ] SEO > 90

---

## 📝 Code Review

### Revisores
- [ ] Revisor 1: _______________ - ✅ APROVADO
- [ ] Revisor 2: _______________ - ✅ APROVADO

### Pontos Verificados
- [ ] Código segue padrões do projeto
- [ ] Nomes de variáveis/funções claros
- [ ] Comentários onde necessário
- [ ] Sem código duplicado
- [ ] Sem console.logs desnecessários
- [ ] Tratamento de erros adequado

### Feedback Aplicado
- Feedback 1: _______________
  - [ ] Aplicado
- Feedback 2: _______________
  - [ ] Aplicado

---

## 📚 Documentação

- [ ] README atualizado (se necessário)
- [ ] JSDoc nos composables
- [ ] Props/Emits documentados
- [ ] Exemplos de uso adicionados
- [ ] Changelog atualizado

---

## 🚀 Deploy

### Staging
- [ ] Build sem erros
- [ ] Deploy em staging
- [ ] Testes em staging - ✅ PASS
- [ ] Monitoramento 24h - ✅ OK

### Produção
- [ ] Aprovação final
- [ ] Deploy em produção
- [ ] Feature flag ativada (se aplicável)
- [ ] Monitoramento 48h
- [ ] Rollback plan documentado

---

## ✅ Pós-Refatoração

### Validação Final
- [ ] Zero bugs críticos
- [ ] Zero regressões
- [ ] Performance igual ou melhor
- [ ] Feedback positivo da equipe
- [ ] Métricas de sucesso atingidas

### Limpeza
- [ ] Código antigo removido (se aplicável)
- [ ] Feature flags removidas (após estabilização)
- [ ] Arquivos `.backup` documentados
- [ ] Branch mergeada e arquivada

### Retrospectiva
- [ ] Reunião de retrospectiva agendada
- [ ] O que funcionou bem:
  - _______________
  - _______________
- [ ] O que pode melhorar:
  - _______________
  - _______________
- [ ] Lições aprendidas documentadas

---

## 📋 Notas

**Problemas Encontrados**:
- _______________
- _______________

**Soluções Aplicadas**:
- _______________
- _______________

**Observações**:
- _______________
- _______________

---

**Status Final**: ⬜ Em Andamento | ⬜ Concluído | ⬜ Pausado | ⬜ Cancelado

**Assinatura**:  
Desenvolvedor: _______________ Data: ___/___/___  
Revisor: _______________ Data: ___/___/___  
Tech Lead: _______________ Data: ___/___/___
