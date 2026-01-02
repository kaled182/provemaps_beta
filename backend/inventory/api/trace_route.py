"""
Trace Route API - Rastreamento do caminho óptico completo.

Algoritmo de rastreamento bidirecional que navega pelos relacionamentos
FiberFusion e connected_device_port para construir o caminho completo da luz.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, TypedDict

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.request import Request

from django.db.models import Q

from inventory.models import FiberFusion, FiberStrand, Port, CableSegment


def check_cable_integrity(strand: FiberStrand) -> tuple[bool, CableSegment | None, str]:
    """
    Verifica se o cabo da fibra possui algum segmento rompido.
    
    IMPORTANTE: Esta verificação detecta segmentos BROKEN em QUALQUER lugar do cabo,
    não apenas no segmento específico da fibra. Isso garante que o trace pare
    quando houver uma descontinuidade física no cabo, mesmo que a fibra em si
    não esteja diretamente no segmento rompido.
    
    Returns:
        (is_intact, broken_segment, message)
        - is_intact: True se o cabo está íntegro (sem segmentos BROKEN)
        - broken_segment: O primeiro segmento rompido encontrado, se houver
        - message: Mensagem descritiva do problema
    """
    cable = strand.tube.cable
    
    # Primeiro: se a fibra tem um segmento específico atribuído, verifica apenas ele
    if strand.segment:
        if strand.segment.status == CableSegment.STATUS_BROKEN:
            return False, strand.segment, f"Segmento {strand.segment.name} está rompido"
        return True, None, ""
    
    # Segundo: verifica se HÁ QUALQUER segmento BROKEN no cabo
    # (isso cobre o caso de cabos partidos que ainda não têm segmentos atribuídos às fibras)
    broken_segments = cable.segments.filter(status=CableSegment.STATUS_BROKEN).order_by('segment_number')
    
    if broken_segments.exists():
        broken_seg = broken_segments.first()
        return False, broken_seg, f"Rompimento detectado no cabo {cable.name} (segmento {broken_seg.name})"
    
    return True, None, ""


class TraceStep(TypedDict):
    """Single step in the optical path."""
    step_number: int
    type: str  # 'device_port', 'fiber_strand', 'fusion', 'dio', 'patch_cord'
    name: str
    details: dict[str, Any]
    loss_db: Decimal | None


class TraceResult(TypedDict):
    """Complete trace route result."""
    trace_id: str
    source: dict[str, Any]
    destination: dict[str, Any]
    path: list[TraceStep]
    total_distance_km: Decimal
    total_loss_db: Decimal
    fusion_count: int
    connector_count: int
    power_budget: dict[str, Any]
    status: str


def serialize_device_port(port: Port, step_num: int) -> TraceStep:
    """Serialize a device port step."""
    device = port.device

    port_status = getattr(port, "admin_status", None)
    port_type = getattr(port, "port_type", None)

    return TraceStep(
        step_number=step_num,
        type='device_port',
        name=f"{device.name} - {port.name}",
        details={
            'device_id': device.id,
            'device_name': device.name,
            'device_type': device.category,
            'port_id': port.id,
            'port_name': port.name,
            'port_type': port_type,
            'status': port_status,
            'site_name': device.site.display_name if device.site else None,
            'latitude': (
                float(device.site.latitude)
                if device.site and device.site.latitude
                else None
            ),
            'longitude': (
                float(device.site.longitude)
                if device.site and device.site.longitude
                else None
            ),
        },
        loss_db=Decimal('0.5')  # Connector loss
    )


def serialize_fiber_strand(strand: FiberStrand, step_num: int) -> TraceStep:
    """Serialize a fiber strand step."""
    cable = strand.tube.cable
    segment = strand.segment

    distance_km: Decimal | None = None
    if segment and segment.length_meters:
        distance_km = Decimal(str(segment.length_meters)) / Decimal('1000')
    elif cable.length_km:
        distance_km = Decimal(str(cable.length_km))

    if strand.attenuation_db is not None:
        fiber_loss = Decimal(str(strand.attenuation_db))
    elif distance_km is not None:
        fiber_loss = distance_km * Decimal('0.35')
    else:
        fiber_loss = Decimal('0')
    
    # Adicionar informação de status do segmento
    segment_status = segment.status if segment else CableSegment.STATUS_ACTIVE

    return TraceStep(
        step_number=step_num,
        type='fiber_strand',
        name=(
            f"{cable.name} - Fibra {strand.absolute_number} "
            f"({strand.color})"
        ),
        details={
            'strand_id': strand.id,
            'cable_id': cable.id,
            'cable_name': cable.name,
            'fiber_number': strand.absolute_number,
            'fiber_color': strand.color,
            'fiber_status': strand.status,
            'tube_number': strand.tube.number,
            'distance_km': float(distance_km) if distance_km is not None else None,
            'attenuation_measured_db': (
                float(strand.attenuation_db)
                if strand.attenuation_db
                else None
            ),
            'segment_id': segment.id if segment else None,
            'segment_length_m': (
                float(segment.length_meters)
                if segment and segment.length_meters
                else None
            ),
        },
        loss_db=fiber_loss
    )


def serialize_fusion(
    fusion: FiberFusion,
    strand_a: FiberStrand,
    strand_b: FiberStrand,
    step_num: int,
) -> TraceStep:
    """Serialize a fusion point."""

    infra = fusion.infrastructure

    details: dict[str, Any] = {
        'fusion_id': fusion.id,
        'strand_a_id': strand_a.id,
        'strand_b_id': strand_b.id,
        'tray': fusion.tray,
        'slot': fusion.slot,
        'fusion_location': None,
        'infrastructure_id': None,
        'infrastructure_type': None,
        'latitude': None,
        'longitude': None,
    }

    if infra:
        latitude = None
        longitude = None
        if getattr(infra, "location", None):
            latitude = float(infra.location.y)
            longitude = float(infra.location.x)

        details.update({
            'fusion_location': infra.name,
            'infrastructure_id': infra.id,
            'infrastructure_type': getattr(infra, 'type', None),
            'latitude': latitude,
            'longitude': longitude,
        })

    return TraceStep(
        step_number=step_num,
        type='fusion',
        name=(
            f"Fusão em {infra.name}" if infra else "Fusão sem infraestrutura"
        ),
        details=details,
        loss_db=Decimal('0.1')  # Typical fusion loss
    )


def trace_direction(
    start_strand: FiberStrand,
    visited_fibers: set[int],
    visited_fusions: set[int],
) -> list[TraceStep]:
    """Trace from a strand until reaching a device port or a dead end."""

    path: list[TraceStep] = []
    current = start_strand
    step_num = 1

    while current:
        if current.id in visited_fibers:
            break
        
        # CRITICAL: Verificar integridade do cabo ANTES de adicionar ao trace
        is_intact, broken_segment, error_msg = check_cable_integrity(current)
        
        if not is_intact:
            # Adicionar passo indicando rompimento
            path.append(TraceStep(
                step_number=step_num,
                type='broken_segment',
                name=f"⚠️ ROMPIMENTO: {error_msg}",
                details={
                    'segment_id': broken_segment.id if broken_segment else None,
                    'segment_name': broken_segment.name if broken_segment else None,
                    'cable_id': current.tube.cable.id,
                    'cable_name': current.tube.cable.name,
                    'error': error_msg,
                    'is_broken': True,
                },
                loss_db=None  # Perda infinita - luz não passa
            ))
            # PARAR o trace aqui - luz não continua
            break

        path.append(serialize_fiber_strand(current, step_num))
        visited_fibers.add(current.id)
        step_num += 1

        if current.connected_device_port:
            path.append(
                serialize_device_port(current.connected_device_port, step_num)
            )
            break

        fusion = (
            FiberFusion.objects.select_related(
                'infrastructure',
                'fiber_a__tube__cable',
                'fiber_a__segment',
                'fiber_a__connected_device_port__device__site',
                'fiber_b__tube__cable',
                'fiber_b__segment',
                'fiber_b__connected_device_port__device__site',
            )
            .filter(Q(fiber_a=current) | Q(fiber_b=current))
            .exclude(id__in=visited_fusions)
            .order_by('created_at')
            .first()
        )

        if not fusion:
            break

        visited_fusions.add(fusion.id)
        paired = (
            fusion.fiber_b
            if fusion.fiber_a_id == current.id
            else fusion.fiber_a
        )

        path.append(serialize_fusion(fusion, current, paired, step_num))
        step_num += 1

        current = paired

    return path


def iter_remaining_fusions(
    strand: FiberStrand,
    visited_fusions: set[int],
) -> Iterable[tuple[FiberFusion, FiberStrand]]:
    """Yield fusions connected to a strand that have not been traversed yet."""

    qs = FiberFusion.objects.select_related(
        'infrastructure',
        'fiber_a__tube__cable',
        'fiber_a__segment',
        'fiber_a__connected_device_port__device__site',
        'fiber_b__tube__cable',
        'fiber_b__segment',
        'fiber_b__connected_device_port__device__site',
    ).filter(Q(fiber_a=strand) | Q(fiber_b=strand))

    for fusion in qs.order_by('created_at'):
        if fusion.id in visited_fusions:
            continue
        other = (
            fusion.fiber_b
            if fusion.fiber_a_id == strand.id
            else fusion.fiber_a
        )
        yield fusion, other


def calculate_power_budget(path: list[TraceStep]) -> dict[str, Any]:
    """
    Calculate optical power budget for the path.
    
    Standard calculation:
    - Fiber loss: 0.35 dB/km
    - Fusion loss: 0.1 dB per fusion
    - Connector loss: 0.5 dB per connector
    """
    total_loss = Decimal('0')
    total_distance = Decimal('0')
    fusion_count = 0
    connector_count = 0
    
    for step in path:
        if step['loss_db']:
            total_loss += step['loss_db']
        
        if step['type'] == 'fiber_strand':
            distance = step['details'].get('distance_km', 0)
            if distance:
                total_distance += Decimal(str(distance))
        elif step['type'] == 'fusion':
            fusion_count += 1
        elif step['type'] == 'device_port':
            connector_count += 1
    
    # Typical SFP transmit power: -3 dBm to 0 dBm
    # Typical SFP receive sensitivity: -18 dBm to -23 dBm
    # Margin should be at least 3 dB for safety
    
    tx_power = Decimal('0')  # Typical SFP TX power (dBm)
    rx_sensitivity = Decimal('-18')  # Typical SFP RX sensitivity (dBm)
    margin_required = Decimal('3')  # Safety margin
    
    available_margin = tx_power - rx_sensitivity - total_loss
    is_viable = available_margin >= margin_required
    
    return {
        'total_loss_db': float(total_loss),
        'total_distance_km': float(total_distance),
        'fusion_count': fusion_count,
        'connector_count': connector_count,
        'tx_power_dbm': float(tx_power),
        'rx_sensitivity_dbm': float(rx_sensitivity),
        'available_margin_db': float(available_margin),
        'required_margin_db': float(margin_required),
        'is_viable': is_viable,
        'status': 'OK' if is_viable else 'WARNING',
        'message': (
            f"Link viável com {available_margin:.2f} dB de margem"
            if is_viable
            else (
                f"Atenção: Margem insuficiente "
                f"({available_margin:.2f} dB < {margin_required} dB)"
            )
        )
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trace_fiber_route(request: Request) -> Response:
    """
    Trace the complete optical path starting from a fiber strand.
    
    Query Parameters:
        - strand_id: ID of the starting fiber strand
    
    Returns:
        Complete trace with source, destination, path steps, and power budget.
    
    Example:
        GET /api/v1/inventory/trace-route/?strand_id=123
    """
    strand_id = request.query_params.get('strand_id')
    
    if not strand_id:
        return Response(
            {'error': 'strand_id query parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        start_strand = FiberStrand.objects.select_related(
            'tube__cable',
            'segment',
            'connected_device_port__device__site',
        ).get(id=strand_id)
    except FiberStrand.DoesNotExist:
        return Response(
            {'error': f'FiberStrand with id={strand_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    visited_fibers: set[int] = set()
    visited_fusions: set[int] = set()

    path_upstream = trace_direction(
        start_strand,
        visited_fibers,
        visited_fusions,
    )
    full_path: list[TraceStep] = list(reversed(path_upstream))

    # Ensure we only keep unique fusion traversals starting from this strand
    for fusion, next_strand in iter_remaining_fusions(
        start_strand,
        visited_fusions,
    ):
        visited_fusions.add(fusion.id)

        full_path.append(
            serialize_fusion(
                fusion,
                start_strand,
                next_strand,
                len(full_path) + 1,
            )
        )

        downstream_steps = trace_direction(
            next_strand,
            visited_fibers,
            visited_fusions,
        )
        full_path.extend(downstream_steps)

    # Renumber steps sequentially
    for idx, step in enumerate(full_path, start=1):
        step['step_number'] = idx
    
    # Extract source and destination
    source = None
    destination = None
    
    if full_path:
        if full_path[0]['type'] == 'device_port':
            source = full_path[0]['details']
        if full_path[-1]['type'] == 'device_port':
            destination = full_path[-1]['details']
    
    # Calculate power budget
    power_budget = calculate_power_budget(full_path)
    
    # Generate trace ID
    import time
    trace_id = f"trace_{strand_id}_{int(time.time())}"
    
    result: TraceResult = {
        'trace_id': trace_id,
        'source': source or {},
        'destination': destination or {},
        'path': full_path,
        'total_distance_km': Decimal(str(power_budget['total_distance_km'])),
        'total_loss_db': Decimal(str(power_budget['total_loss_db'])),
        'fusion_count': power_budget['fusion_count'],
        'connector_count': power_budget['connector_count'],
        'power_budget': power_budget,
        'status': power_budget['status'],
    }
    
    return Response(result)
