from __future__ import annotations
"""L?gica reutiliz?vel para obten??o e combina??o de status de fibras.

Extra?da/refatorada de `maps_view.views` para ser usada tamb?m por management commands
(e.g. update_fiber_status) e eventuais tarefas agendadas.

Fun??es principais:
- fetch_interface_status_advanced(hostid, primary_item_key=None, interfaceid=None, rx_key=None, tx_key=None)
- combine_cable_status(origin_status, destination_status)
- evaluate_cable_status_for_cable(fiber_cable) -> dict com detalhes e status combinado

Heur?sticas:
1. Tenta item prim?rio (ex: ifOperStatus) se fornecido.
2. Fallback: tenta descobrir itens de pot?ncia ?ptica RX/TX (informados ou via interfaceid)
3. Aplica threshold simples para determinar down por pot?ncia muito baixa.

Retorna sempre metadados (reason) para auditoria.
"""
from typing import Tuple, Dict, Any
from zabbix_api.services.zabbix_service import zabbix_request

UP_VALUES = {"1", 1}
DOWN_VALUES = {"2", 2, "0", 0}


def interpret_item_value(value):
    if value in UP_VALUES:
        return 'up'
    if value in DOWN_VALUES:
        return 'down'
    return 'unknown'


def fetch_interface_status_advanced(hostid: str | int | None,
                                     primary_item_key: str | None = None,
                                     interfaceid: str | int | None = None,
                                     rx_key: str | None = None,
                                     tx_key: str | None = None) -> Tuple[str, Dict[str, Any]]:
    """Retorna (status, reason_dict). L?gica unificada para uso em views e comandos.
    """
    if not hostid:
        return 'unknown', {'error': 'missing_hostid'}

    def _get_item(key):
        if not key:
            return None
        items = zabbix_request('item.get', {
            'output': ['itemid', 'key_', 'lastvalue', 'value_type', 'name'],
            'hostids': hostid,
            'search': {'key_': key},
            'searchByAny': True,
            'limit': 1
        })
        return items[0] if items else None

    # 1. Item prim?rio
    primary_item = _get_item(primary_item_key) if primary_item_key else None
    if primary_item:
        raw = primary_item.get('lastvalue')
        if raw is not None:
            interpreted = interpret_item_value(raw)
            return interpreted, {'method': 'primary_item', 'key': primary_item.get('key_'), 'raw': raw}
        # Tenta hist?rico
        hist = zabbix_request('history.get', {
            'itemids': primary_item['itemid'],
            'history': primary_item.get('value_type', 3),
            'sortfield': 'clock', 'sortorder': 'DESC', 'limit': 1
        })
        if hist:
            raw = hist[0].get('value')
            interpreted = interpret_item_value(raw)
            return interpreted, {'method': 'primary_item_history', 'key': primary_item.get('key_'), 'raw': raw}

    # 2. Fallback ?ptico (RX/TX)
    discovered = {}
    rx_item = _get_item(rx_key)
    tx_item = _get_item(tx_key)

    if (not rx_item and not tx_item) and interfaceid:
        candidate_items = zabbix_request('item.get', {
            'output': ['itemid', 'key_', 'lastvalue', 'value_type', 'name'],
            'interfaceids': [interfaceid],
            'filter': {'status': '0'},
        }) or []
        rx_patterns = ['rxpower', 'lanerxpower', 'opticalrx', 'rx low', 'rx high']
        tx_patterns = ['txpower', 'lanetxpower', 'opticaltx', 'tx low', 'tx high']

        def match_any(text, patterns):
            t = text.lower()
            return any(p in t for p in patterns)

        for it in candidate_items:
            combined = f"{(it.get('key_') or '').lower()} {(it.get('name') or '').lower()}"
            if not rx_item and match_any(combined, rx_patterns) and 'tx' not in combined:
                rx_item = it
                discovered['rx_key'] = it.get('key_')
            elif not tx_item and match_any(combined, tx_patterns) and 'rx' not in combined:
                tx_item = it
                discovered['tx_key'] = it.get('key_')
            if rx_item and tx_item:
                break
        if not rx_item and not tx_item:
            for it in candidate_items:  # fallback gen?rico
                key_low = (it.get('key_') or '').lower()
                if not rx_item and 'rx' in key_low:
                    rx_item = it
                    discovered['rx_key_generic'] = it.get('key_')
                if not tx_item and 'tx' in key_low:
                    tx_item = it
                    discovered['tx_key_generic'] = it.get('key_')
                if rx_item and tx_item:
                    break
        if discovered:
            discovered['auto_discovered'] = True

    if not rx_item and not tx_item:
        reason = {'method': 'no_items_found'}
        if interfaceid:
            reason['interfaceid'] = interfaceid
            reason['auto_discovery_attempt'] = True
        return 'unknown', reason

    def _parse_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    rx_val = _parse_float(rx_item.get('lastvalue')) if rx_item else None
    tx_val = _parse_float(tx_item.get('lastvalue')) if tx_item else None

    threshold_down = -50  # dBm (ajust?vel futuramente via settings)
    if rx_val is not None or tx_val is not None:
        values = [v for v in (rx_val, tx_val) if v is not None]
        if values and all(v < threshold_down for v in values):
            meta = {'method': 'optical_power', 'rx': rx_val, 'tx': tx_val, 'threshold': threshold_down}
            meta.update(discovered)
            return 'down', meta
        meta = {'method': 'optical_power', 'rx': rx_val, 'tx': tx_val, 'threshold': threshold_down}
        meta.update(discovered)
        return 'up', meta

    meta = {'method': 'optical_power_no_values'}
    meta.update(discovered)
    return 'unknown', meta


