# Solução Final - Google Maps API Key via Endpoint

## Problema Identificado
Ao navegar de `/zabbix/lookup/` para `/NetworkDesign/` (navegação client-side SPA), o meta tag `<meta name="google-maps-api-key">` não estava disponível no DOM porque:
1. Django só renderiza o template HTML na carga inicial
2. Navegações subsequentes são feitas pelo Vue Router (client-side)
3. O DOM não é re-renderizado pelo Django, então o meta tag não existe

## Solução Implementada

### Backend: Endpoint de Configuração
**Arquivo:** `backend/core/views_api.py`
```python
@require_GET
def frontend_config(request):
    """Retorna configuração do frontend incluindo API keys"""
    return JsonResponse({
        'googleMapsApiKey': settings.GOOGLE_MAPS_API_KEY,
        'debug': settings.DEBUG,
    })
```

**Rota:** `backend/core/urls.py`
```python
path('api/config/', api_views.frontend_config, name='frontend_config'),
```

### Frontend: Fetch da API Key
**Arquivo:** `frontend/src/utils/googleMapsLoader.js`

Antes (dependia de meta tag):
```javascript
const metaTag = document.querySelector('meta[name="google-maps-api-key"]');
const apiKey = metaTag?.getAttribute('content');
```

Depois (fetch do endpoint):
```javascript
export async function getGoogleMapsApiKey() {
  const response = await fetch('/api/config/');
  const config = await response.json();
  return config.googleMapsApiKey;
}
```

## Vantagens da Solução

1. ✅ **Funciona em navegação client-side**: Não depende do DOM renderizado pelo Django
2. ✅ **Consistente**: Mesma fonte de dados para carga inicial e navegação SPA
3. ✅ **Seguro**: Google Maps API Key pode ser restrita por domínio no Google Console
4. ✅ **Extensível**: Endpoint pode retornar outras configurações conforme necessário

## Como Testar

### 1. Verificar o endpoint
```powershell
Invoke-WebRequest -Uri http://localhost:8000/api/config/ | Select-Object -ExpandProperty Content
```

Deve retornar:
```json
{"googleMapsApiKey": "AIzaSy...", "debug": true}
```

### 2. Testar no navegador
1. Abra DevTools (F12) na aba Console
2. Acesse `http://localhost:8000/zabbix/lookup/`
3. Navegue para `/NetworkDesign/` (clique no menu)
4. **Observe os logs no console:**
   - `[GoogleMapsLoader] Fetching API key from /api/config/`
   - `[GoogleMapsLoader] ✅ API key found from config endpoint`
   - `[App] ✅ Google Maps loaded successfully`
   - O mapa deve aparecer **SEM precisar F5**

### 3. Testar isolamento
1. Em `/zabbix/lookup/` → Console NÃO deve tentar carregar Google Maps
2. Em `/NetworkDesign/` → Console deve carregar Google Maps
3. Em `/monitoring/backbone/` → Console deve carregar Google Maps

## Logs Esperados (Sucesso)

```
[App] Navigation: /zabbix/lookup/ → /NetworkDesign
[App] Route needs maps: true
[App] Loading Google Maps for this route...
[GoogleMapsLoader] loadGoogleMaps() called
[GoogleMapsLoader] Fetching API key from /api/config/
[GoogleMapsLoader] ✅ API key found from config endpoint
[GoogleMapsLoader] Starting new load...
[App] ✅ Google Maps loaded successfully
[NetworkDesignView] Component mounting...
[NetworkDesignView] ✅ Google Maps already available!
```

## Arquivos Modificados

1. `backend/core/views_api.py` - NOVO: Endpoint de configuração
2. `backend/core/urls.py` - Adicionada rota `/api/config/`
3. `frontend/src/utils/googleMapsLoader.js` - Substituído meta tag por fetch

## Rollback (se necessário)

Se precisar reverter:
1. Restaurar `googleMapsLoader.js` para usar meta tag
2. Remover `path('api/config/', ...)` de `core/urls.py`
3. Deletar `backend/core/views_api.py`
