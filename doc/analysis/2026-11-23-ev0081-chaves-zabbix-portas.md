# EV-0081 — Chaves Zabbix das portas: o que o inventário tem vs. o que o Zabbix devolve

> **Data:** 2026-11-23 · **Âmbito:** só diagnóstico (nada foi alterado no inventário, na base nem no Zabbix).
> **Origem:** «Fica» do EV-0063 ([quadro manual](2026-11-23-quadro-manual.md)): 129 portas com chaves que
> nenhum host devolve e 2 portas Huawei (334, 514) com TX = 32,2471 constante.
> **Método:** shell Django no container de produção (`docker-web-1`), inventário pelo ORM em modo leitura,
> Zabbix só pelo gateway `integrations.zabbix.zabbix_service.zabbix_request` (`host.get`, `item.get`,
> `discoveryrule.get`, `history.get` com `limit` 200). **≈ 30 chamadas ao Zabbix no total.** O gateway
> está em `READ_ONLY` e bloqueou um `trend.get` (ver «Fora do âmbito»).

## Resumo

| | Nº de portas | Causa | Correção provável |
|---|---|---|---|
| OLT ZTE BRV C300 (device 22) | **150** (as 129 do EV-0063 + as 21 que liam de outros hosts) | **O equipamento aponta para o host Zabbix `10694`, que já não existe.** O host atual com o mesmo nome é o **`10744`**, com outro template («OLT ZTE GPON»): as chaves `zxoltrxsignal.[…]`/`zxolttxsignal.[…]` não existem em **nenhum** host do Zabbix (procura global → 0 itens) | `Device.zabbix_hostid` 10694 → 10744; 108 portas-ONU ganham a chave nova `onu.rx[<serial>,<slot>,<pon>,<onu>]` (só RX); 42 portas ficam sem chave |
| OLT VSOL GRANADA (10702) | 1 (porta 523) | chave de RX aponta para um item duplicado com `{#USERNAME}` literal **de outra ONU** (0/1/4); chave de TX para uma ONU que já não existe (0/1/6) | limpar as duas chaves |
| Huawei Cristo Rei 334 / Santana IDC 514 | 2 | o transceptor **não tem diagnóstico digital (DDM)**: RX devolve `-nan` (item «unsupported»), limiares falsos (TX 32,25 / RX 0); 32,2471 dBm = **10·log₁₀(2²⁴ × 0,1 µW / 1 mW)**, o valor de um registo «todo a uns». **Não é unidade, multiplicador nem pré-processamento**: o mesmo item, com o mesmo `×0,01`, dá valores certos em 20 outras portas dos mesmos switches | no Zabbix: validação «In range» ou desativar os 2 (4) itens; no inventário: opcionalmente limpar as chaves |

Contagem de controlo: das 226 portas com chave óptica, **151** têm pelo menos uma chave que o host do
equipamento não devolve (150 ZTE + 1 VSOL). As 75 restantes resolvem no seu host.

## 1. Por equipamento

Itens lidos com **um `item.get` por host** (campos `key_`, `name`, `units`, `value_type`, `lastvalue`,
`lastclock`, `state`, `error`, `snmp_oid`, `selectPreprocessing`).

