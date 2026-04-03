#!/usr/bin/env python
"""
Script para configurar emenda de reparo: mesmo cabo entra e sai da CEO.

Uso:
    docker compose exec web python /docker/attach_repair_cable.py

Cenário:
    Cabo rompido → duas pontas do mesmo cabo chegam na CEO
    - Ponta A → port_type='oval' (entrada)
    - Ponta B → port_type='round' (saída)
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberInfrastructure, FiberCable, InfrastructureCableAttachment


def attach_repair_cable():
    """Configura cabo de reparo: mesmo cabo nos dois lados da CEO"""
    
    # Buscar CEO e cabo
    try:
        ceo = FiberInfrastructure.objects.get(name__icontains='2098')  # CEO-2098
    except FiberInfrastructure.DoesNotExist:
        print("❌ CEO não encontrada (buscando por '2098' no nome)")
        return
    
    try:
        cable = FiberCable.objects.get(name__icontains='asdasdsa')
    except FiberCable.DoesNotExist:
        print("❌ Cabo 'asdasdsa' não encontrado")
        return
    
    print(f"✅ CEO: {ceo.name} (ID: {ceo.id})")
    print(f"✅ Cabo: {cable.name} (ID: {cable.id})")
    
    # Limpar attachments anteriores
    InfrastructureCableAttachment.objects.filter(infrastructure=ceo, cable=cable).delete()
    print("🧹 Attachments anteriores removidos")
    
    # Criar attachment de ENTRADA (ponta A do cabo rompido)
    att_entrada = InfrastructureCableAttachment.objects.create(
        infrastructure=ceo,
        cable=cable,
        port_type='oval',  # Porta oval = passagem/entrada
        is_pass_through=False
    )
    print(f"✅ Attachment ENTRADA criado: {att_entrada.id} (port_type=oval)")
    
    # Criar attachment de SAÍDA (ponta B do cabo rompido)
    att_saida = InfrastructureCableAttachment.objects.create(
        infrastructure=ceo,
        cable=cable,
        port_type='round',  # Porta redonda = derivação/saída
        is_pass_through=False
    )
    print(f"✅ Attachment SAÍDA criado: {att_saida.id} (port_type=round)")
    
    print("\n" + "="*60)
    print("🎯 CONFIGURAÇÃO CONCLUÍDA!")
    print("="*60)
    print(f"Cabo '{cable.name}' agora aparece DOS DOIS LADOS na CEO:")
    print(f"  • ENTRADA (esquerda): attachment_id={att_entrada.id}, port_type=oval")
    print(f"  • SAÍDA (direita):    attachment_id={att_saida.id}, port_type=round")
    print("\nAgora você pode fusionar:")
    print("  Verde(Entrada) ↔ Verde(Saída)")
    print("  Laranja(Entrada) ↔ Laranja(Saída)")
    print("  etc.")
    print("="*60)


if __name__ == '__main__':
    attach_repair_cable()
