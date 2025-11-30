#!/usr/bin/env python
"""
Remove attachments obsoletos da CEO-2098 que causam duplicação.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import InfrastructureCableAttachment

# Delete all attachments from CEO-2098 (sistema agora usa apenas segmentos)
deleted = InfrastructureCableAttachment.objects.filter(infrastructure_id=25).delete()

print(f"Deletados: {deleted[0]} attachments")
print("CEO-2098 agora usa apenas segmentos!")
