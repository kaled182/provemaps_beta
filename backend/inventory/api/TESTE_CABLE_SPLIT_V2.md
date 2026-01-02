"""
Teste rápido do cable_split_v2 endpoint.

Para testar:
1. Encontrar um cabo com ID
2. Criar uma CEO
3. Fazer POST para /api/v1/inventory/cables/<cable_id>/split-at-ceo-v2/

Exemplo de payload:
{
    "ceo_id": 123,
    "split_point": {
        "lat": -23.456,
        "lng": -47.123
    }
}
"""

# Para testar via curl ou Postman:
# POST http://localhost:8000/api/v1/inventory/cables/50/split-at-ceo-v2/
# Headers: Content-Type: application/json
#          X-CSRFToken: <token>
# Body:
# {
#     "ceo_id": 2098,
#     "split_point": {
#         "lat": -15.5,
#         "lng": -47.8
#     }
# }

# Resposta esperada:
# {
#     "status": "success",
#     "message": "Cabo CABO-BACKBONE-50 partido em segmentos na CEO CEO-Split-Test",
#     "cable": {
#         "id": 50,
#         "name": "CABO-BACKBONE-50",
#         "total_length_km": 10.5
#     },
#     "segments": {
#         "before": {
#             "id": 1,
#             "name": "CABO-BACKBONE-50-Seg1",
#             "length_m": 5250,
#             "status": "active"
#         },
#         "broken": {
#             "id": 2,
#             "name": "CABO-BACKBONE-50-BREAK-CEO-Split-Test",
#             "length_m": 0,
#             "status": "broken"
#         },
#         "after": {
#             "id": 3,
#             "name": "CABO-BACKBONE-50-Seg2",
#             "length_m": 5250,
#             "status": "active"
#         }
#     }
# }

# Depois de fazer o split, o trace_route deve detectar o BREAK:
# GET http://localhost:8000/api/v1/inventory/trace-route/?strand_id=<id>
# Resposta deve incluir:
# {
#     "path": [
#         {...},
#         {
#             "step_number": N,
#             "type": "broken_segment",
#             "name": "CABO-BACKBONE-50-BREAK-CEO-Split-Test",
#             "message": "Segmento BROKEN detectado no cabo CABO-BACKBONE-50"
#         }
#     ]
# }
