import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import FiberCable, FiberFusion

print("\n=== CABOS '001' ===")
cables = FiberCable.objects.filter(name__icontains='001').order_by('id')
for cable in cables:
    print(f"ID: {cable.id} | Nome: {cable.name} | Parent: {cable.parent_cable_id}")
    tubes = cable.tubes.all()
    if tubes:
        first_tube = tubes[0]
        strands = first_tube.strands.all()[:3]
        print(f"  Fibras (primeiras 3): {[f'ID={s.id}, Cor={s.color}' for s in strands]}")

print("\n=== FUSÕES ===")
fusions = FiberFusion.objects.all()
for fusion in fusions:
    print(f"Slot {fusion.tray}-{fusion.slot}: Fiber_A={fusion.fiber_a.id} ({fusion.fiber_a.color}, Cabo={fusion.fiber_a.tube.cable.name}) ↔ Fiber_B={fusion.fiber_b.id} ({fusion.fiber_b.color}, Cabo={fusion.fiber_b.tube.cable.name})")
