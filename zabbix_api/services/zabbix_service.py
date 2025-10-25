# zabbix_api/services/zabbix_service.py
# Servi?o de integra??o Zabbix (JSON-RPC) + utilit?rios de lookup (Fase 1)
# Mant?m comportamento existente, adiciona buscas de host/porta com cache curto.

import json
import logging
import platform
import re
import subprocess
import time
import hashlib
import requests

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

from .zabbix_client import (
    READ_ONLY_SAFE_METHODS,
    clear_token_cache,
    get_current_config as _client_current_config,
    normalize_zabbix_url as _normalize_zabbix_url,
    zabbix_login,
    zabbix_request,
)

logger = logging.getLogger(__name__)


# Utilit?rio de cache seguro para desenvolvimento local
# -----------------------------------------------------------------------------
def safe_cache_get(key, default=None):
    """
    Wrapper seguro para cache.get() que ignora falhas de conex?o Redis.
    Retorna None se Redis estiver offline (modo desenvolvimento).
    """
    try:
        return cache.get(key, default=default)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis indispon?vel), continuando sem cache: %s",
            exc.__class__.__name__,
        )
        return default


def safe_cache_set(key, value, timeout=None):
    """
    Wrapper seguro para cache.set() que ignora falhas de conex?o Redis.
    N?o faz nada se Redis estiver offline (modo desenvolvimento).
    """
    try:
        cache.set(key, value, timeout=timeout)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis indispon?vel), n?o armazenando: %s",
            exc.__class__.__name__,
        )


def safe_cache_delete(key):
    """
    Wrapper seguro para cache.delete() que ignora falhas de conex?o Redis.
    N?o faz nada se Redis estiver offline (modo desenvolvimento).
    """
    try:
        cache.delete(key)
    except Exception as exc:
        logger.debug(
            "Cache offline (Redis indispon?vel), n?o deletando: %s",
            exc.__class__.__name__,
        )


def _current_zabbix_config():
    """
    Wrapper mantido por compatibilidade com testes e chamadas existentes.
    """
    return _client_current_config()

# Utilit?rios / Relat?rios (mantidos)
# -----------------------------------------------------------------------------

def get_host_performance_metrics(hostid):
    """
    Obt?m m?tricas de performance b?sicas de um host.

    Observa??o: Zabbix 'search' n?o aceita lista; para evitar erro,
    fazemos m?ltiplas consultas por termos e unimos os resultados.
    """
    terms = ["system.cpu", "vm.memory", "vfs.fs", "net.if", "disk", "memory", "cpu"]
    seen = set()
    items = []

    for term in terms:
        res = zabbix_request(
            "item.get",
            {
                "output": ["itemid", "name", "key_", "units", "value_type"],
                "hostids": hostid,
                "search": {"key_": term},
                "searchWildcardsEnabled": True,
                "filter": {"status": 0},
                "limit": 200,
            },
        ) or []
        for it in res:
            iid = it.get("itemid")
            if iid and iid not in seen:
                seen.add(iid)
                items.append(it)

    if not items:
        return None

    latest = []
    for it in items:
        hist = zabbix_request(
            "history.get",
            {
                "itemids": it["itemid"],
                "history": it["value_type"],
                "sortfield": "clock",
                "sortorder": "DESC",
                "limit": 1,
            },
        )
        if hist:
            it["latest_value"] = hist[0]["value"]
            it["latest_timestamp"] = hist[0]["clock"]
        latest.append(it)
    return latest


def get_host_problems(hostid):
    """Obt?m problemas recentes de um host."""
    return zabbix_request(
        "problem.get",
        {
            "output": ["eventid", "objectid", "name", "severity", "clock", "acknowledged"],
            "hostids": hostid,
            "recent": True,
            "sortfield": ["eventid"],
            "sortorder": "DESC",
        },
    )


