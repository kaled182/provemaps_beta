"""
Script para converter cabos existentes em segmentos com parent_cable.
Isto atualiza cabos já rompidos para usar o novo sistema de parent_cable.
"""

from django.db import transaction
from inventory.models import FiberCable, InfrastructureCableAttachment

def fix_cable_segments():
    """
    Encontra cabos que parecem ser segmentos (nome termina em _A, _B, etc)
    e tenta associá-los ao cabo pai.
    """
    
    # Encontrar possíveis segmentos
    potential_segments = FiberCable.objects.filter(
        name__regex=r'.*[_\s](A|B|1|2)$'
    ).exclude(
        parent_cable__isnull=False  # Já tem parent
    )
    
    print(f"Encontrados {potential_segments.count()} possíveis segmentos")
    
    for segment in potential_segments:
        # Tentar encontrar o cabo pai baseado no nome
        # Ex: "TESTE_A" -> buscar "TESTE"
        parent_name = segment.name.rsplit('_', 1)[0].rsplit(' ', 1)[0]
        
        try:
            parent = FiberCable.objects.get(name=parent_name)
            
            with transaction.atomic():
                segment.parent_cable = parent
                segment.save()
                print(f"✓ Associado {segment.name} -> {parent.name}")
                
        except FiberCable.DoesNotExist:
            print(f"✗ Cabo pai '{parent_name}' não encontrado para {segment.name}")
        except FiberCable.MultipleObjectsReturned:
            print(f"✗ Múltiplos cabos '{parent_name}' encontrados para {segment.name}")

if __name__ == "__main__":
    fix_cable_segments()
