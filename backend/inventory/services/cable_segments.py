"""
Serviço para gerenciamento de segmentos de cabo.

Handles:
- Criação automática de segmentos ao adicionar CEO
- Quebra de cabos em trechos lógicos
- Reassociação de fibras aos segmentos corretos
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from inventory.models import FiberCable, FiberInfrastructure, CableSegment


def create_initial_segment(cable: 'FiberCable') -> 'CableSegment':
    """
    Cria segmento inicial para um cabo sem segmentação.
    
    Args:
        cable: Cabo físico
        
    Returns:
        Segmento criado (Seg1: origem → destino completo)
    """
    from inventory.models import CableSegment
    
    segment = CableSegment.objects.create(
        cable=cable,
        segment_number=1,
        name=f"{cable.name}-Seg1",
        # Infraestrutura será mapeada quando implementarmos:
        # - Associação automática Site A ↔ origin_port.device.site
        # - Associação automática Site B ↔ destination_port.device.site  
        # Por ora, None é válido para segmentos sem infra mapeada
        start_infrastructure=None,  # Future: mapear Site A automaticamente
        end_infrastructure=None,    # Future: mapear Site B automaticamente
        length_meters=float(cable.length_km or 0) * 1000 if cable.length_km else 0
    )
    
    # Associar todas as fibras do cabo a este segmento
    # Corrige: relacionamento é via FiberStrand -> BufferTube -> FiberCable
    from inventory.models import FiberStrand
    FiberStrand.objects.filter(
        tube__cable=cable,
        segment__isnull=True
    ).update(segment=segment)
    
    return segment


def split_segment_at_ceo(
    segment: 'CableSegment',
    ceo: 'FiberInfrastructure',
    distance_from_start: float
) -> tuple['CableSegment', 'CableSegment']:
    """
    Quebra um segmento em dois ao adicionar CEO intermediária.
    
    Args:
        segment: Segmento a ser dividido
        ceo: CEO que está sendo inserida
        distance_from_start: Distância da CEO em relação ao início do segmento (metros)
        
    Returns:
        Tupla (seg_before, seg_after)
        
    Exemplo:
        Seg1 (1000m) dividido na CEO-01 (500m):
          → Seg1 (0→500m) + Seg2 (500→1000m)
    """
    from inventory.models import CableSegment
    
    with transaction.atomic():
        cable = segment.cable
        
        # Calcular comprimentos
        length_before = distance_from_start
        length_after = segment.length_meters - distance_from_start
        
        original_end = segment.end_infrastructure

        # Renomear segmento existente (será o "antes")
        segment.name = f"{cable.name}-Seg{segment.segment_number}"
        segment.end_infrastructure = ceo
        segment.length_meters = length_before
        segment.save(update_fields=['name', 'end_infrastructure', 'length_meters'])
        
        # CRITICAL: Renumerar segmentos posteriores ANTES de criar o novo
        # Fazemos em ordem decrescente para evitar colisão de chave única
        later_segments = (
            CableSegment.objects.filter(
                cable=cable,
                segment_number__gt=segment.segment_number
            )
            .order_by('-segment_number')
            .select_for_update()
        )

        for seg in later_segments:
            seg.segment_number += 1
            seg.save(update_fields=['segment_number'])
        
        # Criar novo segmento (depois da CEO) no número liberado
        seg_after = CableSegment.objects.create(
            cable=cable,
            segment_number=segment.segment_number + 1,
            name=f"{cable.name}-Seg{segment.segment_number + 1}",
            start_infrastructure=ceo,
            end_infrastructure=original_end,
            length_meters=length_after
        )
        
        return segment, seg_after


def auto_segment_cable_at_ceo(
    cable: 'FiberCable',
    ceo: 'FiberInfrastructure',
    distance_meters: float = None
) -> tuple['CableSegment', 'CableSegment']:
    """
    Segmenta automaticamente um cabo ao adicionar CEO.
    
    Workflow:
    1. Se cabo não tem segmentos → cria Seg1 inicial
    2. Identifica em qual segmento a CEO está
    3. Divide o segmento na posição da CEO
    
    Args:
        cable: Cabo a ser segmentado
        ceo: CEO sendo adicionada
        distance_meters: Distância da CEO ao longo do cabo (metros).
                        Se None, tenta usar ceo.distance_from_origin
        
    Returns:
        Tupla (seg_entrada, seg_saida) para uso em fusões
    """
    from inventory.models import CableSegment
    
    # 1. Criar segmento inicial se não existir
    if not cable.segments.exists():
        create_initial_segment(cable)
    
    # 2. Obter distância da CEO ao longo do cabo
    if distance_meters is None:
        # Tentar usar campo da CEO se existir
        distance = getattr(ceo, 'distance_from_origin', None)
        if distance is None:
            # Fallback: usar ponto médio do cabo
            total_length = sum(seg.length_meters for seg in cable.segments.all())
            distance = total_length / 2
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"CEO {ceo.name} sem distance_from_origin, usando ponto médio: {distance}m"
            )
    else:
        distance = distance_meters
    
    # 3. Encontrar segmento que contém esta distância
    current_distance = 0
    target_segment = None
    
    for seg in cable.segments.order_by('segment_number'):
        if current_distance <= distance <= current_distance + seg.length_meters:
            target_segment = seg
            break
        current_distance += seg.length_meters
    
    if not target_segment:
        # CEO fora do range → usar último segmento
        target_segment = cable.segments.order_by('segment_number').last()
    
    # 4. Dividir segmento
    distance_in_segment = distance - current_distance
    seg_before, seg_after = split_segment_at_ceo(
        target_segment,
        ceo,
        distance_in_segment
    )
    
    return seg_before, seg_after


def get_segments_at_ceo(ceo: 'FiberInfrastructure') -> dict[str, list['CableSegment']]:
    """
    Retorna segmentos de entrada e saída de uma CEO.
    
    Returns:
        {
            "entrada": [seg1, seg3],  # Segmentos que TERMINAM nesta CEO
            "saida": [seg2, seg4]     # Segmentos que COMEÇAM nesta CEO
        }
    """
    from inventory.models import CableSegment
    
    entrada = list(CableSegment.objects.filter(end_infrastructure=ceo).select_related('cable'))
    saida = list(CableSegment.objects.filter(start_infrastructure=ceo).select_related('cable'))
    
    return {
        "entrada": entrada,
        "saida": saida
    }
