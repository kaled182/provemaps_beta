from django.db import models
from django.utils import timezone


class Site(models.Model):
	name = models.CharField(max_length=120, unique=True)
	city = models.CharField(max_length=120, blank=True)
	latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	description = models.TextField(blank=True)

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name


class Device(models.Model):
	site = models.ForeignKey(Site, related_name="devices", on_delete=models.CASCADE)
	name = models.CharField(max_length=120)
	vendor = models.CharField(max_length=120, blank=True)
	model = models.CharField(max_length=120, blank=True)
	zabbix_hostid = models.CharField(max_length=32, blank=True, help_text="hostid no Zabbix")

	class Meta:
		unique_together = ("site", "name")
		ordering = ["site__name", "name"]

	def __str__(self):
		return f"{self.site.name} - {self.name}" if self.site_id else self.name


class Port(models.Model):
	device = models.ForeignKey(Device, related_name="ports", on_delete=models.CASCADE)
	name = models.CharField(max_length=64)
	zabbix_item_key = models.CharField(max_length=255, blank=True, help_text="Chave item/interface no Zabbix (ex: net.if.in[ether10])")
	zabbix_interfaceid = models.CharField(max_length=32, blank=True, help_text="interfaceid no Zabbix")
	# Itens de pot?ncia ?ptica (RX/TX) opcionais para inferir status quando n?o h? ifOperStatus
	rx_power_item_key = models.CharField(max_length=255, blank=True, help_text="Item de pot?ncia ?ptica RX (ex: hwEntityOpticalLaneRxPower[ID])")
	tx_power_item_key = models.CharField(max_length=255, blank=True, help_text="Item de pot?ncia ?ptica TX (ex: hwEntityOpticalLaneTxPower[ID])")
	notes = models.CharField(max_length=255, blank=True)

	class Meta:
		unique_together = ("device", "name")
		ordering = ["device__site__name", "device__name", "name"]

	def __str__(self):
		return f"{self.device}::{self.name}"


class FiberCable(models.Model):
	STATUS_UP = "up"
	STATUS_DOWN = "down"
	STATUS_DEGRADED = "degraded"
	STATUS_UNKNOWN = "unknown"
	STATUS_CHOICES = [
		(STATUS_UP, "Operacional"),
		(STATUS_DOWN, "Indispon?vel"),
		(STATUS_DEGRADED, "Degradado"),
		(STATUS_UNKNOWN, "Desconhecido"),
	]

	name = models.CharField(max_length=150, unique=True)
	origin_port = models.ForeignKey(Port, related_name="fiber_origin", on_delete=models.PROTECT)
	destination_port = models.ForeignKey(Port, related_name="fiber_destination", on_delete=models.PROTECT)
	length_km = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
	# Lista de coordenadas intermedi?rias para tra?ar rota (inclui origem e destino opcionalmente)
	path_coordinates = models.JSONField(blank=True, null=True, help_text="Lista de pontos [{'lat': -16.6, 'lng': -49.2}, ...]")
	status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_UNKNOWN)
	last_status_update = models.DateTimeField(null=True, blank=True)
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name

	def update_status(self, new_status: str):
		if new_status not in dict(self.STATUS_CHOICES):
			new_status = self.STATUS_UNKNOWN
		self.status = new_status
		self.last_status_update = timezone.now()
		self.save(update_fields=["status", "last_status_update"])


class FiberEvent(models.Model):
	fiber = models.ForeignKey(FiberCable, related_name="events", on_delete=models.CASCADE)
	timestamp = models.DateTimeField(default=timezone.now)
	previous_status = models.CharField(max_length=15, blank=True)
	new_status = models.CharField(max_length=15)
	detected_reason = models.CharField(max_length=255, blank=True)

	class Meta:
		ordering = ["-timestamp"]

	def __str__(self):
		return f"{self.fiber.name} {self.previous_status}->{self.new_status} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"

