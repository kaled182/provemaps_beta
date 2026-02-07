"""
Script para testar Cable Split V2 e verificar integridade.

Uso:
    docker compose exec web python /app/backend/test_split_v2.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '/app/backend')
django.setup()

import logging
from django.db import models
from inventory.models import FiberCable, FiberInfrastructure, CableSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_split_v2():
    """Testa split V2 e verificação de integridade."""
    
    logger.info("=" * 80)
    logger.info("TESTE: Cable Split V2 com CableSegments")
    logger.info("=" * 80)
    
    # 1. Encontrar cabo para teste
    cabo = FiberCable.objects.filter(path__isnull=False).first()
    if not cabo:
        logger.error("❌ Nenhum cabo com path encontrado!")
        return
    
    logger.info(f"✅ Cabo encontrado: {cabo.name} (ID {cabo.id})")
    logger.info(f"   Length: {cabo.length_km}km")
    
    # 2. Verificar segmentos existentes e limpar se necessário
    segments_antes = cabo.segments.all()
    logger.info(f"\n📊 Segmentos ANTES do split: {segments_antes.count()}")
    
    if segments_antes.exists():
        logger.warning("⚠️  Cabo já tem segmentos! Limpando para teste...")
        segments_antes.delete()
        logger.info("   ✅ Segmentos anteriores removidos")
    
    for seg in cabo.segments.all():
        logger.info(f"   - {seg.name}: {seg.status}, {seg.length_meters}m")
    
    # 3. Verificar se há CEOs no cabo
    ceo = cabo.infrastructure_points.filter(type='splice_box').first()
    if not ceo:
        logger.error("❌ Cabo não tem CEOs!")
        logger.info("   Criando CEO de teste associada ao cabo...")
        from django.contrib.gis.geos import Point
        # Pegar coordenada do meio do path do cabo
        coords = list(cabo.path.coords)
        mid_idx = len(coords) // 2
        mid_lng, mid_lat = coords[mid_idx]
        
        ceo = FiberInfrastructure.objects.create(
            cable=cabo,
            type='splice_box',
            name="CEO-TEST-SPLIT",
            location=Point(mid_lng, mid_lat, srid=4326),
            distance_from_origin=float(cabo.length_km or 1) * 1000 / 2  # Ponto médio
        )
        logger.info(f"   ✅ CEO criada: {ceo.name}")
    else:
        logger.info(f"✅ CEO encontrada: {ceo.name} (ID {ceo.id})")
    
    # 4. Simular split usando service layer
    logger.info("\n🔧 Executando split usando auto_segment_cable_at_ceo()...")
    from inventory.services.cable_segments import auto_segment_cable_at_ceo
    
    try:
        # Calcular ponto médio do cabo (50%)
        total_length_m = float(cabo.length_km or 1) * 1000
        distance_meters = total_length_m / 2
        
        logger.info(f"   Distance: {distance_meters}m (50% do cabo)")
        
        seg_before, seg_after = auto_segment_cable_at_ceo(
            cable=cabo,
            ceo=ceo,
            distance_meters=distance_meters
        )
        
        logger.info(f"   ✅ Segmentos criados:")
        logger.info(f"      - Before: {seg_before.name} ({seg_before.length_meters}m)")
        logger.info(f"      - After:  {seg_after.name} ({seg_after.length_meters}m)")
        
    except Exception as e:
        logger.error(f"❌ Erro no split: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. Criar segmento BROKEN
    logger.info("\n🔴 Criando segmento BROKEN virtual...")
    try:
        # Calcular próximo segment_number disponível
        max_seg_num = cabo.segments.aggregate(models.Max('segment_number'))['segment_number__max']
        next_seg_num = (max_seg_num or 0) + 1
        
        broken_segment = CableSegment.objects.create(
            cable=cabo,
            segment_number=next_seg_num,
            name=f"{cabo.name}-BREAK-{ceo.name}",
            start_infrastructure=ceo,
            end_infrastructure=ceo,
            length_meters=0,
            status=CableSegment.STATUS_BROKEN
        )
        logger.info(f"   ✅ Segmento BROKEN criado: {broken_segment.name}")
        logger.info(f"      Segment #: {broken_segment.segment_number}")
        logger.info(f"      Status: {broken_segment.status}")
        logger.info(f"      Length: {broken_segment.length_meters}m")
    except Exception as e:
        logger.error(f"❌ Erro ao criar BROKEN: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 6. Verificar estrutura final
    segments_depois = cabo.segments.all().order_by('segment_number')
    logger.info(f"\n📊 Segmentos DEPOIS do split: {segments_depois.count()}")
    for seg in segments_depois:
        status_emoji = "✅" if seg.status == 'active' else "🔴" if seg.status == 'broken' else "⚪"
        logger.info(f"   {status_emoji} {seg.name}:")
        logger.info(f"      - Segment #: {seg.segment_number}")
        logger.info(f"      - Status: {seg.status}")
        logger.info(f"      - Length: {seg.length_meters}m")
    
    # 7. Testar check_cable_integrity
    logger.info("\n🔍 Testando check_cable_integrity()...")
    from inventory.api.trace_route import check_cable_integrity
    from inventory.models import FiberStrand
    
    # Pegar primeira fibra do cabo
    strand = FiberStrand.objects.filter(tube__cable=cabo).first()
    if not strand:
        logger.warning("⚠️  Cabo não tem fibras, não pode testar integrity check")
    else:
        try:
            is_intact, broken_seg, message = check_cable_integrity(strand)
            
            if is_intact:
                logger.info(f"   ✅ Cabo está INTACTO: {message}")
            else:
                logger.info(f"   🔴 Cabo está BROKEN: {message}")
                if broken_seg:
                    logger.info(f"      Segmento problemático: {broken_seg.name}")
        except Exception as e:
            logger.error(f"   ❌ Erro no check: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("\n" + "=" * 80)
    logger.info("TESTE CONCLUÍDO!")
    logger.info("=" * 80)
    
    # Retornar IDs para testes manuais
    return {
        'cabo_id': cabo.id,
        'ceo_id': ceo.id,
        'broken_segment_id': broken_segment.id if 'broken_segment' in locals() else None
    }

if __name__ == '__main__':
    result = test_split_v2()
    if result:
        print(f"\n📝 IDs para testes manuais:")
        print(f"   Cabo: {result['cabo_id']}")
        print(f"   CEO: {result['ceo_id']}")
        print(f"   Broken Segment: {result['broken_segment_id']}")
