# Fase 1 – Preparação e Diagnóstico de Desempenho

Esta primeira etapa tem como objetivo levantar uma linha de base confiável antes de aplicarmos mudanças mais invasivas. Todos os passos abaixo podem ser executados no ambiente atual (SQLite) e repetidos após a migração para validar os ganhos.

## 1. Linha de base dos endpoints

1. Garanta que exista um usuário com acesso aos endpoints (ex.: `staff`).
2. Execute o comando de profiling recém-criado:

   ```bash
   python manage.py profile_endpoints --username=<USER> --password=<PASS> --runs=5
   ```

   O comando exercita as rotas críticas (`/zabbix_api/api/fibers/`, `/zabbix_api/api/sites/`, `/zabbix_api/api/device-ports/<id>/`, etc.) e imprime a média, p95 e tempo máximo em milissegundos. Use esse resultado como referência para comparar depois da migração/cache.

3. Caso queira mais detalhes, habilite temporariamente o log de tempo das requisições Django, adicionando ao `settings.py`:

   ```python
   LOGGING["loggers"]["django.request"] = {
       "handlers": ["console"],
       "level": "INFO",
   }
   ```

   Ou utilize ferramentas de carga (Locust, k6) apontando para os endpoints REST e registrando throughput/latência.

## 2. Instrumentação das chamadas ao Zabbix

Agora toda chamada `zabbix_request` é logada com duração e status (`DEBUG`). Para coletar o volume real:

1. No `LOGGING` do Django, habilite o namespace `zabbix_api.services.zabbix_service` em nível `DEBUG` durante o período de medição:

   ```python
   LOGGING["loggers"]["zabbix_api.services.zabbix_service"] = {
       "handlers": ["console"],
       "level": "DEBUG",
   }
   ```

2. Rode o sistema normalmente (ou o comando de profiling acima) e observe no console a quantidade de chamadas, duração média, presença de retries, etc. Esse log servirá para validar se as futuras otimizações (batch requests, cache) reduzem o número e o tempo dessas chamadas.

## 3. Consumo de CPU/IO do banco atual

Mesmo em SQLite é possível monitorar o impacto das consultas:

- Ative a saída de queries lentas pelo Django adicionando:

  ```python
  LOGGING["loggers"]["django.db.backends"] = {
      "handlers": ["console"],
      "level": "DEBUG",
  }
  ```

  Isso imprime cada SQL executado com a duração estimada (útil para identificar N+1 ou consultas custosas).

- Utilize ferramentas do sistema operacional (Task Manager, `Get-Process`, `perfmon`) para observar uso de CPU/IO enquanto os testes rodam.

- Para ambientes Linux, `iotop` e `htop` ajudam a visualizar gargalos.

Essas evidências indicarão quão limitado o SQLite está e quais tabelas consultamos com mais frequência.

## 4. Mapeamento da infraestrutura atual e planejamento da migração

- Confirmamos que o projeto utiliza SQLite (`django.db.backends.sqlite3`) e o arquivo `db.sqlite3` fica em `C:\Users\Paulo Adriano\Downloads\django-maps-prove-master-fixed\db.sqlite3`. Esse formato não suporta bem múltiplos processos nem carga concorrente.

- Levante onde mais o projeto roda (staging/prod). Se também usa SQLite, será necessário agendar downtime para migração.

- Defina o alvo: MySQL 8.x ou MariaDB 10.x são recomendados pelo ecossistema Zabbix, mas PostgreSQL também é suportado pelo Django. Verifique com a equipe de infra quais opções de hospedagem/backup existem.

- Valide drivers/libraries no Django:
  * MySQL/MariaDB: `mysqlclient` (mais performático) ou `PyMySQL`.
  * PostgreSQL: `psycopg2`.
  * Garanta que as dependências sejam incluídas no `requirements.txt`.

- Esboce o plano de migração:
  1. Criar database vazio no alvo (`utf8mb4` no MySQL).
  2. Atualizar `settings.DATABASES` (manter `CONN_MAX_AGE` padrão por ora).
  3. Executar `python manage.py migrate`.
  4. Carregar dados via `dumpdata/loaddata` ou ferramentas nativas (por exemplo, `sqlite3 db.sqlite3 .dump` + `mysql`).
  5. Testar bateria de comandos (`profile_endpoints`, testes automatizados).

## 5. Próximos passos após a Fase 1

Com as métricas iniciais em mãos:

- Documente os resultados (guardar logs do profiling e do logger de Zabbix).
- Use essas métricas como baseline para a Fase 2 (migração do banco/índices).
- Assim que MySQL estiver operacional, repita o comando `profile_endpoints` e compare.

Esse checklist garante visibilidade sobre o estado atual antes de qualquer alteração estrutural, ajudando a medir os ganhos reais das fases seguintes.