| Equipamento (hostid no inventário) | Portas com chave | Portas com chave inexistente | Chaves no inventário | Itens ópticos reais no host | Proposta |
|---|---|---|---|---|---|
| ZTE - OLT BRV C300 (**10694 — host apagado**; atual **10744**) | 150 | **150** | 129 × `zxoltrxsignal.[<ifIndex>.<onu>]` + `zxolttxsignal.[…]`; 19 × `net.if.in[ifHCInOctets.<ifIndex>]` (RX, TX vazio); 2 × `olt[power0|1]` (RX e TX) | no 10744: 122 × `onu.rx[<serial>,<slot>,<pon>,<onu>]` — «ONU …: Potencia RX na OLT (upstream)», `dBm`, `value_type` 0 (float), pré-processamento «SNMP walk value» (`{$ONU_RX_OID}.<ifIndex>.<onu>`) + multiplicador `0.001`. **Não há item de TX por ONU.** `net.if.in[…]` = tráfego em `bps`; `olt[power*]` = fonte de alimentação em **W** | ver §1.1 |
| VSOL - OLT EPON GRANADA (10702) | 10 | 1 (523) | `SinalRXS0P<pon>[GPON0/<pon>:<onu> - <onu>]` usada como RX **e** como TX | `SinalRXS0P1[GPON0/1:<n> - <n>]` (`dbm`, JS `parseFloat`) para ONU 1–5; mais 2 itens com `{#USERNAME}` literal (duplicados de ONU 4 e 5) | ver §1.2 |
| VSOL - OLT EPON FURACAO (10703) | 3 | 0 | idem (RX = TX) | idem | ver §1.2 (mesma chave em RX e TX) |
| Huawei - Switch Santana IDC (10665) | 17 | 0 | `hwEntityOpticalLaneRxPower[<idx>]` / `…TxPower[<idx>]` | idem, `dBm`, `×0,01` | só a 514 (§2) |
| Huawei - Switch Faz. Cristo Rei (10675) | 6 | 0 | idem | idem | só a 334 (§2) |
| Huawei - Switch Santa terezinha (10663) | 2 | 0 | idem | idem, **mas nunca coletados** (`lastclock` 0 em 329 de 368 itens do host) | ver «Fora do âmbito» (0,00 dBm gravado) |
| Huawei Santana Marajo (10658), Furacao (10660), Vila Mandi (10661), Vila Rica (10664), CDT (10667), Veranopolis (10678), Confresa (10679), Elagro (10723) | 6/7/5/4/4/2/6/4 | 0 | idem | idem | nada |

Há só **um** equipamento órfão: dos 22 equipamentos do inventário, todos com `zabbix_hostid`, só o
device 22 aponta para um host que não existe (`host.get` com os 22 ids).

### 1.1 OLT ZTE BRV C300 — o host foi recriado e o template mudou

- `host.get hostids=[10694]` → `[]`. `host.get` por nome → `10744 «ZTE - OLT BRV C300»` (10.254.0.2,
  template «OLT ZTE GPON»). As OLT irmãs 10691 (CDT C300) e 10693 (STA C300) usam o mesmo template.
- `item.get search key_=zxolt` em todos os hosts → **0 itens**: a família `zxolt*` deixou de existir no
  Zabbix (o template antigo foi substituído). As portas estão sem leitura desde **2026-08-01**
  (`last_optical_check` de 107 portas); os `0,00` que ainda lá estão são dessa altura e o
  `optical-summary` já os trata como `stale`.
- **Correspondência:** o índice antigo é o ifIndex ZTE «antigo» da PON, `0x10SSPP00`
  (SS = slot, PP = porta PON); o novo template usa `0x1101SSPP` e põe slot/pon/onu na chave.
  Ex.: `zxoltrxsignal.[269025536.1]` = `0x10090100`.1 → slot 9, PON 1, ONU 1 →
  `onu.rx[GPON00A87658,9,1,1]`. Os slots/PONs do inventário (9/1–9/16, sem 9/3) são exatamente os do
  host 10744.

