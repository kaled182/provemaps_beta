# Fase 6 – Observabilidade e Monitoramento

## 1. Métricas Prometheus
- Instalado django-prometheus e adicionado a INSTALLED_APPS / MIDDLEWARE.
- Nova rota GET /metrics/ (via core/urls.py) expõe métricas padrão do Django, Redis e MariaDB.
- Exemplo rápido:
  `ash
  curl http://localhost:8000/metrics/ | head
  `
  Integre esse endpoint ao Prometheus/Grafana para dashboards de latência, cache hits e uso de tarefas Celery.

## 2. Logging estruturado
- Diretório logs/ criado automaticamente; RotatingFileHandler grava pplication.log (5 MB + 5 backups).
- Loggers principais (django, celery, zabbix_api, etc.) enviam para console e arquivo.
- Consultar em tempo real: 	ail -f logs/application.log.

## 3. Slow Query Inspector
- Novo comando: python manage.py show_slow_queries --path "C:\Program Files\MariaDB 12.0\data\<host>-slow.log" --limit 10
- Pode omitir --path se MYSQL_SLOW_LOG_PATH estiver definido.
- Saída inclui Query_time, Lock_time, linhas examinadas e o SQL completo para análise/EXPLAIN.

## 4. Próximos passos sugeridos
- Conectar /metrics/ a um Prometheus/Grafana e definir alertas (latência alta, worker inativo, crescimento do log).
- Automatizar coleta do slow-log (cron + show_slow_queries ou parsing via Promtail/Loki).
- Avaliar integração com APM (Sentry, New Relic) para rastreamento de requisições Celery + HTTP.
