#!/usr/bin/env python
"""
Script para criar segmentos no cabo 'asdasdsa' com CEO-2098.

Converte o modelo antigo (attachments) para o novo (segments).
"""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, FiberInfrastructure, CableSegment
from django.db import transaction
from django.db.models import Count


def create_segments():
    """Criar segmentos para o cabo de teste"""
    
    try:
        cable = FiberCable.objects.get(name__icontains='asdasdsa')
        ceo = FiberInfrastructure.objects.get(name__icontains='2098')
    except (FiberCable.DoesNotExist, FiberInfrastructure.DoesNotExist) as e:
        print(f"❌ Erro: {e}")
        return
    
    print(f"✅ Cabo: {cable.name} (ID: {cable.id})")
    print(f"✅ CEO: {ceo.name} (ID: {ceo.id})")
    print(f"📍 CEO posição: {ceo.distance_from_origin:.0f}m do início")
    
    with transaction.atomic():
        # Limpar segmentos anteriores
        CableSegment.objects.filter(cable=cable).delete()
        print("🧹 Segmentos anteriores removidos")
        
        # Criar Segmento 1: Início → CEO
        seg1 = CableSegment.objects.create(
            cable=cable,
            segment_number=1,
            name=f"{cable.name}-Seg1",
            start_infrastructure=None,  # TODO: mapear Site A se existir
            end_infrastructure=ceo,
            length_meters=ceo.distance_from_origin
        )
        print(f"✅ Segmento 1 criado: 0m → CEO ({seg1.length_meters:.0f}m)")
        
        # Criar Segmento 2: CEO → Fim
        total_length = float(cable.length_km or 1) * 1000
        seg2_length = total_length - ceo.distance_from_origin
        
        seg2 = CableSegment.objects.create(
            cable=cable,
            segment_number=2,
            name=f"{cable.name}-Seg2",
            start_infrastructure=ceo,
            end_infrastructure=None,  # TODO: mapear Site B se existir
            length_meters=seg2_length
        )
        print(f"✅ Segmento 2 criado: CEO → {total_length:.0f}m ({seg2.length_meters:.0f}m)")
        
            # Associar fibras ao Seg1
            count = 0
        for tube in cable.tubes.all():
            for strand in tube.strands.all():
                strand.segment = seg1
                strand.save(update_fields=['segment'])
                    count += 1
        
            print(f"✅ {count} fibras associadas ao Seg1")
        
        print("\n" + "="*60)
        print("🎯 SEGMENTAÇÃO CONCLUÍDA!")
        print("="*60)
        print(f"Cabo '{cable.name}' agora tem 2 segmentos:")
        print(f"  • Seg1 (Entrada): 0m → CEO ({seg1.length_meters:.0f}m)")
        print(f"  • Seg2 (Saída):   CEO → Fim ({seg2.length_meters:.0f}m)")
        print("\nAgora você pode fusionar fibras entre segmentos:")
        print(f"  Seg1-FO1 ↔ Seg2-FO1")
        print(f"  Seg1-FO2 ↔ Seg2-FO2")
        print("  etc.")
if __name__ == '__main__':
    create_segments()
