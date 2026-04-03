from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.gis.geos import Point
from django.db.models import F
from django.apps import apps
from django.db import connection
import logging
import json

logger = logging.getLogger(__name__)

"""
API para criação de pontos de infraestrutura sem importar serializers
para evitar ciclos de import durante startup/migrações.
"""


@api_view(["POST"])
def api_create_infrastructure(request):
    """
    Cria um ponto de infraestrutura sobre um cabo e calcula a metragem
    sequencial (distance_from_origin) via Linear Referencing.
    Projeta o ponto clicado na linha do cabo para cálculo preciso.
    
    Regras especiais:
    - splice_box (CEO): adiciona 20m ao comprimento total do cabo
    - slack (Reserva Técnica): exige 'slack_length' em metadata e adiciona ao cabo
    """
    FiberCable = apps.get_model("inventory", "FiberCable")
    FiberInfrastructure = apps.get_model("inventory", "FiberInfrastructure")

    cable_id = request.data.get("cable")
    lat = request.data.get("lat")
    lng = request.data.get("lng")
    infra_type = request.data.get("type")
    name = request.data.get("name") or ""
    metadata = request.data.get("metadata") or {}
    
    # Validação: Reserva Técnica exige tamanho (aceitar slack_length OU length_added)
    if infra_type == "slack":
        # metadata pode vir como dict (REST) ou string JSON (inconsistências de clients)
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                pass

        raw_value = metadata.get("slack_length")
        if raw_value in (None, ""):
            raw_value = metadata.get("length_added")

        logger.info(
            f"[Infrastructure] Validando slack: metadata={metadata}, value={raw_value}"
        )

        if raw_value in (None, ""):
            return Response(
                {"detail": "Reserva Técnica exige 'slack_length' (metros) em metadata"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            slack_value = float(raw_value)
        except (ValueError, TypeError) as e:
            logger.error(f"[Infrastructure] Erro ao converter slack_length: {e}")
            return Response(
                {"detail": f"Valor inválido para slack_length: {raw_value}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if slack_value <= 0:
            return Response(
                {"detail": "O tamanho da reserva deve ser maior que zero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if not cable_id or lat is None or lng is None:
        logger.warning(
            f"[Infrastructure] Bad payload: cable={cable_id}, lat={lat}, lng={lng}, type={infra_type}, name={name}"
        )
        return Response(
            {"detail": "Campos obrigatórios: cable, lat, lng"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cable = FiberCable.objects.get(id=cable_id)
    except FiberCable.DoesNotExist:
        return Response(
            {"detail": "Cabo não encontrado"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    # Validar que o cabo tem path (geometria) definida
    if not cable.path:
        logger.warning(
            f"[Infrastructure] Cable {cable_id} has no geometry 'path'. Cannot add infrastructure."
        )
        return Response(
            {
                "detail": "Cabo sem traçado definido. Desenhe o traçado primeiro antes de adicionar infraestrutura.",
                "error_code": "NO_PATH_GEOMETRY"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    clicked_point = Point(float(lng), float(lat), srid=4326)
    
    # Calcular fração e distância usando geometria PostGIS
    # IMPORTANTE: Usar ST_Length(geography) para comprimento real,
    # não cable.length_km (pode ser estimativa manual)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                ST_LineLocatePoint(
                    path,
                    ST_ClosestPoint(
                        path,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    )
                ) as fraction,
                ST_X(ST_ClosestPoint(
                    path,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )) as proj_lng,
                ST_Y(ST_ClosestPoint(
                    path,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )) as proj_lat,
                ST_Length(path::geography) as cable_length_meters
            FROM zabbix_api_fibercable
            WHERE id = %s
            """,
            [lng, lat, lng, lat, lng, lat, cable_id]
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            fraction = float(row[0])
            proj_lng = float(row[1])
            proj_lat = float(row[2])
            total_meters = float(row[3])  # Comprimento real da geometria
            projected_point = Point(proj_lng, proj_lat, srid=4326)
            distance_from_origin = fraction * total_meters
        else:
            # Fallback: usar ponto clicado se query falhar
            fraction = 0.0
            total_meters = 0.0
            distance_from_origin = 0.0
            projected_point = clicked_point
            logger.warning(
                f"[Infrastructure] PostGIS query returned NULL for cable {cable_id}, "
                f"using clicked point as fallback"
            )
    
    logger.info(
        f"[Infrastructure] Cable {cable_id}: fraction={fraction:.6f}, "
        f"total_meters={total_meters:.2f}, distance={distance_from_origin}"
    )

    infra = FiberInfrastructure.objects.create(
        cable=cable,
        type=infra_type,
        name=name,
        location=projected_point,  # Salvar ponto projetado (sobre a linha)
        distance_from_origin=distance_from_origin,
        metadata=metadata,
    )
    
    # REGRA: Adicionar comprimento extra ao cabo conforme tipo de infraestrutura
    cable_extension = 0.0
    
    if infra_type == "splice_box":
        # CEO adiciona 20m padrão (média de trabalho)
        cable_extension = 20.0
        logger.info(f"[Infrastructure] CEO criado: adicionando {cable_extension}m ao cabo {cable_id}")
    
    elif infra_type == "slack":
        # Reserva Técnica adiciona o tamanho especificado
        slack_raw = metadata.get("slack_length")
        if slack_raw in (None, ""):
            slack_raw = metadata.get("length_added", 0)
        try:
            slack_length = float(slack_raw)
        except (ValueError, TypeError):
            slack_length = 0.0
        cable_extension = slack_length
        logger.info(
            f"[Infrastructure] Reserva Técnica criada: adicionando {cable_extension}m ao cabo {cable_id}"
        )
    
    # Atualizar comprimento do cabo se necessário
    if cable_extension > 0:
        # Recalcular usando geometria PostGIS (sempre disponível agora)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ST_Length(path::geography) as base_length
                FROM zabbix_api_fibercable
                WHERE id = %s
                """,
                [cable_id]
            )
            row = cursor.fetchone()
            base_length_meters = float(row[0]) if row and row[0] else 0.0
        
        # Somar todas as extensões de infraestruturas usando query SQL direta
        # para evitar problemas de cache do ORM
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    type,
                    metadata
                FROM inventory_fiber_infrastructure
                WHERE cable_id = %s
                """,
                [cable_id]
            )
            rows = cursor.fetchall()
        
        total_extension = 0.0
        logger.info(f"[Infrastructure] Cable {cable_id}: recalculando com {len(rows)} infraestruturas")
        
        for infra_type, infra_metadata in rows:
            # metadata vem como string JSON do PostgreSQL
            if isinstance(infra_metadata, str):
                metadata_dict = json.loads(infra_metadata)
            else:
                metadata_dict = infra_metadata
            
            if infra_type == "splice_box":
                total_extension += 20.0
                logger.info(f"  - CEO: +20.0m")
            elif infra_type == "slack":
                # aceitar tanto 'slack_length' quanto 'length_added'
                slack_val = metadata_dict.get("slack_length")
                if slack_val in (None, ""):
                    slack_val = metadata_dict.get("length_added", 0)
                try:
                    slack_meters = float(slack_val)
                except (ValueError, TypeError):
                    slack_meters = 0.0
                total_extension += slack_meters
                logger.info(f"  - Slack: +{slack_meters}m")
        
        new_total_km = (base_length_meters + total_extension) / 1000.0
        cable.length_km = new_total_km
        cable.save(update_fields=["length_km"])
        
        logger.info(
            f"[Infrastructure] Cable {cable_id} length updated: "
            f"base={base_length_meters/1000:.2f}km + extensions={total_extension/1000:.2f}km "
            f"= {new_total_km:.2f}km"
        )

    # Resposta manual para evitar import do serializer
    return Response(
        {
            "id": infra.id,
            "cable": infra.cable_id,
            "type": infra.type,
            "type_display": infra.get_type_display(),
            "name": infra.name,
            "location": {
                "type": "Point",
                "coordinates": [infra.location.x, infra.location.y],
            },
            "distance_from_origin": infra.distance_from_origin,
            "metadata": infra.metadata,
            "created_at": infra.created_at,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
def api_update_infrastructure(request, pk):
    """
    Atualiza nome e/ou tipo de infraestrutura existente.
    Não permite alterar localização ou distância (são calculadas).
    
    Conversões permitidas:
    - slack → splice_box (adiciona 20m, remove slack_length)
    """
    FiberInfrastructure = apps.get_model("inventory", "FiberInfrastructure")
    FiberCable = apps.get_model("inventory", "FiberCable")

    # If DELETE sent to this endpoint, delegate to delete handler
    if request.method == "DELETE":
        return api_delete_infrastructure(request, pk)
    
    try:
        infra = FiberInfrastructure.objects.get(pk=pk)
    except FiberInfrastructure.DoesNotExist:
        return Response(
            {"detail": "Infraestrutura não encontrada"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    # Atualizar apenas campos permitidos
    updated_fields = []
    old_type = infra.type
    cable = infra.cable
    
    if "name" in request.data:
        infra.name = request.data["name"]
        updated_fields.append("name")
    
    if "type" in request.data:
        valid_types = ["slack", "splice_box", "splitter_box", "transition"]
        new_type = request.data["type"]
        if new_type not in valid_types:
            return Response(
                {"detail": f"Tipo inválido. Valores aceitos: {valid_types}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Conversão de Reserva Técnica para CEO
        if old_type == "slack" and new_type == "splice_box":
            # Remover slack_length do metadata e adicionar 20m de CEO
            old_slack_length = float(infra.metadata.get("slack_length", 0))
            infra.metadata.pop("slack_length", None)
            
            # Recalcular comprimento do cabo usando PostGIS
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ST_Length(path::geography) as base_length
                    FROM zabbix_api_fibercable
                    WHERE id = %s
                    """,
                    [cable.id]
                )
                row = cursor.fetchone()
                base_length_meters = float(row[0]) if row and row[0] else 0.0
            
            # Recalcular extensões totais usando SQL direta
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT type, metadata
                    FROM inventory_fiber_infrastructure
                    WHERE cable_id = %s
                    """,
                    [cable.id]
                )
                rows = cursor.fetchall()
            
            total_extension = 0.0
            for row_type, row_metadata in rows:
                # metadata vem como string JSON do PostgreSQL
                if isinstance(row_metadata, str):
                    metadata_dict = json.loads(row_metadata)
                else:
                    metadata_dict = row_metadata
                
                if row_type == "splice_box":
                    total_extension += 20.0
                elif row_type == "slack":
                    # Pular a reserva que está sendo convertida
                    if metadata_dict.get("slack_length"):
                        total_extension += float(metadata_dict.get("slack_length", 0))
            
            # Subtrair slack antigo e adicionar CEO (20m)
            total_extension = total_extension - old_slack_length + 20.0
            
            new_total_km = (base_length_meters + total_extension) / 1000.0
            cable.length_km = new_total_km
            cable.save(update_fields=["length_km"])
            
            logger.info(
                f"[Infrastructure] Converted slack→CEO: cable {cable.id} "
                f"adjusted by {20.0 - old_slack_length:+.1f}m, new total={new_total_km:.2f}km"
            )
            
            updated_fields.append("metadata")
        
        infra.type = new_type
        updated_fields.append("type")
    
    if "metadata" in request.data and "type" not in request.data:
        # Atualização direta de metadata (sem conversão de tipo)
        infra.metadata = request.data["metadata"]
        updated_fields.append("metadata")
    
    if updated_fields:
        infra.save(update_fields=updated_fields)
    
    return Response(
        {
            "id": infra.id,
            "cable": infra.cable_id,
            "type": infra.type,
            "type_display": infra.get_type_display(),
            "name": infra.name,
            "location": {
                "type": "Point",
                "coordinates": [infra.location.x, infra.location.y],
            },
            "distance_from_origin": infra.distance_from_origin,
            "metadata": infra.metadata,
            "created_at": infra.created_at,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
def api_delete_infrastructure(request, pk):
    """
    Remove uma infraestrutura permanentemente.
    Atualiza o comprimento do cabo ao remover CEO (20m) ou Reserva Técnica.
    """
    FiberInfrastructure = apps.get_model("inventory", "FiberInfrastructure")
    FiberCable = apps.get_model("inventory", "FiberCable")
    
    try:
        infra = FiberInfrastructure.objects.get(pk=pk)
    except FiberInfrastructure.DoesNotExist:
        return Response(
            {"detail": "Infraestrutura não encontrada"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    cable_id = infra.cable_id
    cable = infra.cable
    infra_name = infra.name or f"Infra-{pk}"
    infra_type = infra.type
    
    # Calcular redução no comprimento do cabo
    cable_reduction = 0.0
    if infra_type == "splice_box":
        cable_reduction = 20.0
    elif infra_type == "slack":
        slack_val = infra.metadata.get("slack_length", 0) if infra.metadata else 0
        cable_reduction = float(slack_val) if slack_val else 0.0
    
    # Deletar ANTES de tentar atualizar o cabo
    infra.delete()
    
    # Recalcular comprimento do cabo usando PostGIS
    if cable_reduction > 0 and cable:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ST_Length(path::geography) as base_length
                    FROM zabbix_api_fibercable
                    WHERE id = %s
                    """,
                    [cable_id]
                )
                row = cursor.fetchone()
                base_length_meters = float(row[0]) if row and row[0] else 0.0
            
            # Somar extensões restantes usando SQL direta
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT type, metadata
                    FROM inventory_fiber_infrastructure
                    WHERE cable_id = %s
                    """,
                    [cable_id]
                )
                rows = cursor.fetchall()
            
            total_extension = 0.0
            for row_type, row_metadata in rows:
                # metadata vem como string JSON do PostgreSQL
                if isinstance(row_metadata, str):
                    metadata_dict = json.loads(row_metadata)
                else:
                    metadata_dict = row_metadata
                
                if row_type == "splice_box":
                    total_extension += 20.0
                elif row_type == "slack":
                    total_extension += float(metadata_dict.get("slack_length", 0))
            
            new_total_km = (base_length_meters + total_extension) / 1000.0
            cable.length_km = new_total_km
            cable.save(update_fields=["length_km"])
            
            logger.info(
                f"[Infrastructure] Deleted {infra_name} ({infra_type}): "
                f"cable {cable_id} reduced by {cable_reduction}m, new total={new_total_km:.2f}km"
            )
        except Exception as e:
            logger.error(f"[Infrastructure] Error updating cable length after delete: {e}")
    else:
        logger.info(f"[Infrastructure] Deleted {infra_name} from cable {cable_id}")
    
    return Response(
        {"detail": "Infraestrutura removida com sucesso"},
        status=status.HTTP_204_NO_CONTENT,
    )
