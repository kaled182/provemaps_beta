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
from collections.abc import Iterable, Mapping
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
