"""
Script para limpar split incorreto da CEO-9384 e refazer com V2.

O problema: Split V1 criou teste-A e teste-B como novos FiberCables.
A solução: Deletar A e B, usar split V2 que mantém o cabo original.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '/app/backend')
django.setup()

import logging
from inventory.models import FiberCable, FiberInfrastructure, CableSegment, InfrastructureCableAttachment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_ceo_9384():
    logger.info("=" * 80)
    logger.info("LIMPEZA: CEO-9384 - Remover split V1 incorreto")
    logger.info("=" * 80)
    
    # 1. Encontrar CEO-9384
    try:
        ceo = FiberInfrastructure.objects.get(name="CEO-9384")
        logger.info(f"✅ CEO encontrada: {ceo.name} (ID {ceo.id})")
    except FiberInfrastructure.DoesNotExist:
        logger.error("❌ CEO-9384 não encontrada!")
        return
    
    # 2. Listar cabos ligados à CEO
    attachments = InfrastructureCableAttachment.objects.filter(infrastructure=ceo)
    logger.info(f"\n📊 Cabos anexados à CEO-9384: {attachments.count()}")
    
    for att in attachments:
        logger.info(f"   - {att.cable.name} (ID {att.cable.id})")
    
    # 3. Encontrar cabos teste-A e teste-B (criados pelo split V1)
    cabo_a = FiberCable.objects.filter(name__contains="teste-A").first()
    cabo_b = FiberCable.objects.filter(name__contains="teste-B").first()
    cabo_original = FiberCable.objects.filter(name="teste").exclude(
        name__contains="-A"
    ).exclude(name__contains="-B").first()
    
    if cabo_a:
        logger.info(f"\n🗑️  Cabo A encontrado: {cabo_a.name} (ID {cabo_a.id})")
        logger.info(f"   Parent: {cabo_a.parent_cable}")
        
    if cabo_b:
        logger.info(f"🗑️  Cabo B encontrado: {cabo_b.name} (ID {cabo_b.id})")
        logger.info(f"   Parent: {cabo_b.parent_cable}")
    
    if cabo_original:
        logger.info(f"\n✅ Cabo ORIGINAL encontrado: {cabo_original.name} (ID {cabo_original.id})")
    
    # 4. Confirmar limpeza
    if cabo_a or cabo_b:
        logger.warning("\n⚠️  ATENÇÃO: Vou DELETAR os cabos teste-A e teste-B!")
        logger.warning("   Isso removerá:")
        logger.warning("   - Tubos e fibras desses cabos")
        logger.warning("   - Fusões associadas")
        logger.warning("   - Attachments na CEO")
        
        # Deletar cabo-A
        if cabo_a:
            logger.info(f"\n🗑️  Deletando {cabo_a.name}...")
            cabo_a.delete()
            logger.info("   ✅ Deletado!")
        
        # Deletar cabo-B
        if cabo_b:
            logger.info(f"🗑️  Deletando {cabo_b.name}...")
            cabo_b.delete()
            logger.info("   ✅ Deletado!")
        
        logger.info("\n✅ Limpeza concluída!")
    else:
        logger.info("\n✅ Nenhum cabo teste-A ou teste-B encontrado. CEO já está limpa!")
    
    # 5. Verificar estado final
    attachments_final = InfrastructureCableAttachment.objects.filter(infrastructure=ceo)
    logger.info(f"\n📊 Cabos anexados APÓS limpeza: {attachments_final.count()}")
    for att in attachments_final:
        logger.info(f"   - {att.cable.name} (ID {att.cable.id})")
    
    # 6. Verificar segmentos do cabo original
    if cabo_original:
        segments = cabo_original.segments.all().order_by('segment_number')
        logger.info(f"\n📊 Segmentos do cabo '{cabo_original.name}': {segments.count()}")
        for seg in segments:
            status_emoji = "✅" if seg.status == 'active' else "🔴" if seg.status == 'broken' else "⚪"
            logger.info(f"   {status_emoji} {seg.name}: {seg.status}, {seg.length_meters}m")
    
    logger.info("\n" + "=" * 80)
    logger.info("PRÓXIMO PASSO:")
    logger.info("Agora você pode fazer fusões normalmente!")
    logger.info("A CEO deve mostrar apenas o cabo 'teste' nos dois lados.")
    logger.info("=" * 80)

if __name__ == '__main__':
    fix_ceo_9384()
