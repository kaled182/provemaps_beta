# ADR 0009 — Topologia da rede desenhada em SVG próprio, por projeção das coordenadas dos POPs

| Campo            | Valor                                                       |
|------------------|-------------------------------------------------------------|
| Estado           | **Aceito** (implementado em EV-0060, 2026-11-23)            |
| Data             | 2026-11-23                                                  |
| Decisores        | Equipe Técnica Simples Internet — Paulo Marcelino           |
| Tags             | `frontend`, `visualização`, `topologia`                     |
| Substitui        | —                                                           |
| Substituído por  | —                                                           |

---

## 1. Contexto e Problema

O plano «ProveMaps NOC» (aceito pelo Paulo em 2026-11-23) pede um ecrã
**Topologia**: vista esquemática dos POPs e dos enlaces, com o estado de cada
enlace e a capacidade por trecho. O produto já tem duas formas de desenhar:
o mapa (`providers/maps/`, geográfico, com tiles) e os gráficos de série
temporal (`TimeSeriesChart.vue`, Chart.js). Nenhuma serve: o mapa mostra o
traçado real (ruído para quem quer ver ligações), o Chart.js não desenha grafos.

Dados disponíveis (medido em produção, 2026-11-23): 19 sites, todos com
coordenadas; 17 cabos, todos com as duas pontas em portas de equipamentos
(os campos `site_a`/`site_b` estão vazios — o site de cada ponta vem do
equipamento); **nenhuma fibra, tubo, segmento ou fusão cadastrados**.

## 2. Drivers da Decisão

- **D-1 — Sem biblioteca nova** (CLAUDE.md §6: não instalar biblioteca de UI sem ADR; peso no bundle).
- **D-2 — Disposição estável e reconhecível** pelo NOC: o POP do norte fica a norte.
- **D-3 — Tokens e dois temas** sem código à parte.
- **D-4 — Nada inventado:** capacidade sem fibras cadastradas é «sem dados».

## 3. Opções Consideradas

- **A — SVG próprio, posição dos nós = projeção equiretangular das coordenadas dos sites** no retângulo do ecrã (com margem). Linhas retas entre POPs; cabos paralelos entre o mesmo par afastados por curva quadrática.
- **B — Biblioteca de grafos (Cytoscape.js, vis-network, D3-force).** Disposição por forças: muda a cada carga, perde a geografia, +150–400 KB.
- **C — Reutilizar o mapa com estilo «em branco».** Continua a ser o traçado real e depende do provedor de mapas.

## 4. Decisão

**Opção A.** `views/TopologyView.vue` desenha um `<svg viewBox>` com nós e
arestas a partir de `GET /api/v1/fiber-cables/topology/`; a projeção e o
afastamento de arestas paralelas vivem em `utils/topologyLayout.js` (puro,
testado). Cores por tokens (`--success|--warning|--danger|--n-*`).

## 5. Consequências

- Positivas: zero dependências, disposição determinística e geográfica, temas grátis.
- Negativas: POPs muito próximos podem sobrepor-se — mitigado com raio mínimo e rótulos só ao passar o rato quando a densidade sobe; não há zoom/pan nesta versão.
- A capacidade por trecho fica «sem dados» até haver fibras cadastradas (EV-0061 regista que a barra de ocupação do inventário mostrava 0 % inventado).
