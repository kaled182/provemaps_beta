"""
Custom Maps API - Sistema de Mapas Personalizados
Permite criar múltiplos mapas com seleção customizada de equipamentos.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import models
from inventory.models import Device, FiberCable, CustomMap
import json


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def custom_maps_list(request):
    """
    GET: Lista todos os mapas customizados do usuário
    POST: Cria um novo mapa customizado
    """
    if request.method == 'GET':
        # Buscar mapas do usuário ou públicos
        try:
            maps = CustomMap.objects.filter(
                models.Q(created_by=request.user) | models.Q(is_public=True)
            ).distinct()
            
            maps_data = [{
                'id': m.id,
                'name': m.name,
                'description': m.description,
                'category': m.category,
                'is_public': m.is_public,
                'items_count': m.items_count,
                'devices_count': m.devices_count,
                'cables_count': m.cables_count,
                'cameras_count': m.cameras_count,
                'created_at': m.created_at.isoformat(),
            } for m in maps]
            
        except Exception as e:
            maps_data = []
        
        return Response({
            'maps': maps_data,
            'total': len(maps_data)
        })
    
    elif request.method == 'POST':
        data = request.data
        
        # Validação
        if not data.get('name'):
            return Response(
                {'error': 'Nome do mapa é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_map = CustomMap.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                category=data.get('category', 'backbone'),
                is_public=data.get('is_public', True),
                created_by=request.user
            )
            
            return Response({
                'message': 'Mapa criado com sucesso',
                'map': {
                    'id': new_map.id,
                    'name': new_map.name,
                    'description': new_map.description,
                    'category': new_map.category,
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Erro ao criar mapa: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def custom_map_detail(request, map_id):
    """
    GET: Detalhes de um mapa específico
    PUT: Atualiza mapa
    DELETE: Remove mapa
    """
    try:
        custom_map = CustomMap.objects.get(id=map_id)
        
        # Verificar permissão
        if custom_map.created_by != request.user and not custom_map.is_public:
            return Response(
                {'error': 'Sem permissão para acessar este mapa'},
                status=status.HTTP_403_FORBIDDEN
            )
        
    except Exception as e:
        return Response(
            {'error': 'Mapa não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        return Response({
            'map': {
                'id': custom_map.id,
                'name': custom_map.name,
                'description': custom_map.description,
                'category': custom_map.category,
                'is_public': custom_map.is_public,
                'items_count': custom_map.items_count,
            },
            'selected_items': {
                'devices': custom_map.selected_devices,
                'cables': custom_map.selected_cables,
                'cameras': custom_map.selected_cameras,
                'racks': custom_map.selected_racks,
            }
        })
    
    elif request.method == 'PUT':
        # Verificar se é o dono
        if custom_map.created_by != request.user:
            return Response(
                {'error': 'Sem permissão para editar este mapa'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data
        custom_map.name = data.get('name', custom_map.name)
        custom_map.description = data.get('description', custom_map.description)
        custom_map.category = data.get('category', custom_map.category)
        custom_map.is_public = data.get('is_public', custom_map.is_public)
        custom_map.save()
        
        return Response({
            'message': 'Mapa atualizado com sucesso',
            'map': {
                'id': custom_map.id,
                'name': custom_map.name,
                'description': custom_map.description,
            }
        })
    
    elif request.method == 'DELETE':
        # Verificar se é o dono
        if custom_map.created_by != request.user:
            return Response(
                {'error': 'Sem permissão para excluir este mapa'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        custom_map.delete()
        return Response({
            'message': 'Mapa excluído com sucesso'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_map_items(request, map_id):
    """
    Salva os itens selecionados de um mapa
    """
    try:
        custom_map = CustomMap.objects.get(id=map_id)
        
        # Verificar se é o dono
        if custom_map.created_by != request.user:
            return Response(
                {'error': 'Sem permissão para editar este mapa'},
                status=status.HTTP_403_FORBIDDEN
            )
        
    except Exception as e:
        return Response(
            {'error': 'Mapa não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    data = request.data.get('selected_items', {})
    
    custom_map.selected_devices = data.get('devices', [])
    custom_map.selected_cables = data.get('cables', [])
    custom_map.selected_cameras = data.get('cameras', [])
    custom_map.selected_racks = data.get('racks', [])
    custom_map.save()
    
    return Response({
        'message': 'Itens salvos com sucesso',
        'items_count': custom_map.items_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def map_devices_with_location(request):
    """
    Retorna todos os dispositivos com localização (lat/lng) para o mapa
    """
    devices = Device.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('site').values(
        'id', 'name', 'device_type', 'latitude', 'longitude', 
        'status', 'ip_address', 'site__name', 'zabbix_hostid'
    )
    
    devices_data = [{
        'id': d['id'],
        'name': d['name'],
        'type': d.get('device_type', 'unknown'),
        'lat': float(d['latitude']) if d['latitude'] else None,
        'lng': float(d['longitude']) if d['longitude'] else None,
        'status': d.get('status', 'unknown'),
        'ip': d.get('ip_address'),
        'location': d.get('site__name', 'N/A'),
        'zabbix_hostid': d.get('zabbix_hostid')
    } for d in devices if d['latitude'] and d['longitude']]
    
    return Response({
        'results': devices_data,
        'total': len(devices_data)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def map_cables_with_location(request):
    """
    Retorna todos os cabos de fibra com coordenadas para o mapa
    """
    from inventory.spatial import linestring_to_coords
    
    # Buscar cabos que têm geometria (path não nulo)
    # Nota: FiberCable não tem campo is_deleted, então não filtramos por isso
    cables = FiberCable.objects.filter(
        path__isnull=False  # Apenas cabos com geometria
    ).select_related('origin_port__device__site', 'destination_port__device__site')
    
    cables_data = []
    for cable in cables:
        # Extrair coordenadas do campo PostGIS path
        path_coords = linestring_to_coords(cable.path) if cable.path else []
        
        if not path_coords:  # Pular cabos sem coordenadas
            continue
            
        cable_data = {
            'id': cable.id,
            'name': cable.name,
            'description': cable.notes or '',
            'status': cable.status or 'unknown',
            'path_coordinates': path_coords,
            'points': len(path_coords),
        }
        
        # Adicionar informações das portas se disponíveis
        if cable.origin_port:
            cable_data['origin_port'] = {
                'id': cable.origin_port.id,
                'name': cable.origin_port.name,
                'device': cable.origin_port.device.name if cable.origin_port.device else None,
                'site': cable.origin_port.device.site.name if cable.origin_port.device and cable.origin_port.device.site else None,
            }
        
        if cable.destination_port:
            cable_data['destination_port'] = {
                'id': cable.destination_port.id,
                'name': cable.destination_port.name,
                'device': cable.destination_port.device.name if cable.destination_port.device else None,
                'site': cable.destination_port.device.site.name if cable.destination_port.device and cable.destination_port.device.site else None,
            }
        
        cables_data.append(cable_data)
    
    return Response({
        'results': cables_data,
        'total': len(cables_data)
    })