def format_host_data(host_data):
    """Formata dados de host de forma amig?vel."""
    if not host_data:
        return None

    status_map = {"0": "Monitorado", "1": "N?o monitorado"}
    available_map = {"0": "Desconhecido", "1": "Dispon?vel", "2": "Indispon?vel"}

    formatted = []
    for h in host_data:
        formatted.append(
            {
                "hostid": h.get("hostid"),
                "host": h.get("host"),
                "name": h.get("name", h.get("host")),
                "status": {"code": h.get("status", "0"), "description": status_map.get(h.get("status", "0"), "Desconhecido")},
                "available": {
                    "code": h.get("available", "0"),
                    "description": available_map.get(h.get("available", "0"), "Desconhecido"),
                },
                "error": h.get("error", ""),
                "groups": h.get("groups", []),
                "interfaces": h.get("interfaces", []),
                "items_count": len(h.get("items", [])),
                "triggers_count": len(h.get("triggers", [])),
            }
        )
    return formatted


def get_host_network_details(hostid):
    """Informa??es de rede + ?ltimos valores relevantes + problemas do host."""
    try:
        host_info = zabbix_request(
            "host.get",
            {
                "output": ["hostid", "host", "name", "status", "available"],
                "hostids": hostid,
                "selectInterfaces": "extend",
                "selectInventory": "extend",
                "selectMacros": ["macro", "value"],
            },
        )
        if not host_info:
            return None

        host = host_info[0]
        # Coleta alguns itens de rede comuns com m?ltiplas buscas seguras
        terms = ["net.if", "agent.ping", "icmpping", "system.uptime"]
        items = []
        seen = set()
        for term in terms:
            res = zabbix_request(
                "item.get",
                {
                    "output": ["itemid", "name", "key_", "units", "value_type"],
                    "hostids": hostid,
                    "search": {"key_": term},
                    "searchWildcardsEnabled": True,
                    "filter": {"status": "0"},
                    "limit": 200,
                },
            ) or []
            for it in res:
                iid = it.get("itemid")
                if iid and iid not in seen:
                    seen.add(iid)
                    items.append(it)

        network_data = {}
        for it in items:
            try:
                hist = zabbix_request(
                    "history.get",
                    {
                        "itemids": it["itemid"],
                        "history": it["value_type"],
                        "sortfield": "clock",
                        "sortorder": "DESC",
                        "limit": 1,
                    },
                )
                if hist:
                    network_data[it["key_"]] = {"name": it["name"], "value": hist[0]["value"], "timestamp": hist[0]["clock"]}
            except Exception:
                continue

        problems = zabbix_request("problem.get", {"output": ["eventid", "name", "severity", "clock"], "hostids": hostid, "recent": True}) or []

        return {"host_info": host, "network_data": network_data, "problems": problems}
    except Exception:
        return None


