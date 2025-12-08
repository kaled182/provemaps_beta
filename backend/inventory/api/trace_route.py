"""
Trace Route API - Rastreamento do caminho óptico completo.

Algoritmo de rastreamento bidirecional que navega pelos relacionamentos
fused_to e connected_device_port para construir o caminho completo da luz.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.request import Request

from inventory.models import FiberStrand, Port


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
            'port_type': port.port_type,
            'status': port.admin_status,
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
    
    # Calcula distância do segmento se disponível
    distance_km = Decimal('0')
    if segment and segment.length_km:
        distance_km = segment.length_km
    elif cable.route and cable.route.total_length_km:
        distance_km = cable.route.total_length_km
    
    # Atenuação: 0.35 dB/km (fibra monomodo típica)
    fiber_loss = distance_km * Decimal('0.35') if distance_km else Decimal('0')
    
    return TraceStep(
        step_number=step_num,
        type='fiber_strand',
        name=(
            f"{cable.label} - Fibra {strand.absolute_number} "
            f"({strand.color})"
        ),
        details={
            'strand_id': strand.id,
            'cable_id': cable.id,
            'cable_label': cable.label,
            'fiber_number': strand.absolute_number,
            'fiber_color': strand.color,
            'fiber_status': strand.status,
            'tube_number': strand.tube.number,
            'distance_km': float(distance_km),
            'attenuation_measured_db': (
                float(strand.attenuation_db)
                if strand.attenuation_db
                else None
            ),
            'segment_id': segment.id if segment else None,
        },
        loss_db=fiber_loss
    )


def serialize_fusion(
    strand: FiberStrand, paired_strand: FiberStrand, step_num: int
) -> TraceStep:
    """Serialize a fusion point."""
    infra = strand.fusion_infrastructure or paired_strand.fusion_infrastructure
    
    details: dict[str, Any] = {
        'strand_a_id': strand.id,
        'strand_b_id': paired_strand.id,
        'fusion_location': None,
        'tray': None,
        'slot': None,
    }
    
    if infra:
        details.update({
            'fusion_location': infra.name,
            'infrastructure_id': infra.id,
            'infrastructure_type': infra.infrastructure_type,
            'latitude': float(infra.latitude) if infra.latitude else None,
            'longitude': float(infra.longitude) if infra.longitude else None,
        })
    
    return TraceStep(
        step_number=step_num,
        type='fusion',
        name=f"Fusão em {infra.name if infra else 'CEO Desconhecido'}",
        details=details,
        loss_db=Decimal('0.1')  # Typical fusion loss
    )


def trace_direction(
    start_strand: FiberStrand,
    visited: set[int],
    direction: str
) -> list[TraceStep]:
    """
    Trace in one direction (upstream or downstream).
    
    Args:
        start_strand: Starting fiber strand
        visited: Set of visited strand IDs to prevent loops
        direction: 'upstream' or 'downstream'
    
    Returns:
        List of trace steps in order
    """
    path: list[TraceStep] = []
    current = start_strand
    step_num = 1
    
    while current:
        # Check if already visited (prevent infinite loops)
        if current.id in visited:
            break
        visited.add(current.id)
        
        # Add current fiber strand to path
        path.append(serialize_fiber_strand(current, step_num))
        step_num += 1
        
        # Check if connected to device port (endpoint reached)
        if current.connected_device_port:
            path.append(
                serialize_device_port(current.connected_device_port, step_num)
            )
            break
        
        # Check for fusion to another strand
        if current.fused_to and current.fused_to.id not in visited:
            # Add fusion step
            path.append(serialize_fusion(current, current.fused_to, step_num))
            step_num += 1
            
            # Move to fused strand
            current = current.fused_to
        else:
            # No more connections
            break
    
    return path


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
            'tube__cable__route',
            'connected_device_port__device__site',
            'fused_to',
            'fusion_infrastructure',
            'segment'
        ).get(id=strand_id)
    except FiberStrand.DoesNotExist:
        return Response(
            {'error': f'FiberStrand with id={strand_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    visited: set[int] = set()
    
    # Trace upstream (direction A)
    path_a = trace_direction(start_strand, visited, 'upstream')
    
    # Reverse path A so it goes from endpoint to start
    path_a.reverse()
    
    # Trace downstream (direction B) - start_strand already in visited
    # We need to continue from start_strand's fusion partner
    path_b: list[TraceStep] = []
    if start_strand.fused_to and start_strand.fused_to.id not in visited:
        # Add fusion step
        fusion_step = serialize_fusion(
            start_strand, start_strand.fused_to, len(path_a) + 1
        )
        path_b.append(fusion_step)
        
        # Continue tracing from fused strand
        remaining_path = trace_direction(
            start_strand.fused_to, visited, 'downstream'
        )
        path_b.extend(remaining_path)
    
    # Combine paths
    full_path = path_a + path_b
    
    # Renumber steps
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
