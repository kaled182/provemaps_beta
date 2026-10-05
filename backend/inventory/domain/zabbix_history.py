"""
Leitura de histórico numérico do Zabbix com o tipo de valor correto.

`history.get` só devolve dados quando o parâmetro ``history`` coincide com o
``value_type`` do item (0 = float, 3 = unsigned). Os endpoints de tráfego
pediam ``history: 3`` fixo e, para itens float (comum com pré-processamento
«change per second» e multiplicador), recebiam ``[]`` e mostravam «sem dados».
Este módulo resolve o tipo (e as unidades) via ``item.get`` antes de pedir o
histórico — CLAUDE.md §7, EV-0003.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, TypedDict

from integrations.zabbix import zabbix_service

logger = logging.getLogger(__name__)

# Valor assumido quando o Zabbix não devolve metadados do item. Mantém o
# comportamento antigo (unsigned) como último recurso, mas agora registado.
DEFAULT_VALUE_TYPE = 3
NUMERIC_VALUE_TYPES = {0, 3}


class ItemMeta(TypedDict):
    itemid: str
    value_type: int
    units: str


def _coerce_list(raw: Any) -> list[Mapping[str, Any]]:
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, Mapping)]
    return []


def get_items_meta(item_ids: Iterable[Any]) -> dict[str, ItemMeta]:
    """Resolve ``value_type`` e ``units`` de vários itens numa só chamada.

    Devolve um dicionário indexado por ``itemid`` (string). Itens ausentes na
    resposta ficam de fora; quem chama usa :func:`meta_or_default`.
    """
    ids = [str(i) for i in item_ids if i]
    if not ids:
        return {}
    try:
        raw = zabbix_service.zabbix_request(
            "item.get",
            {"output": ["itemid", "value_type", "units"], "itemids": ids},
        )
    except Exception:
        logger.warning("zabbix_history.item_get_failed", extra={"itemids": ids}, exc_info=True)
        return {}

    result: dict[str, ItemMeta] = {}
    for entry in _coerce_list(raw):
        itemid = str(entry.get("itemid", "")).strip()
        if not itemid:
            continue
        try:
            value_type = int(entry.get("value_type", DEFAULT_VALUE_TYPE))
        except (TypeError, ValueError):
            value_type = DEFAULT_VALUE_TYPE
        result[itemid] = ItemMeta(
            itemid=itemid,
            value_type=value_type,
            units=str(entry.get("units") or ""),
        )
    return result


def meta_or_default(meta: Mapping[str, ItemMeta], item_id: Any) -> ItemMeta:
    """Metadados do item ou o default documentado (unsigned, sem unidade)."""
    key = str(item_id)
    if key in meta:
        return meta[key]
    logger.info("zabbix_history.value_type_defaulted", extra={"itemid": key})
    return ItemMeta(itemid=key, value_type=DEFAULT_VALUE_TYPE, units="")


def fetch_history(
    item_id: Any,
    time_from: int,
    time_till: int,
    *,
    meta: Mapping[str, ItemMeta] | None = None,
    limit: int | None = None,
) -> list[Mapping[str, Any]]:
    """``history.get`` de um item com ``history`` igual ao seu ``value_type``.

    ``meta`` permite reutilizar um ``item.get`` já feito para vários itens;
    sem ele, resolve-se o item isoladamente. Itens não numéricos devolvem
    ``[]`` sem consultar o histórico.
    """
    if not item_id:
        return []
    resolved = meta if meta is not None else get_items_meta([item_id])
    item_meta = meta_or_default(resolved, item_id)
    if item_meta["value_type"] not in NUMERIC_VALUE_TYPES:
        logger.warning(
            "zabbix_history.non_numeric_item",
            extra={"itemid": str(item_id), "value_type": item_meta["value_type"]},
        )
        return []

    params: dict[str, Any] = {
        "itemids": [str(item_id)],
        "history": item_meta["value_type"],
        "time_from": time_from,
        "time_till": time_till,
        "sortfield": "clock",
        "sortorder": "ASC",
    }
    if limit:
        params["limit"] = int(limit)
    return _coerce_list(zabbix_service.zabbix_request("history.get", params))


# ---------------------------------------------------------------------------
# Alinhamento de séries (EV-0010)
# ---------------------------------------------------------------------------

# Buckets «redondos» (segundos) usados para alinhar amostras de itens que o
# Zabbix coleta em instantes diferentes. O menor é 1 min: é a frequência típica
# de coleta de tráfego/óptico; abaixo disso não há ganho.
BUCKET_LADDER: tuple[int, ...] = (60, 120, 300, 600, 900, 1800, 3600)
DEFAULT_MAX_POINTS = 1500

Sample = tuple[int, float]


def choose_bucket_seconds(span_seconds: int, max_points: int = DEFAULT_MAX_POINTS) -> int:
    """Menor bucket da escada que mantém a série com no máximo ``max_points``.

    24 h a 1 min são 1.440 pontos (cabem); 7 dias a 1 min seriam 10.080 →
    bucket de 10 min (1.008 pontos). Acima da escada, cresce em horas inteiras.
    """
    span = max(int(span_seconds), 1)
    points = max(int(max_points), 1)
    for bucket in BUCKET_LADDER:
        if math.ceil(span / bucket) <= points:
            return bucket
    hours = math.ceil(span / points / 3600)
    return max(3600, hours * 3600)


def history_to_samples(history: Iterable[Mapping[str, Any]]) -> list[Sample]:
    """``history.get`` → ``[(clock, value)]`` ignorando entradas inválidas."""
    samples: list[Sample] = []
    for entry in history or []:
        try:
            samples.append((int(entry["clock"]), float(entry["value"])))
        except (KeyError, TypeError, ValueError):
            continue
    return samples


def merge_series(
    series: Mapping[str, Sequence[Sample]],
    *,
    bucket_seconds: int,
) -> list[dict[str, Any]]:
    """Alinha várias séries por bucket e devolve linhas com ``None`` nos buracos.

    Para cada bucket em que *alguma* série tem amostra sai uma linha
    ``{"timestamp": <ISO UTC do início do bucket>, <nome>: média | None, ...}``.
    Um bucket sem amostra de uma série fica ``None`` — é um buraco real, que o
    gráfico deve mostrar como buraco (nunca forward-fill, que esconde quedas).
    Zero é um valor e é preservado.
    """
    bucket = max(int(bucket_seconds), 1)
    acc: dict[int, dict[str, list[float]]] = {}
    for name, samples in series.items():
        for clock, value in samples:
            key = (int(clock) // bucket) * bucket
            acc.setdefault(key, {}).setdefault(name, []).append(float(value))

    rows: list[dict[str, Any]] = []
    for key in sorted(acc):
        row: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(key, tz=UTC).isoformat(),
        }
        for name in series:
            values = acc[key].get(name)
            row[name] = (sum(values) / len(values)) if values else None
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Um só serviço de séries (EV-0029)
# ---------------------------------------------------------------------------


class AlignedSeries(TypedDict):
    rows: list[dict[str, Any]]
    bucket_seconds: int
    units: dict[str, str]
    samples: dict[str, list[Sample]]


def get_item_by_key(hostid: Any, key: str | None) -> ItemMeta | None:
    """Resolve um item pela ``key_`` num host (``item.get`` com filtro).

    Devolve ``ItemMeta`` (``itemid``, ``value_type``, ``units``) ou ``None`` se
    o host não tem o item — é como as portas ópticas localizam RX/TX quando só
    guardam a chave e não o ``itemid``.
    """
    if not hostid or not key:
        return None
    try:
        raw = zabbix_service.zabbix_request(
            "item.get",
            {
                "hostids": [str(hostid)],
                "filter": {"key_": key},
                "output": ["itemid", "value_type", "units"],
            },
        )
    except Exception:
        logger.warning(
            "zabbix_history.item_by_key_failed",
            extra={"hostid": str(hostid), "key": key},
            exc_info=True,
        )
        return None
    for entry in _coerce_list(raw):
        itemid = str(entry.get("itemid", "")).strip()
        if not itemid:
            continue
        try:
            value_type = int(entry.get("value_type", DEFAULT_VALUE_TYPE))
        except (TypeError, ValueError):
            value_type = DEFAULT_VALUE_TYPE
        return ItemMeta(itemid=itemid, value_type=value_type, units=str(entry.get("units") or ""))
    return None


def fetch_aligned_series(
    items: Mapping[str, Any],
    time_from: int,
    time_till: int,
    *,
    meta: Mapping[str, ItemMeta] | None = None,
    max_points: int = DEFAULT_MAX_POINTS,
) -> AlignedSeries:
    """Histórico de vários itens, já alinhado por bucket — a fachada das 5 rotas.

    ``items`` mapeia o nome da série (``traffic_in``, ``rx_power``…) para o
    ``itemid``; nomes com ``itemid`` vazio saem como série vazia (``None`` em
    todas as linhas). Faz UM ``item.get`` para os tipos/unidades (ou reutiliza
    ``meta``), pede os históricos em paralelo com o ``history`` certo de cada
    item, escolhe o bucket que mantém a saída em ≤ ``max_points`` e alinha com
    ``None`` real nos buracos.

    Não usa o ``limit`` do Zabbix para encolher a série: ``history.get`` corta
    pelo fim da janela (os pontos mais recentes), que é exatamente o que um
    gráfico não pode perder. Quem limita o tamanho é o bucket; quem limita a
    entrada é o tecto do período de cada rota.
    """
    ids = {name: str(item_id) for name, item_id in items.items() if item_id}
    resolved = meta if meta is not None else get_items_meta(ids.values())

    samples: dict[str, list[Sample]] = {name: [] for name in items}
    if ids:
        with ThreadPoolExecutor(max_workers=len(ids)) as pool:
            futures = {
                name: pool.submit(fetch_history, item_id, time_from, time_till, meta=resolved)
                for name, item_id in ids.items()
            }
            for name, future in futures.items():
                samples[name] = history_to_samples(future.result())

    bucket = choose_bucket_seconds(time_till - time_from, max_points)
    return AlignedSeries(
        rows=merge_series(samples, bucket_seconds=bucket),
        bucket_seconds=bucket,
        units={name: meta_or_default(resolved, item_id)["units"] for name, item_id in ids.items()},
        samples=samples,
    )
