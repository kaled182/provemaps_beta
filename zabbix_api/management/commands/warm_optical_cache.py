from django.core.management.base import BaseCommand

from inventory.models import Device, Port
from zabbix_api.domain.optical import _fetch_port_optical_snapshot
from zabbix_api import tasks


class Command(BaseCommand):
    help = "Pré-aquece o cache de potência óptica (RX/TX) das portas monitoradas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--device-id",
            type=int,
            help="Limita o aquecimento a um dispositivo específico.",
        )
        parser.add_argument(
            "--async",
            dest="async_mode",
            action="store_true",
            help="Envia as tarefas para o Celery em vez de executá-las inline.",
        )

    def handle(self, *args, **options):
        device_id = options.get("device_id")
        async_mode = options.get("async_mode")

        if device_id:
            devices = Device.objects.filter(id=device_id)
            if not devices.exists():
                self.stderr.write(self.style.ERROR(f"Dispositivo {device_id} não encontrado."))
                return
        else:
            devices = Device.objects.all()

        total_ports = 0
        for device in devices:
            ports = Port.objects.select_related("device").filter(device=device)
            for port in ports:
                total_ports += 1
                if async_mode:
                    tasks.warm_port_optical_cache.delay(port.id)
                else:
                    _fetch_port_optical_snapshot(port, discovery_cache={}, persist_keys=False)

        if async_mode:
            self.stdout.write(self.style.SUCCESS(f"Enfileiradas tarefas para {total_ports} portas."))
            self.stdout.write("Execute o worker Celery: celery -A core worker -l info")
        else:
            self.stdout.write(self.style.SUCCESS(f"Cache aquecido para {total_ports} portas."))