| Grupo (device 22) | Portas | Valor atual do item novo | Proposta |
|---|---|---|---|
| Portas-ONU (`name` = `<ifIndex>.<onu>`) com `onu.rx` na mesma posição | **108** | 67 plausíveis (ex.: −23,24; −28,31; −30,18 dBm); 22 com **−80** (ONU `offline` — sentinela); 19 com **0** em ONU `online` (sentinela «sem leitura», não 0 dBm) | `rx_power_item_key` ← `onu.rx[…]`; `tx_power_item_key` ← `""` (não há TX por ONU) |
| Portas-ONU sem `onu.rx` na posição | 13 | — (ONU desprovisionada; ex.: 9/2/1, 9/5/12, 9/16/9) | limpar as duas chaves |
| Portas de cartão/curtas (`0`, `1`, `9`, `10`, `11`, `19`, `20`, `1.1.1`; `zabbix_item_key` = `Card[…]`/`cardcpu[…]`) | 8 | herdaram `zxolt*` por engano (4 delas a **mesma** `zxoltrxsignal.[269025536.1]`) | limpar as duas chaves |
| `ifHCInOctets.<ifIndex>` e `cardcpu[…]` com RX = `net.if.in[…]` | 19 | contador de tráfego em `bps` (ex.: 729 352) — não é potência | limpar `rx_power_item_key` |
| `power0`/`power1` com RX = TX = `olt[power0|1]` | 2 | potência da **fonte** em W (322 / 0) | limpar as duas chaves |

A tabela completa porta → item novo está em
`/tmp/claude-0/-opt-provemaps/f8580cd7-fd74-478d-b151-a6bb503674f3/scratchpad/ev0081/mapa_zte_zxolt_para_onu_rx.csv`
(temporária; regenera-se com os scripts de «Como reproduzir»).

**Ressalvas.** (1) A chave nova traz o **número de série** da ONU: trocar a ONU de um cliente muda a chave
e a porta volta a ficar órfã; a correspondência estável é (slot, PON, ONU). (2) Não dá para confirmar
que `zxoltrxsignal` media a mesma grandeza que `onu.rx` («RX na OLT, upstream») — os itens antigos já
não existem. (3) Nenhuma destas 150 portas é ponta de cabo (`FiberCable` com porta do device 22: 0);
o efeito é só no ecrã de portas/Ativos.

### 1.2 OLTs VSOL

- **Porta 523 `GPON0/1:6`** (Granada): RX = `SinalRXS0P1[{#USERNAME} - 4]` — o item existe, mas é uma
  cópia da **ONU 0/1/4** (mesmo serial `SHLN3c4d923e`, −12,27 dBm) com a macro LLD por expandir; o
  inventário mostra −12,27 como se fosse a ONU 6. TX = `SinalRXS0P1[GPON0/1:6 - 6]` não existe (não há
  ONU 0/1/6 no host). → limpar as duas chaves.
- **12 portas VSOL (9 Granada + 3 Furacão) têm RX = TX** (a mesma chave `SinalRX…`) e por isso `last_tx_power` = `last_rx_power`
  (ex.: 519 −19,71/−19,71). É potência RX da ONU; não há item de TX. As portas de PON (`GPON0/1`,
  `GPON0/2`, …) levam a chave da ONU 1 do PON. → limpar `tx_power_item_key` e as chaves das portas de PON.

### 1.3 Como as chaves ficaram erradas (código)

- **Host recriado:** nada sincroniza `Device.zabbix_hostid` quando o host é apagado e recriado;
  a coleta (`inventory/tasks.py:update_all_port_optical_levels` → `domain/optical.fetch_ports_optical_snapshots`)
  agrupa por esse hostid e, desde o EV-0063, simplesmente não encontra nada (antes ia buscar a outros hosts).
- **Chaves de não-ópticos em portas:** `domain/optical._discover_optical_keys_by_portname` procura itens
  com `search key_ LIKE %<nome da porta>%` e escolhe pelo `_score_optical_candidate`, que pontua
  positivo palavras como `receive`/`input`/`rx` sem exigir unidade dBm. Com nomes curtos (`0`, `1`, `9`)
  o `LIKE` apanha centenas de itens e ganha o primeiro com pontuação → a mesma chave em 4 portas.
  Com `ifHCInOctets.<n>` como nome, encontra o próprio `net.if.in[…]` (provavelmente pontuado pelo nome
  inglês antigo «Bits received»). `olt[power*]` entra pela palavra `power`.
  `inventory/services/fiber_status.fetch_interface_status_advanced` tem um segundo caminho ainda mais
  largo (`rx_key_generic`: qualquer chave com `rx` no mesmo `interfaceid`, que nos hosts SNMP é o host
  inteiro). Os dois escrevem a chave com `persist_keys=True` (descoberta/ importação) ou por
  `usecases/fibers._persist_discovered_optical_keys`.