def combine_cable_status(origin_status: str, dest_status: str) -> str:
    if origin_status == 'up' and dest_status == 'up':
        return 'up'
    if origin_status == 'down' and dest_status == 'down':
        return 'down'
    if (origin_status == 'up' and dest_status == 'down') or (origin_status == 'down' and dest_status == 'up'):
        return 'degraded'
    return 'unknown'


def evaluate_cable_status_for_cable(cable) -> Dict[str, Any]:
    """Recebe instancia de FiberCable e retorna dict com detalhes de avalia??o.
    N?o persiste altera??es; apenas calcula.
    """
    o_dev = cable.origin_port.device
    d_dev = cable.destination_port.device
    o_status, o_reason = fetch_interface_status_advanced(
        o_dev.zabbix_hostid,
        primary_item_key=cable.origin_port.zabbix_item_key,
        interfaceid=cable.origin_port.zabbix_interfaceid,
        rx_key=cable.origin_port.rx_power_item_key,
        tx_key=cable.origin_port.tx_power_item_key,
    )
    d_status, d_reason = fetch_interface_status_advanced(
        d_dev.zabbix_hostid,
        primary_item_key=cable.destination_port.zabbix_item_key,
        interfaceid=cable.destination_port.zabbix_interfaceid,
        rx_key=cable.destination_port.rx_power_item_key,
        tx_key=cable.destination_port.tx_power_item_key,
    )
    combined = combine_cable_status(o_status, d_status)

    # Fallback extra: se ambos unknown tentar disponibilidade de host (host.available)
    if combined == 'unknown' and o_status == 'unknown' and d_status == 'unknown':
        host_av_origin = _host_availability_status(o_dev.zabbix_hostid)
        host_av_dest = _host_availability_status(d_dev.zabbix_hostid)
        if host_av_origin != 'unknown' or host_av_dest != 'unknown':
            # Se s? um conhecido, mant?m unknown? Vamos aplicar mesma combina??o.
            fallback_combined = combine_cable_status(host_av_origin, host_av_dest)
            if fallback_combined != 'unknown':
                combined = fallback_combined
                # Adicionar motivos de fallback
                o_reason = {'method': 'host_availability_fallback', 'host_available': host_av_origin}
                d_reason = {'method': 'host_availability_fallback', 'host_available': host_av_dest}
                o_status = host_av_origin
                d_status = host_av_dest

    return {
        'origin_status': o_status,
        'destination_status': d_status,
        'origin_reason': o_reason,
        'destination_reason': d_reason,
        'combined_status': combined,
        'previous_status': cable.status,
        'changed': combined != cable.status,
    }


def _host_availability_status(hostid) -> str:
    if not hostid:
        return 'unknown'
    data = zabbix_request('host.get', {
        'output': ['hostid', 'available'],
        'hostids': hostid,
        'limit': 1
    }) or []
    if not data:
        return 'unknown'
    code = str(data[0].get('available', '0'))
    if code == '1':
        return 'up'
    if code == '2':
        return 'down'
    return 'unknown'


def get_oper_status_from_zabbix(device, port_name):
    """
    Consulta o status operacional da porta via Zabbix, usando value mapping.
    Retorna: (status, valor, mapeamento_dict)
    """
    from zabbix_api.services.zabbix_service import zabbix_request
    item_key = f"ifOperStatus[{port_name}]"
    items = zabbix_request('item.get', {
        'output': ['itemid', 'key_', 'lastvalue', 'valuemapid', 'value_type', 'name'],
        'hostids': device.zabbix_hostid,
        'search': {'key_': item_key},
        'searchByAny': True,
        'limit': 1
    }) or []
    if not items:
        return ('unknown', None, {})
    item = items[0]
    valuemapid = item.get('valuemapid')
    # Busca mapeamento
    valuemap = None
    if valuemapid:
        maps = zabbix_request('valuemap.get', {'output': 'extend', 'valuemapids': [valuemapid]}) or []
        if maps:
            valuemap = {e['value']: e['newvalue'] for e in maps[0].get('mappings',[])}
    # Valor atual
    raw = item.get('lastvalue')
    if raw is None:
        hist = zabbix_request('history.get', {
            'itemids': item['itemid'],
            'history': item.get('value_type', 3),
            'sortfield': 'clock', 'sortorder': 'DESC', 'limit': 1
        }) or []
        if hist:
            raw = hist[0].get('value')
    # Interpreta??o
    status = 'unknown'
    if raw == '1':
        status = 'up'
    elif raw == '2':
        status = 'down'
    return (status, raw, valuemap or {})
