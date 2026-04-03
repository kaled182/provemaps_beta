#!/usr/bin/env python
"""
Teste rápido: verifica se os cabos têm coordenadas no serializer
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from inventory.models import FiberCable
from inventory.serializers import FiberCableSerializer

cables = FiberCable.objects.all()[:3]

print(f"\nTotal de cabos: {FiberCable.objects.count()}")
print("\nTestando serialização dos primeiros 3 cabos:\n")

for cable in cables:
    serializer = FiberCableSerializer(cable)
    data = serializer.data
    coords = data.get('path_coordinates', [])
    
    print(f"Cabo ID: {cable.id}")
    print(f"Nome: {cable.name}")
    print(f"Path (PostGIS): {'Sim' if cable.path else 'Não'}")
    print(f"Coordenadas no serializer: {len(coords)} pontos")
    if coords:
        print(f"Primeiro ponto: {coords[0]}")
        print(f"Último ponto: {coords[-1]}")
    print("-" * 60)