- **A descoberta não resolveria o ZTE:** `usecases/devices_common._identify_item_role` só reconhece
  ópticos pela **chave** (`rxpower`, `opticalrx`, `hwentityopticallanerxpower`, …); `onu.rx[…]` não tem
  nenhum marcador → não é classificado como óptico. Correr a descoberta no host 10744 criaria portas
  novas (`ifOperStatus[…]`) e deixaria as 150 antigas como estão.
- **VSOL RX = TX:** a mesma heurística por nome; sem item de TX, o candidato com melhor pontuação para TX
  é o próprio item de RX.

## 2. TX = 32,2471 nas portas 334 e 514

| | 334 — Cristo Rei `XGigabitEthernet0/0/5` («to-agrobrilhante») | 514 — Santana IDC `XGigabitEthernet0/0/9` («CCR-RURAL») |
|---|---|---|
| Item TX | `hwEntityOpticalLaneTxPower[67469646]` (itemid 76882), OID `…2011.5.25.31.1.1.3.1.33.67469646`, `dBm`, float, intervalo 15 min, pré-proc. `×0,01` | `hwEntityOpticalLaneTxPower[67469902]` (93826), idem |
| Valor | **32,2471** — 200 últimas amostras (21→23/11) todas iguais | **32,2471** — idem |
| Item RX | `state=1` (unsupported): «Preprocessing failed for: -nan … cannot apply multiplier "0.01" to value of type "string"» | idem |
| Limiares do transceptor | Tx High/Low/Warn = **32,25**; Rx High/Low/Warn = **0** | idem |
| Interface | `ifOperStatus` 1, tráfego 98 kbps / 376 kbps, `ifSpeed` **1000** numa porta de 10 G | `ifOperStatus` 1, tráfego 1,4 / 4,4 kbps, `ifSpeed` **1000** |
| Ponta de cabo? | não | não |

**Porquê:** o switch está a ler um módulo de 1 G **sem diagnóstico digital** (provavelmente SFP elétrico
1000BASE-T ou óptico sem DDM). O RX vem como a string `-nan`, os limiares vêm com valores impossíveis,
e o TX é o valor que o switch calcula a partir de um registo de potência inválido:
10·log₁₀(2²⁴ × 0,1 µW / 1 mW) = **32,2472 dBm** (calculado; coincide com o valor do item até à 4.ª casa).
**Não é problema de unidade, de multiplicador nem de pré-processamento em falta**: as 20 outras portas dos
mesmos dois switches, com itens do mesmo template e o mesmo `×0,01`, dão valores coerentes (RX +0,4 a
−40 dBm, TX −10,2 a +2,7 dBm) e limiares normais.

Do lado do ProVeMaps, a coleta já descarta o 32,2471 (fora de −60…+15, regra do EV-0063), **mas grava
`last_rx_power = 0,00`** nas duas portas: o `lastvalue` de um item `unsupported` nunca coletado é `"0"`
e o `_bulk_fetch_item_values` aceita-o (ver «Fora do âmbito»).

## Proposta de correção (nada disto foi executado)

**Recomendada — A + B + C, por esta ordem, cada passo com dry-run e cópia antes:**

- **A. Device 22: `Device.zabbix_hostid` 10694 → 10744** (1 linha). Sem isto nenhuma leitura do OLT BRV
  funciona (estado, tráfego, óptico). Rever depois `Port.zabbix_interfaceid`/`zabbix_itemid` das portas
  desse device (apontam para ids do host apagado).
