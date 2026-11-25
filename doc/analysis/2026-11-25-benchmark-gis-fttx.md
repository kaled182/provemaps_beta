# Benchmark de GIS / projeto de rede FTTx — 2026-11-25

> Pedido do Paulo (2026-11-25): «sugar o que cada um tem de melhor e o que falta» no
> mapeamento de rede FTTx. Fontes: páginas públicas lidas a 2026-11-25. Onde a página é só
> marketing, isso está dito; onde há inferência, está marcado. O SGP (fotos do Paulo) ainda
> não foi incluído — as fotos estão no computador dele.

## Fontes e limites

| Produto | O que se leu | Limite |
|---|---|---|
| FTTH Planner | `ftthplanner.com.br` (SPA): textos pt-BR do bundle `/assets/index-*.js` e a API pública `/api/saas/public/plans` (conferida: Trial R$ 0, Básico 100, Intermediário 199,90, Consultor 300, Turbo 397) | Texto da interface prova que o ecrã existe, não a qualidade |
| OZmap | `ozmap.com`, `/planos/`, `/como-resolvemos/`, `/ozmob/`, `/ozloc/`, `/findme/`, `/integracoes/`, `/release-notes/` | «OTDR ativo» e «tempo real» são texto de marketing |
| Tomodat | `/tutoriais/` (5 vídeos: TreeView, adicionar itens, itens em série, regiões, régua), `/funcionalidades/`, `/planos/` | Frases genéricas; sem detalhe de splitters/potência |
| ISP Gestión | `/pt/gis-ftth/` + cobertura por rua, mapa de conexões, app ISP-TEC | Módulo de um ERP; o forte é o ERP, não o projeto óptico |
| FTTx Maps | — | Não abriu (WebFetch e curl sem resposta, sem cópia no Wayback) |

## Matriz

✓ a página mostra/afirma · ✗ não existe no ProVeMaps · ? não dá para saber

| Funcionalidade | FTTH Planner | OZmap | Tomodat | ISP Gestión | ProVeMaps (2026-11-25) |
|---|---|---|---|---|---|
| Mapa com cabos, caixas, postes | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dutos / subdutos | ✓ | ? | ? | ? | ✗ |
| Diagrama de caixa (fusões, splitters) | ✓ | ✓ | ✓ | ✓ | fusões ✓; editor 3 colunas = EV-0141 |
| Diagrama lógico / unifilar exportável | ✓ | ✓ (PDF) | ? | ? | ✗ |
| Splitter com estado/bloqueio por porta | ✓ | ✓ (tags, bloqueio) | reserva de porta | porta livre | EV-0142 |
| Cálculo de potência | ✓ (catálogo/PON manual) | ✓ | ? | ? | ✓ EV-0140, com TX **real** do Zabbix |
| Rastreamento da luz (VFL virtual) | ✓ | ✓ («Iluminação») | ✓ («Ativação de redes») | ? | ✓ |
| OTDR distância → mapa | ✓ | ✓ | ✓ | ? | ✓ (+ medição cruzada A/B, alerta da equipa) |
| Estado em tempo real (NMS) | ✗ (online/offline vem do ERP) | afirma, «depende de integração» | ? | parcial | ✓ Zabbix nativo (enlaces, RX/TX, GPON) |
| Cliente/ONU na porta da CTO | ✓ (serial, MAC, dBm) | ✓ | ✓ | ✓ | ✗ (ONUs existem pelo GPON, sem vínculo à CTO) |
| Condomínio vertical | ✓ | ✓ | ? | ✓ | ✗ |
| Viabilidade por endereço | ✓ | ✓ (OZloc) | ✓ | ✓ | ✗ |
| Link para o cliente mandar o GPS | ✓ | ✓ (FindMe) | ? | ? | ✗ |
| API de viabilidade (site/chatbot) | ✓ | ✓ (TMForum, devolve OLT/slot/PON) | ? | ? | ✗ (há tokens de serviço, ADR 0008) |
| Postes da distribuidora (ANEEL) | ✓ (99 distribuidoras) | parcial | ferragem por poste | ? | postes ✓ (EV-0139), sem base ANEEL |
| Relatório de área / BOM de materiais | ✓ | ✓ | custos | ? | ✗ |
| Export KMZ/PDF/planilha | ✓ | ✓ | ✓ (KML) | ? | só import |
| Integração ERP (IXC, SGP…) | ✓ (12) | ✓ (15+) | ? | é o ERP | ✗ |
| App de campo offline + pendências | ✓ | ✓ (OZmob) | «controle de obras» | app de OS | ✗ |
| Sugestão de alteração vinda do campo | ? | ✓ (revisão no escritório) | ? | ? | ✗ |
| Ciclo de vida planejado → implantado → certificado | ✓ | % documentação | ? | ? | ✗ |
| Rack / DIO / folha do POP | ✓ | DIO | ? | ? | parcial (chassi OLT/switch) |
| Permissões por papel e área | ✓ | ✓ | ? | ? | staff/login + TOTP |
| Auditoria em cascata | por caixa | ✓ | ? | ? | parcial |
| Street View no ponto | ? | ? | ? | ? | ✓ |

