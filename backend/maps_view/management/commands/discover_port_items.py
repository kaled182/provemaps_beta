import json
from django.core.management.base import BaseCommand
from maps_view.models import Port
from integrations.zabbix.zabbix_service import zabbix_request

CANDIDATE_STATUS_PATTERNS = [
    'ifoperstatus', 'ifadminstatus', 'net.if.status', 'if.status', 'ifoper', 'link.status'
]
OPTICAL_RX_PATTERNS = ['rxpower', 'lanerxpower', 'opticalrx', 'rx power']
OPTICAL_TX_PATTERNS = ['txpower', 'lanetxpower', 'opticaltx', 'tx power']

class Command(BaseCommand):
    help = 'Tenta descobrir itens de status e pot?ncia ?ptica para Ports sem chaves definidas.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100, help='Limite de ports processados')
        parser.add_argument('--apply', action='store_true', help='Salva automaticamente campos encontrados (sem isso apenas exibe)')
        parser.add_argument('--json', action='store_true', help='Sa?da em JSON')

    def handle(self, *args, **options):
        limit = options['limit']
        apply_changes = options['apply']
        as_json = options['json']

        ports = Port.objects.select_related('device').all()[:limit]
        results = []
        for p in ports:
            hostid = p.device.zabbix_hostid
            if not hostid:
                results.append({'port': str(p), 'reason': 'no_hostid'})
                continue
            # Buscar subset de itens
            items = zabbix_request('item.get', {
                'output': ['itemid', 'key_', 'name', 'lastvalue'],
                'hostids': hostid,
                'filter': {'status': '0'},
                'searchByAny': True,
                'limit': 200
            }) or []
            status_candidate = None
            rx_candidate = None
            tx_candidate = None
            for it in items:
                key_low = (it.get('key_') or '').lower()
                name_low = (it.get('name') or '').lower()
                combined = key_low + ' ' + name_low
                if not status_candidate and any(pat in combined for pat in CANDIDATE_STATUS_PATTERNS):
                    status_candidate = it.get('key_')
                if not rx_candidate and any(pat in combined for pat in OPTICAL_RX_PATTERNS):
                    rx_candidate = it.get('key_')
                if not tx_candidate and any(pat in combined for pat in OPTICAL_TX_PATTERNS):
                    tx_candidate = it.get('key_')
                if status_candidate and rx_candidate and tx_candidate:
                    break
            change = {}
            if status_candidate and not p.zabbix_item_key:
                change['zabbix_item_key'] = status_candidate
            if rx_candidate and not p.rx_power_item_key:
                change['rx_power_item_key'] = rx_candidate
            if tx_candidate and not p.tx_power_item_key:
                change['tx_power_item_key'] = tx_candidate
            applied = False
            if apply_changes and change:
                for field, val in change.items():
                    setattr(p, field, val)
                p.save(update_fields=list(change.keys()))
                applied = True
            results.append({
                'port': str(p),
                'hostid': hostid,
                'changes_detected': change,
                'applied': applied
            })
        if as_json:
            self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                self.stdout.write(f"{r['port']} host={r['hostid']} changes={r['changes_detected']} applied={r['applied']}")
            self.stdout.write(self.style.SUCCESS(f"Ports processados: {len(results)}"))
