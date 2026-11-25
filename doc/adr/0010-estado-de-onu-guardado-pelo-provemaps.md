# ADR 0010 — O ProVeMaps guarda o estado de cada ONU a cada coleta

| Campo            | Valor                                                       |
|------------------|-------------------------------------------------------------|
| Estado           | **Proposto**                                                |
| Data             | 2026-11-24                                                  |
| Decisores        | Equipe Técnica Simples Internet — Paulo Marcelino           |
| Tags             | `gpon`, `zabbix`, `monitoramento`, `persistência`           |
| Substitui        | —                                                           |
| Substituído por  | —                                                           |

---

## 1. Contexto e Problema

O ecrã «Monitoramento GPON» (EV-0095) precisa de dizer **desde quando** uma ONU está no estado
atual e de reconhecer uma **queda coletiva** numa PON (≥ 3 ONUs em LOS dentro de 10 min — sinal
de fibra cortada a montante, não de clientes isolados).

O Zabbix não dá isso de forma fiável:

- os itens de ONU (`onu.status[…]` na ZTE, `OnlineStateS0P<p>[…]` na VSOL) dão só o **estado
  atual**; o histórico de um item de texto não marca transições e varia por template;
- o «último offline» da ZTE (`onu.last_offline[…]`) vem do **relógio da OLT**, que em produção
  está errado (`07 D1 01 0D …` = ano 2001) — não serve para «desde quando»;
- a VSOL não tem motivo de queda nem hora de transição.

Princípio §2.1 do `CLAUDE.md`: o que não se sabe mostra-se como desconhecido, nunca inventado.

## 2. Drivers da Decisão

- **D-1:** «online desde» e queda coletiva com instantes **reais**, não do relógio da OLT.
- **D-2:** custo baixo no Zabbix (a mesma API já serve a coleta óptica a cada 60 s).
- **D-3:** o pedido do ecrã não chama o Zabbix (resposta rápida, sem depender dele).
- **D-4:** preparar a ligação a SGP/Radius (cliente, login, caixa CTO) sem outro modelo.

## 3. Opções Consideradas

### Opção A — Ler tudo do Zabbix a cada pedido

**Prós:** nada para guardar; sem migração.

**Contras:** sem transições observadas → sem «desde» nem queda coletiva; o ecrã fica tão lento
e tão disponível quanto o Zabbix; N pedidos de N operadores = N vezes a carga.

### Opção B — Usar triggers/eventos do Zabbix (`event.get`)

**Prós:** o Zabbix já regista eventos.

**Contras:** depende de existirem triggers por ONU (não existem nos templates atuais); a hora do
evento é a da coleta do Zabbix, o que até serviria, mas obrigaria a criar e manter triggers para
centenas de ONUs fora do ProVeMaps.

### Opção C — O ProVeMaps guarda o estado observado (`gpon.OnuState`)

**Prós:** transições observadas por nós com o relógio do servidor; ecrã lê só a base;
campos para SGP/Radius no mesmo registo.

**Contras:** mais uma tabela e uma tarefa periódica; a resolução da transição é a do ciclo
(120 s).

## 4. Decisão

Escolhemos a **Opção C — o ProVeMaps guarda o estado observado**.

- Tarefa Celery `gpon.tasks.collect_onu_states` a cada **120 s** (beat em `core/celery.py`,
  fila `zabbix`, lock por `cache.add`). Faz **um `item.get` por OLT** pelo gateway
  (`zabbix_request`), com `output` mínimo e `search` só pelas famílias de chave usadas, e no
  máximo um `valuemap.get` por OLT (em cache 1 h) para o texto do motivo ZTE.
- Guarda-se por ONU (`OnuState`, único por `(device, onu_key)`): identidade (serial na ZTE;
  `<pon>:<n>|<mac ou serial>` na VSOL), PON e índice, estado e motivo (classificado e o código
  bruto), RX na ONU / na OLT (sentinelas 0/−80 → `null`), distância, chave do item de RX (para o
  histórico), `status_since` + `status_since_is_first_seen`, `first_seen`, `last_seen`, e
  `cliente_nome`/`login_radius`/`caixa_cto` (hoje vazios).
- `status_since` só muda quando muda o estado ou o motivo. Na primeira observação é a hora da
  coleta e `status_since_is_first_seen = true` (o ecrã diz «desde ≥ …»); esses instantes **não**
  contam para a queda coletiva.
- O estado da OLT (ping, CPU, temperatura, estado das PONs) e o resultado da última execução
  ficam em cache (10 min / 1 dia), não na base.
- Uma ONU que deixa de vir do Zabbix não se apaga: fica com o `last_seen` antigo e aparece como
  `unknown` passado 1 dia.

## 5. Consequências

### Positivas

- «Online desde» e queda coletiva com janela real de 10 min.
- O ecrã responde da base (2 consultas), mesmo com o Zabbix em baixo — e diz que está.
- Custo no Zabbix previsível: 9 OLT → 9 `item.get` a cada 120 s (~2 s no total, medido em
  produção a 2026-11-24, ~1 200 itens).

### Negativas

- Resolução de 120 s nas transições; uma queda e volta dentro do ciclo não se vê.
- Antes da primeira transição observada não há «desde» exato (por desenho).
- Mais uma tarefa na fila `zabbix`.

### Neutras

- A identificação das OLT é por convenção de nome no inventário («OLT» no nome, fabricante
  «ZTE»/«VSOL» no nome ou no campo `vendor`, `zabbix_hostid` preenchido).

## 6. Referências

- [Manual operacional](../../CLAUDE.md) — §2.1 (nada inventado), §7 (Zabbix).
- EV-0095 na Central de Evolução; contrato do ecrã (payload de `/api/v1/monitoring/gpon/`).
- `backend/gpon/` — `models.py`, `domain/parsers.py`, `usecases.py`, `tasks.py`.
- EV-0063 (lock da coleta óptica), EV-0082 (sentinelas de ONU).