## O melhor de cada um que ainda falta ao ProVeMaps (por valor para um ISP com Zabbix)

1. **ONU/cliente na porta do splitter da CTO** — o elo entre o GPON que já monitorizamos e o
   cadastro físico (FTTH Planner, OZmap, ISP Gestión). Pré-requisito: EV-0142 (splitters).
2. **Viabilidade por endereço + link de GPS para o cliente** (FTTH Planner, OZmap FindMe/OZloc).
   Temos PostGIS (`ST_DWithin`) e portas; falta geocoding e o veredicto «porta livre a X m».
3. **Integração com o ERP (SGP)** — clientes, portas, comparação «só aqui / só no ERP».
4. **Relatório de área e BOM** — polígono → metros de cabo por tipo, CTO/CEO/postes, splitters.
5. **Diagrama lógico e rota completa de uma fibra exportáveis** (PDF/CSV/KML) — o rastreamento
   já existe; falta o documento.
6. **App de campo offline com pendências e sugestão de alteração revista** — liga ao alerta OTDR.
7. **Postes da distribuidora (BDGD/ANEEL) como camada** convertível em poste do projeto, com
   atributos de compartilhamento (código, aprovação, conflito elétrico).
8. **Ciclo de vida do elemento** (planejado/implantado/certificado) e % de documentação.
9. **Tags, bloqueio e reserva comercial por porta** (complementa EV-0142).
10. **Condomínio vertical** (andares, unidades, splitters por andar).
11. **POP: rack em U, DIO com bandejas, auto-fusão para o DIO, folha do POP.**
12. **Export KMZ/PDF/planilha.**
13. **Permissões por área/projeto e auditoria em cascata** (terceirizados).
14. **Dutos e subdutos** com caixas de passagem.
15. **API de viabilidade** com tokens/scopes (ADR 0008).

## O que falta a todos — onde o ProVeMaps se diferencia (inferência sobre o que as páginas não mostram)

1. **Potência medida × projetada por porta, contínua.** Todos calculam pelo catálogo; nós temos o
   RX real de cada ONU e o TX da porta (EV-0140). Marcar no mapa a CTO cuja perda real está X dB
   acima do projeto (conector sujo, fusão má, macrocurvatura) antes da reclamação.
2. **Alarme físico correlacionado com a topologia** — N ONUs do mesmo splitter/cabo caem juntas →
   menor ancestral comum na árvore óptica → segmento provável, cruzado com a medição OTDR A/B.
3. **Impacto antes da manutenção** — numa janela num cabo/CEO: clientes, PONs e enlaces de
   backbone afetados (rastreamento + GPON + enlaces).
4. **Validação da documentação pela telemetria** — ONU que a OLT diz estar na PON 3 mas o cadastro
   põe numa CTO servida pela PON 5 vira divergência automática.
5. **Backbone, DWDM, switches e FTTH no mesmo mapa**, com estado ao vivo.
6. **Histórico de degradação por fibra/CTO** (tendência de RX ligada ao elemento físico).
7. **MTTR real de ponta a ponta** — alarme Zabbix → alerta OTDR → pendência de campo → reposição
   confirmada pelo Zabbix.

## Ligação com o quadro atual

- Já em curso: EV-0141 (editor 3 colunas + tubo 1:1), EV-0142 (splitters com portas e dBm),
  EV-0143 (rastreamento destacado com dBm). O EV-0142 deve já prever tags/bloqueio/reserva (item 9).
- Candidatos a itens novos (triagem do Paulo): 1, 2, 3, 4, 5, 8 e os diferenciais D1–D4.
