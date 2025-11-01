# API Fiber Routes - Especificação Completa

## 📋 Endpoints Descobertos

### **1. Listar Cabos**
```
GET /zabbix_api/api/fibers/
```
**Response:**
```json
{
  "cables": [
    {
      "id": 1,
      "name": "Cabo SP-RJ",
      "status": "up",
      "length_km": 435.5
    }
  ]
}
```

### **2. Detalhes do Cabo**
```
GET /zabbix_api/api/fiber/<cable_id>/
```
**Response:**
```json
{
  "id": 1,
  "name": "Cabo SP-RJ",
  "status": "up",
  "length_km": 435.5,
  "origin": {
    "site": "Site A",
    "lat": -23.5505,
    "lng": -46.6333,
    "device": "Switch-A",
    "device_id": 1,
    "port": "eth0/1",
    "port_id": 1
  },
  "destination": {
    "site": "Site B",
    "lat": -22.9068,
    "lng": -43.1729,
    "device": "Switch-B",
    "device_id": 2,
    "port": "eth0/1",
    "port_id": 2
  },
  "path": [
    {"lat": -23.5505, "lng": -46.6333},
    {"lat": -23.0000, "lng": -45.0000},
    {"lat": -22.9068, "lng": -43.1729}
  ],
  "single_port": false
}
```

### **3. Atualizar Path do Cabo**
```
PUT /zabbix_api/api/fiber/<cable_id>/
Content-Type: application/json
```
**Request Body:**
```json
{
  "path": [
    {"lat": -23.5505, "lng": -46.6333},
    {"lat": -23.2000, "lng": -45.5000},
    {"lat": -22.9068, "lng": -43.1729}
  ]
}
```
**Response:**
```json
{
  "status": "ok",
  "length_km": 450.2,
  "points": 3
}
```

### **4. Criar Cabo Manual**
```
POST /zabbix_api/api/fibers/manual-create/
Content-Type: application/json
```
**Request Body:**
```json
{
  "name": "Novo Cabo",
  "origin_device_id": 1,
  "origin_port_id": 1,
  "dest_device_id": 2,
  "dest_port_id": 2,
  "path": [
    {"lat": -23.5505, "lng": -46.6333},
    {"lat": -22.9068, "lng": -43.1729}
  ],
  "single_port": false
}
```
**Response:**
```json
{
  "fiber_id": 3,
  "name": "Novo Cabo",
  "points": 2,
  "length_km": 435.5,
  "origin_port": {...},
  "destination_port": {...}
}
```

### **5. Deletar Cabo**
```
DELETE /zabbix_api/api/fiber/<cable_id>/
```
**Response:** 204 No Content

### **6. Importar KML**
```
POST /zabbix_api/api/fibers/import-kml/
Content-Type: multipart/form-data
```
**Form Data:**
- `name`: Nome do cabo
- `origin_device_id`: ID do device origem
- `origin_port_id`: ID da porta origem
- `dest_device_id`: ID do device destino
- `dest_port_id`: ID da porta destino
- `single_port`: "true"/"false"
- `kml_file`: Arquivo KML

**Response:**
```json
{
  "fiber_id": 4,
  "name": "Cabo Importado",
  "points": 50,
  "path_coordinates": [...]
}
```

---

## 🔑 **IMPORTANTE - Campo Path**

### **Na API (JSON):**
- **Enviar**: `"path": [...]`
- **Receber**: `"path": [...]`

### **No Banco de Dados (modelo):**
- **Campo**: `path_coordinates` (JSONField)

### **Conversão Automática:**
O backend faz a conversão automaticamente:
- `inventory_fibers.py` linha 158: `path = body.get("path")`
- `usecases/fibers.py` linha 288: `cable.path_coordinates = sanitized`
- `usecases/fibers.py` linha 257: retorna `"path": cable.path_coordinates`

**Conclusão:** O JavaScript está CORRETO usando `"path"`!

---

## ✅ **Validações do Backend**

### **Path:**
- Mínimo 2 pontos (exceto se `allow_empty=True`)
- Cada ponto deve ter `lat` e `lng`
- Latitude: -90.0 a 90.0
- Longitude: -180.0 a 180.0

### **Nome:**
- Obrigatório
- Único (case-insensitive)
- Não pode ser vazio após strip()

### **Portas:**
- Origem e destino devem existir
- Devem pertencer aos devices especificados
- Se `single_port=false`: devem ser diferentes
- Se `single_port=true`: destino = origem

### **Single Port Mode:**
- Permite origem e destino iguais
- Útil para monitoramento de loopback
- Campo `notes` = "single-port-monitoring"

---

## 🧪 **Status de Testes**

Arquivo: `routes_builder/tests/test_fiber_routes_full.py`

**18 testes criados:**
- ✅ Listagem de cabos (vazia e com dados)
- ✅ Detalhes de cabo (existente e inexistente)
- ✅ Criação manual
- ✅ Atualização de path
- ✅ Atualização de metadados
- ✅ Deleção
- ✅ Visualização no mapa
- ✅ Validação de modelo
- ✅ Casos extremos (1 ponto, 100 pontos, path vazio)
- ✅ Permissões (autenticado/não autenticado)

**Status Atual:** 4/18 passando (22%)
**Bloqueio:** Fixtures com campos incorretos dos modelos