def get_geolocation_from_ip(ip_address: str):
    """Geolocalização simples via IP-API (apenas utilitário)."""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.debug("Falha ao consultar IP-API para %s: %s", ip_address, exc)
        return None

    try:
        data = response.json()
    except ValueError as exc:
        logger.debug("Resposta inválida da IP-API para %s: %s", ip_address, exc)
        return None

    if data.get("status") != "success":
        return None

    return {
        "country": data.get("country"),
        "region": data.get("regionName"),
        "city": data.get("city"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "isp": data.get("isp"),
        "timezone": data.get("timezone"),
    }


def check_host_connectivity(ip_address: str) -> bool:
    """
    Verifica conectividade básica (ping) de forma compatível com Windows/Linux/macOS.
    """
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", "3000", ip_address]
    else:
        cmd = ["ping", "-c", "1", "-W", "3", ip_address]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired as exc:
        logger.debug("Ping expirou para %s: %s", ip_address, exc)
        return False
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        logger.debug("Falha ao executar ping para %s: %s", ip_address, exc)
        return False

    return result.returncode == 0


def extract_mac_address_from_items(network_data: dict):
    """Extrai poss?veis MACs de um dicion?rio de itens."""
    macs = []
    for key, data in (network_data or {}).items():
        if "mac" in key.lower() or "hwaddr" in key.lower():
            macs.append({"interface": data.get("name"), "mac": data.get("value")})
    return macs


# -----------------------------------------------------------------------------
# Views utilit?rias existentes (mantidas)
# -----------------------------------------------------------------------------

def get_interfaces(request):
    """
    Lista as interfaces (hostinterface.get) de um host espec?fico.
    Espera: ?hostid=10105
    """
    hostid = request.GET.get("hostid")
    if not hostid:
        return JsonResponse({"error": "Par?metro 'hostid' ? obrigat?rio."}, status=400)

    res = zabbix_request(
        "hostinterface.get",
        {"output": ["interfaceid", "hostid", "ip", "port", "type", "main"], "hostids": hostid},
    )
    if res is None:
        return JsonResponse({"error": "Falha ao consultar o Zabbix."}, status=502)

    return JsonResponse({"interfaces": res}, safe=False)


def translate_interface_status(value: str) -> str:
    """Traduz ifOperStatus num?rico em texto leg?vel."""
    return {
        "1": "UP",
        "2": "DOWN",
        "3": "TESTING",
        "4": "UNKNOWN",
        "5": "DORMANT",
        "6": "NOT PRESENT",
        "7": "LOWER LAYER DOWN",
    }.get(value, "UNKNOWN")


def port_itemid_status(request, itemid):
    """
    Retorna status de um item (porta) por itemid.
    Ex.: /status/52638/
    """
    try:
        result = zabbix_request(
            "item.get",
            {
                "output": [
                    "itemid",
                    "name",
                    "key_",
                    "status",
                    "type",
                    "lastvalue",
                    "units",
                    "valuemapid",
                    "value_type",
                ],
                "itemids": [str(itemid)],
                "limit": 1,
            },
        )
        if result is None:
            return JsonResponse({"error": "Falha na chamada ao Zabbix (item.get)."}, status=502)
        if not result:
            return JsonResponse({"error": f"Nenhum item encontrado com itemid={itemid}."}, status=404)

        item = result[0]
        lastvalue = item.get("lastvalue", "")
        status_text = translate_interface_status(str(lastvalue))

        # Tentativa extra se o mapeamento ficar UNKNOWN
        if status_text == "UNKNOWN":
            retry = zabbix_request(
                "item.get",
                {
                    "output": [
                        "itemid",
                        "name",
                        "key_",
                        "status",
                        "type",
                        "lastvalue",
                        "units",
                        "valuemapid",
                        "value_type",
                    ],
                    "itemids": [str(itemid)],
                    "limit": 1,
                },
            )
            if retry:
                rv = retry[0].get("lastvalue", "")
                rt = translate_interface_status(str(rv))
                if rt != "UNKNOWN":
                    lastvalue = rv
                    status_text = rt

        return JsonResponse(
            {
                "itemid": item.get("itemid"),
                "name": item.get("name"),
                "key_": item.get("key_"),
                "status": item.get("status"),
                "type": item.get("type"),
                "lastvalue": lastvalue,
                "status_description": status_text,
                "units": item.get("units"),
            }
        )
    except Exception as e:
        return JsonResponse({"error": f"Erro inesperado: {e}"}, status=500)


# -----------------------------------------------------------------------------
# LOOKUP ? Fase 1 / Passo 1: buscas de host e interfaces com cache curto
# -----------------------------------------------------------------------------

ZABBIX_LOOKUP_CACHE_TTL = getattr(settings, "ZABBIX_LOOKUP_CACHE_TTL", 30)

AVAILABILITY_STATE_LABELS = {
    "0": ("unknown", "Unknown"),
    "1": ("online", "Online"),
    "2": ("offline", "Offline"),
}


def _extract_host_availability(host: dict, interfaces: list | None = None) -> dict:
    """
    Retorna dicionario com canal (agent/snmp/ipmi/jmx),
    valor (0/1/2), rotulo e mensagem de erro (quando existir).
    Preferencia: SNMP -> Agent -> IPMI -> JMX.
    """
    channels = [
        ("snmp", host.get("snmp_available"), host.get("snmp_error")),
        ("agent", host.get("available"), host.get("error")),
        ("ipmi", host.get("ipmi_available"), host.get("ipmi_error")),
        ("jmx", host.get("jmx_available"), host.get("jmx_error")),
    ]
    for channel, value, err in channels:
        if value in (None, "", "null", "None"):
            continue
        value_str = str(value)
        label_key, human = AVAILABILITY_STATE_LABELS.get(value_str, ("unknown", "Unknown"))
        return {
            "channel": channel,
            "value": value_str,
            "state": label_key,
            "label": human,
            "error": err,
        }
    availability = {
        "channel": None,
        "value": None,
        "state": "unknown",
        "label": "Unknown",
        "error": None,
    }
    iface_list = interfaces if interfaces is not None else (host.get("interfaces") or [])
    if availability["value"] in (None, "", "null", "None") and iface_list:
        primary_iface = next((i for i in iface_list if str(i.get("main")) == "1"), None)
        candidate_ifaces = [primary_iface] if primary_iface else []
        if not candidate_ifaces:
            candidate_ifaces = iface_list[:1]
        for iface in candidate_ifaces:
            if iface is None:
                continue
            iface_value = iface.get("available")
            if iface_value in (None, "", "null", "None"):
                continue
            iface_value_str = str(iface_value)
            if iface_value_str in {"1", "2"}:
                availability = {
                    "channel": "device",
                    "value": iface_value_str,
                    "state": "online" if iface_value_str == "1" else "offline",
                    "label": "Online" if iface_value_str == "1" else "Offline",
                    "error": None,
                }
                break
    return availability
_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def _primary_ip(interfaces):
    if not interfaces:
        return None
    main_if = next((i for i in interfaces if str(i.get("main")) == "1"), None)
    return (main_if or interfaces[0]).get("ip")



def fetch_host_availability(hostid: str) -> dict:
    """
    Consulta o Zabbix e retorna disponibilidade agregada do host,
    incluindo interfaces e canal utilizado.
    """
    params = {
        "hostids": [str(hostid)],
        "output": [
            "hostid",
            "host",
            "name",
            "available",
            "status",
            "error",
            "snmp_available",
            "snmp_error",
            "ipmi_available",
            "ipmi_error",
            "jmx_available",
            "jmx_error",
        ],
        "selectInterfaces": ["interfaceid", "ip", "dns", "main", "available", "port"],
        "limit": 1,
    }
    hosts = zabbix_request("host.get", params=params) or []
    if not hosts:
        return {
            "hostid": str(hostid),
            "availability": {
                "channel": None,
                "value": None,
                "state": "unknown",
                "label": "Unknown",
                "error": None,
            },
            "interfaces": [],
            "primary_interface": None,
        }

    host = hosts[0]
    raw_interfaces = host.get("interfaces") or []
    interfaces = []
    primary = None
    for iface in raw_interfaces:
        payload = {
            "interfaceid": str(iface.get("interfaceid")),
            "ip": iface.get("ip"),
            "dns": iface.get("dns"),
            "port": iface.get("port"),
            "main": str(iface.get("main") or "0"),
            "available": str(iface.get("available")) if iface.get("available") is not None else None,
        }
        interfaces.append(payload)
        if payload["main"] == "1":
            primary = payload
    if not primary and interfaces:
        primary = interfaces[0]
    availability = _extract_host_availability(host, raw_interfaces)
    if availability["state"] == "unknown" and primary and primary.get("available") in {"1", "2"}:
        availability = {
            "channel": "device",
            "value": primary["available"],
            "state": "online" if primary["available"] == "1" else "offline",
            "label": "Online" if primary["available"] == "1" else "Offline",
            "error": None,
        }

    return {
        "hostid": str(hostid),
        "host": host.get("host"),
        "name": host.get("name"),
        "availability": availability,
        "interfaces": interfaces,
        "primary_interface": primary,
    }



def _cache_key(prefix, **parts):
    # Usa hash est?vel (md5) para chaves de cache consistentes entre processos
    raw = "&".join(f"{k}={parts[k]}" for k in sorted(parts.keys()))
    return f"zbx:{prefix}:{hashlib.md5(raw.encode('utf-8')).hexdigest()}"


def search_hosts(query=None, groupids=None, limit=20):
    """
    Busca hosts no Zabbix (host.get) com filtros leves.
    Retorna lista normalizada: [{id, name, host, ip, available, status, error}]
    """
    q = (query or "").strip()
    gids = ",".join(groupids) if isinstance(groupids, (list, tuple)) else (groupids or "")
    key = _cache_key("search_hosts", q=q, gids=gids, limit=int(limit))
    cached = safe_cache_get(key)
    if cached is not None:
        return cached

    params = {
        "output": [
            "hostid",
            "host",
            "name",
            "available",
            "status",
            "error",
            "snmp_available",
            "snmp_error",
            "ipmi_available",
            "ipmi_error",
            "jmx_available",
            "jmx_error",
        ],
        "selectInterfaces": ["interfaceid", "ip", "dns", "main", "port", "available"],
        "limit": int(limit),
    }
    if gids:
        params["groupids"] = gids.split(",") if isinstance(gids, str) else gids

    if q and not _IP_RE.match(q):
        params["search"] = {"name": q}
        params["searchWildcardsEnabled"] = True

    result = zabbix_request("host.get", params=params)

    # Busca por IP via hostinterface.get se necess?rio
    if q and _IP_RE.match(q) and not result:
        if_params = {
            "output": ["interfaceid", "hostid", "ip", "dns", "main", "port", "available"],
            "filter": {"ip": q},
            "limit": 50,
        }
        ifaces = zabbix_request("hostinterface.get", params=if_params) or []
        hostids = list({i["hostid"] for i in ifaces})
        if hostids:
            result = zabbix_request(
                "host.get",
                {
                    "hostids": hostids,
                    "output": [
                        "hostid",
                        "host",
                        "name",
                        "available",
                        "status",
                        "error",
                        "snmp_available",
                        "snmp_error",
                        "ipmi_available",
                        "ipmi_error",
                        "jmx_available",
                        "jmx_error",
                    ],
                    "selectInterfaces": ["interfaceid", "ip", "dns", "main", "port", "available"],
                    "limit": int(limit),
                },
            )

    normalized = []
    for h in result or []:
        interfaces = h.get("interfaces") or []
        availability = _extract_host_availability(h, interfaces)
        normalized.append(
            {
                "id": str(h.get("hostid")),
                "host": h.get("host"),
                "name": h.get("name"),
                "ip": _primary_ip(interfaces),
                "available": availability["value"],
            "status": h.get("status"),
            "error": h.get("error"),
            "availability": availability,
        }
    )

    safe_cache_set(key, normalized, ZABBIX_LOOKUP_CACHE_TTL)
    return normalized
def get_host_interfaces(hostid, only_main: bool = False, limit: int = 200):
    """
    Lista interfaces de um host. Retorna:
    [{interfaceid, ip, dns, main, port, available, type, useip}]
    """
    hostid = str(hostid)
    key = _cache_key("host_if", hostid=hostid, main=int(bool(only_main)), limit=int(limit))
    cached = safe_cache_get(key)
    if cached is not None:
        return cached

    params = {
        "output": ["interfaceid", "ip", "dns", "main", "port", "available", "type", "useip"],
        "hostids": [hostid],
        "limit": int(limit),
    }
    res = zabbix_request("hostinterface.get", params=params) or []
    if only_main:
        res = [i for i in res if str(i.get("main")) == "1"]

    out = []
    for i in res:
        out.append(
            {
                "interfaceid": str(i.get("interfaceid")),
                "ip": i.get("ip"),
                "dns": i.get("dns"),
                "main": int(i.get("main") or 0),
                "port": str(i.get("port") or ""),
                "available": int(i.get("available") or 0),
            "type": int(i.get("type") or 0),
            "useip": int(i.get("useip") or 1),
        }
    )

    safe_cache_set(key, out, ZABBIX_LOOKUP_CACHE_TTL)
    return out
# -----------------------------------------------------------------------------
# LOOKUP ? Fase 1: fun??es auxiliares opcionais (seguras)
# -----------------------------------------------------------------------------

def search_hosts_by_name_ip(query: str, groupids=None, limit: int = 20):
    """
    Busca hosts por nome ou IP com dados enriquecidos (grupos/descrição).
    Implementada com chamadas válidas ao Zabbix (sem 'search' com lista).
    """
    cache_key = _cache_key("host_search_ext", q=query or "", gids=str(groupids or ""), limit=int(limit))
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    base_output = [
        "hostid",
        "host",
        "name",
        "available",
        "status",
        "error",
        "description",
        "snmp_available",
        "snmp_error",
        "ipmi_available",
        "ipmi_error",
        "jmx_available",
        "jmx_error",
    ]
    params = {
        "output": base_output,
        "selectInterfaces": ["interfaceid", "ip", "dns", "main", "port", "available"],
        "selectGroups": ["groupid", "name"],
        "limit": int(limit),
    }
    if groupids:
        params["groupids"] = groupids

    # 1) tenta por nome
    if query and not _IP_RE.match(query):
        p = dict(params)
        p["search"] = {"name": query}
        p["searchWildcardsEnabled"] = True
        hosts = zabbix_request("host.get", p) or []
    else:
        hosts = []

    # 2) se não achou e parecer IP, resolve via hostinterface.get
    if (not hosts) and query and _IP_RE.match(query):
        ifaces = zabbix_request(
            "hostinterface.get",
            {"output": ["interfaceid", "hostid", "ip", "dns", "main"], "filter": {"ip": query}, "limit": int(limit)},
        ) or []
        if ifaces:
            host_ids = list({i["hostid"] for i in ifaces})
            hosts = zabbix_request(
                "host.get",
                {
                    "hostids": host_ids,
                    "output": base_output,
                    "selectInterfaces": ["interfaceid", "ip", "dns", "main", "port", "available"],
                    "selectGroups": ["groupid", "name"],
                },
            ) or []

    normalized = []
    for h in hosts:
        interfaces = h.get("interfaces", [])
        availability = _extract_host_availability(h, interfaces)
        primary_ip = _primary_ip(interfaces)
        groups = [g["name"] for g in h.get("groups", [])]
        normalized.append(
            {
                "hostid": h["hostid"],
                "host": h["host"],
                "name": h.get("name", h["host"]),
                "ip": primary_ip,
                "available": availability["value"],
                "status": h.get("status", "0"),
                "error": h.get("error", ""),
                "description": h.get("description", ""),
                "groups": groups,
                "interfaces_count": len(interfaces),
                "availability": availability,
            }
        )

    safe_cache_set(cache_key, normalized, ZABBIX_LOOKUP_CACHE_TTL)
    return normalized


def get_host_interfaces_detailed(hostid: str, include_snmp_info: bool = False):
    """
    Interfaces do host com dados b?sicos. Por padr?o N?O tenta SNMP,
    pois 'hostinterface.port' N?O ? ifIndex e n?o ? seguro inferir.
    """
    cache_key = _cache_key("host_if_detailed", hostid=str(hostid), snmp=int(bool(include_snmp_info)))
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    interfaces = zabbix_request(
        "hostinterface.get",
        {
            "output": ["interfaceid", "hostid", "ip", "dns", "port", "type", "main", "available", "useip"],
            "hostids": [str(hostid)],
            "limit": 200,
        },
    ) or []

    detailed = []
    for i in interfaces:
        detailed.append(
            {
                "interfaceid": i.get("interfaceid"),
                "hostid": i.get("hostid"),
                "ip": i.get("ip", ""),
                "dns": i.get("dns", ""),
                "port": i.get("port", ""),
                "type": i.get("type", "1"),
            "main": i.get("main", "0"),
            "available": i.get("available", "0"),
            "useip": i.get("useip", "1"),
            "snmp_data": {},  # intencionalmente vazio nesta fase
        }
    )

    safe_cache_set(cache_key, detailed, ZABBIX_LOOKUP_CACHE_TTL)
    return detailed
def get_interface_snmp_details(interfaceid: str, snmpindex: str = None):
    """
    Detalhes SNMP de uma interface.
    Para ser correto, requer 'snmpindex' (ifIndex). Se n?o fornecido, retorna apenas metadados b?sicos.
    """
    # 1) Metadados b?sicos da hostinterface
    iface = zabbix_request(
        "hostinterface.get",
        {"output": ["interfaceid", "hostid", "ip", "dns", "port", "type", "main", "available"], "interfaceids": [str(interfaceid)]},
    )
    if not iface:
        return None

    info = {"interface": iface[0], "snmp_data": {}}

    # 2) Sem snmpindex, n?o tentamos buscar itens SNMP (evita erros)
    if not snmpindex:
        return info

    # 3) Busca itens do host com sufixo .{snmpindex} e filtra no Python (modelo seguro)
    items = zabbix_request(
        "item.get",
        {
            "output": ["itemid", "name", "key_", "lastvalue", "units", "lastclock"],
            "hostids": [str(info["interface"]["hostid"])],
            "search": {"key_": f".{snmpindex}"},
            "searchWildcardsEnabled": True,
            "filter": {"status": "0"},
            "limit": 500,
        },
    ) or []

    for it in items:
        key = it.get("key_", "")
        val = it.get("lastvalue")
        if f"ifAlias.{snmpindex}" in key:
            info["snmp_data"]["alias"] = val
        elif f"ifName.{snmpindex}" in key:
            info["snmp_data"]["name"] = val
        elif f"ifDescr.{snmpindex}" in key:
            info["snmp_data"]["description"] = val
        elif f"ifOperStatus.{snmpindex}" in key:
            info["snmp_data"]["oper_status"] = val
        elif f"ifAdminStatus.{snmpindex}" in key:
            info["snmp_data"]["admin_status"] = val
        elif f"ifSpeed.{snmpindex}" in key:
            info["snmp_data"]["speed"] = f"{val} {it.get('units', '')}"
        elif "ifHCInOctets" in key or "ifInOctets" in key:
            info["snmp_data"]["rx_bytes"] = val
        elif "ifHCOutOctets" in key or "ifOutOctets" in key:
            info["snmp_data"]["tx_bytes"] = val

    return info


def test_host_connectivity(hostid: str):
    """
    Testa conectividade de um host (disponibilidade Zabbix + ping opcional).
    """
    cache_key = _cache_key("host_connectivity", hostid=str(hostid))
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    host_data = zabbix_request(
        "host.get",
        {
            "output": ["hostid", "host", "name", "available", "error"],
            "selectInterfaces": ["interfaceid", "ip", "available", "main"],
            "hostids": [str(hostid)],
            "limit": 1,
        },
    )

    if not host_data:
        return {"status": "error", "message": "Host n?o encontrado"}

    host = host_data[0]
    interfaces = host.get("interfaces", []) or []
    primary = next((i for i in interfaces if str(i.get("main")) == "1"), interfaces[0] if interfaces else None)

    result = {
        "hostid": hostid,
        "host": host.get("host"),
        "name": host.get("name", host.get("host")),
        "zabbix_available": host.get("available", "0"),
        "zabbix_error": host.get("error", ""),
        "primary_interface": primary,
    }

    # ping opcional
    if primary and primary.get("ip"):
        ip = primary["ip"]
        result["ping_test"] = {"ip": ip, "reachable": check_host_connectivity(ip), "timestamp": time.time()}

    safe_cache_set(cache_key, result, 60)  # curto
    return result