- **B. Comando de gestão idempotente `ev0081_recadastrar_chaves` com `--dry-run` por omissão** (lista
  porta, chave antiga, chave nova, valor atual do item; só escreve com `--aplicar`, numa transação, depois
  de copiar as chaves antigas para JSON; invalida `invalidate_fiber_cache()` e
  `invalidate_dashboard_cache()`). Alterações:
  - 108 portas-ONU do device 22: `rx_power_item_key` ← `onu.rx[…]` da mesma (slot, PON, ONU) no host
    10744; `tx_power_item_key` ← `""`;
  - 42 portas do device 22 (13 ONU sem item, 8 de cartão, 19 de tráfego, 2 de fonte): `rx_power_item_key`
    e `tx_power_item_key` ← `""`;
  - VSOL: porta 523 → as duas chaves `""`; as 12 portas com RX = TX → `tx_power_item_key` ← `""`
    (e as portas de PON `GPON0/n` → as duas `""`, se o Paulo concordar que a PON não tem leitura própria);
  - Huawei 334 e 514: opcional, as duas chaves `""` (o módulo não tem DDM; voltar a pôr se trocarem o SFP).
  - Total: **163 portas** (150 do device 22 + 13 VSOL) (+2 opcionais Huawei); campos só `rx_power_item_key`/`tx_power_item_key`
    (os `last_*` antigos podem ser postos a `null` no mesmo passo, com cópia).
- **C. No Zabbix (decisão de quem administra o Zabbix, não do ProVeMaps):** nos itens
  `hwEntityOpticalLane{Rx,Tx}Power` do template Huawei, pré-processamento «In range» (ex.: −40…+10)
  com «Custom on fail → Discard value» ou «Set error», o que torna os módulos sem DDM `unsupported`
  em vez de 32,25; ou desativar os 4 itens das portas 0/0/5 (10675) e 0/0/9 (10665). No template
  «OLT ZTE GPON», tratar o `0` (ONU online sem leitura) e o `−80` (offline) do `onu.rx` da mesma forma.
  No template VSOL, corrigir o LLD que gera itens com `{#USERNAME}` literal.

**Alternativas avaliadas:**

- **Correr a descoberta no device 22** — não resolve: `onu.rx` não é reconhecido como óptico
  (`_identify_item_role`), criaria portas novas e deixaria as antigas. Só serve depois de ensinar a
  descoberta o padrão ZTE novo.
- **Ler as ONUs por (slot, PON, ONU) em vez de chave fixa** — resolve a fragilidade do serial na chave,
  mas é mudança de código na coleta (item próprio, não EV-0081).
- **Não fazer nada no inventário e só corrigir A** — as 150 portas continuariam sem leitura (as chaves
  `zxolt*` não existem em lado nenhum).

## Fora do âmbito (com prova — candidatos a itens EV novos)

1. **Dado inventado: a coleta grava 0,00 dBm de itens nunca coletados ou «unsupported».**
   `domain/optical._bulk_fetch_item_values` usa `lastvalue` sem olhar para `lastclock`/`state`; o Zabbix
   devolve `lastvalue "0"` nesses itens e 0 está dentro de −60…+15. Prova: portas 334 e 514
   (RX `state=1`, `lastclock 0`) e 275, 286 (Santa terezinha, RX e TX `lastclock 0`; 329 de 368 itens do
   host nunca coletados) têm `last_*_power = 0.00` com `last_optical_check` de hoje (2026-11-23 23:34 UTC).
   **A porta 275 é a ponta B do cabo 7 «ELAGRO-SANTA TEREZINHA»** — os ecrãs Enlaces/Alarmes leem esse 0
   como leitura fresca, e `services/fiber_status` trata 0,0 como `zero_signal`. Caminho: exigir
   `lastclock > 0` e `state == 0` (pedir esses campos no `item.get`). Os sentinelas `0`/`−80` do `onu.rx`
   ZTE e o `0` das ONU VSOL (`SinalRXS0P1[GPON0/1:1 - 1]` = 0) caem no mesmo problema.
