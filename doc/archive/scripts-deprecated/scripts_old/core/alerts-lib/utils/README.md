# 📬 Alert Queue — Fila de Alertas (queue.sh)

Módulo de gerenciamento de fila para o sistema de alertas do MapsProve.

## Funcionalidades

- **Enfileira alertas** em formato JSON com prioridade e metadados.
- **Processa a fila** enviando alertas para múltiplos canais (Slack, Email, Telegram).
- **Rotação automática** de backups da fila.
- **Promoção automática de prioridade** para alertas antigos.
- **Atomicidade** garantida via flock.
- **Métricas**: tamanho da fila, tempo de processamento, logs detalhados.

## Comandos Principais

```bash
# Enfileirar alerta
enqueue_alert <priority> <type> <message> [metadata_json]
# Exemplo:
enqueue_alert "high" "cpu" "CPU 95%" '{"host":"svr01"}'

# Processar a fila (enviar alertas)
process_alert_queue

# Consultar quantidade de alertas pendentes
get_queue_size

# Listar alertas pendentes (JSON)
get_pending_alerts

Estrutura do Arquivo de Fila
json
Copiar
Editar
{
  "version": "0.3.1",
  "alerts": [
    {
      "priority": "high",
      "type": "disk",
      "message": "Espaço crítico",
      "timestamp": 1625097600,
      "metadata": {"mount": "/var", "usage": 98}
    }
  ]
}

Observações
Backups: Mantém os últimos 7 arquivos .bak da fila em logs/monitor/queue_backups/.

Promoção de prioridade: Alertas de baixa prioridade sobem automaticamente se não forem tratados em 1 hora.

Atomicidade: Uso de flock para evitar corrupção em ambientes concorrentes.

Dependências: jq, flock.

Integração
Este módulo é chamado automaticamente pelo sistema de alertas do MapsProve (monitor-alerts).

Contato: Para dúvidas ou sugestões, utilize o canal oficial do projeto.
