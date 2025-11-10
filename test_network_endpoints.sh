#!/bin/bash

# Script para testar os novos endpoints de informa??es de rede
# Execute este script ap?s iniciar o servidor Django

BASE_URL="http://localhost:8000/api/v1/inventory"

echo "? Testando Endpoints de Informa??es de Rede"
echo "============================================="

echo ""
echo "1. 🔍 Host groups (filtrando vazios):"
curl -s "$BASE_URL/zabbix/lookup/host-groups/?exclude_empty=1" | python3 -m json.tool

echo ""
echo "2. 🖥️ Descoberta de hosts Zabbix (limite padrão):"
curl -s "$BASE_URL/zabbix/lookup/hosts/" | python3 -m json.tool

echo ""
echo "3. 📡 Detalhes do host (usando primeiro resultado se existir):"
HOSTID=$(curl -s "$BASE_URL/zabbix/lookup/hosts/?limit=1" | python3 -c "import sys, json; data=json.load(sys.stdin); hosts=data.get('data') or []; print(hosts[0]['hostid'] if hosts else '')")

if [ ! -z "$HOSTID" ]; then
    echo "   Host ID encontrado: $HOSTID"
    curl -s "$BASE_URL/zabbix/lookup/hosts/$HOSTID/status/" | python3 -m json.tool
    echo ""
    echo "   Interfaces principais:"
    curl -s "$BASE_URL/zabbix/lookup/hosts/$HOSTID/interfaces/?only_main=true" | python3 -m json.tool
else
    echo "   ⚠️ Nenhum host retornado pelo lookup"
fi

echo ""
echo "4. ➕ Teste de importação de dispositivo (payload de exemplo)"
curl -s -X POST "$BASE_URL/devices/add-from-zabbix/" \
  -H "Content-Type: application/json" \
  -d '{"hostid": "12345"}' | python3 -m json.tool

echo ""
echo "5. 📊 Métricas ópticas de porta (substitua PORT_ID conforme necessário)"
PORT_ID=${PORT_ID:-1}
curl -s "$BASE_URL/ports/$PORT_ID/optical/" | python3 -m json.tool

echo ""
echo "? Test complete!"
echo ""
echo "? Summary of tested endpoints:"
echo "   - Grupos: /api/v1/inventory/zabbix/lookup/host-groups/"
echo "   - Hosts: /api/v1/inventory/zabbix/lookup/hosts/"
echo "   - Status do host: /api/v1/inventory/zabbix/lookup/hosts/{hostid}/status/"
echo "   - Interfaces principais: /api/v1/inventory/zabbix/lookup/hosts/{hostid}/interfaces/?only_main=true"
echo "   - Importar dispositivo: /api/v1/inventory/devices/add-from-zabbix/"
echo "   - Telemetria óptica: /api/v1/inventory/ports/{port_id}/optical/"