2. **Heurística de descoberta atribui chaves de tráfego/alimentação/outra ONU a portas**
   (`_discover_optical_keys_by_portname` + `_score_optical_candidate`, `fiber_status` `rx_key_generic`):
   ver §1.3 — 4 portas com a mesma chave, 19 com `net.if.in`, 2 com `olt[power*]`, 12 VSOL com RX = TX.
   Caminho: exigir unidade `dBm` (o `units` já vem no `item.get`) e correspondência exata do nome da porta.
3. **`fetch_interface_status_advanced._get_item` procura a chave com `search` (LIKE)**, não `filter`
   (`inventory/services/fiber_status.py:87-106`): `net.if.in[ifHCInOctets.1]` corresponde também a
   `…ifHCInOctets.10`. Não reproduzido em produção nesta sessão (só leitura de código).
4. **`trend.get` bloqueado pelo modo `READ_ONLY` do cliente** (`integrations.zabbix.client: Blocked unsafe
   method in READ_ONLY mode: trend.get`) — é um método de leitura; a lista de métodos permitidos está
   incompleta. Impacto baixo (nada no código usa `trend.get` hoje).
5. **O arranque do shell em produção imprime `ALLOWED_HOSTS=['*']`** (`[settings.base]
   DJANGO_SETTINGS_MODULE=settings.prod ALLOWED_HOSTS=['*'] DEBUG=False`). O EV-0037 diz que o `.env`
   ganhou `ALLOWED_HOSTS`; vale confirmar se `*` é o valor pretendido.

## Como reproduzir (só leitura)

Os scripts estão no scratchpad da sessão
(`/tmp/claude-0/-opt-provemaps/f8580cd7-fd74-478d-b151-a6bb503674f3/scratchpad/ev0081/`); cada um imprime
JSON a seguir ao marcador `@@JSON@@`.

```bash
S=/tmp/claude-0/-opt-provemaps/f8580cd7-fd74-478d-b151-a6bb503674f3/scratchpad/ev0081
# 1) portas com chave óptica (ORM) + 1 item.get por host (14 chamadas)
docker exec -i docker-web-1 python manage.py shell < $S/01_inventario_e_itens.py > $S/raw01.txt
# 2) host 10694 (→ []), hosts ZTE/VSOL por nome, procura global de chaves zxolt (→ 0)
docker exec -i docker-web-1 python manage.py shell < $S/02_host_olt_zte.py > $S/raw02.txt
# 3) itens dos hosts ZTE 10744/10691/10693 (onu.rx, net.if.in, olt[...])
docker exec -i docker-web-1 python manage.py shell < $S/03_itens_olt_zte.py > $S/raw03.txt
# 4) item.get + history.get (limit 200) do TX das portas 334/514
docker exec -i docker-web-1 python manage.py shell < $S/04_historico_tx_huawei.py > $S/raw04.txt
# 5) Device.zabbix_hostid vs. host.get (órfãos)
docker exec -i docker-web-1 python manage.py shell < $S/05_devices_vs_hosts.py > $S/raw05.txt
# 6) portas afetadas que são ponta de cabo (só ORM)
docker exec -i docker-web-1 python manage.py shell < $S/06_portas_em_cabos.py
```

Verificações rápidas equivalentes, num `manage.py shell`:

```python
from integrations.zabbix.zabbix_service import zabbix_request
zabbix_request("host.get", {"hostids": ["10694"], "output": ["hostid"]})            # []
zabbix_request("item.get", {"search": {"key_": "zxolt"}, "output": ["key_"]})        # []
zabbix_request("item.get", {"hostids": ["10744"], "search": {"key_": "onu.rx["},
                            "output": ["key_", "lastvalue", "units"]})               # 122 itens
zabbix_request("item.get", {"itemids": ["76882", "93826"],
                            "output": ["key_", "lastvalue", "units", "state"]})      # 32.2471 / 32.2471
import math; 10 * math.log10(2**24 * 1e-4)                                          # 32.2472
```
