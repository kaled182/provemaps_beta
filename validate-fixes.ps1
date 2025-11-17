# Script de Validacao - Correcoes de Maps e API
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "VALIDACAO DAS CORRECOES" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. Testar API do Dashboard
Write-Host "1. Testando API do Dashboard..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/maps_view/api/dashboard/data/" -UseBasicParsing -TimeoutSec 5
    $isJson = $response.Content -like '*hosts_status*'
    
    if ($response.StatusCode -eq 200 -and $isJson) {
        Write-Host "   OK - API Dashboard retorna JSON" -ForegroundColor Green
    } else {
        Write-Host "   ERRO - API nao retorna JSON valido" -ForegroundColor Red
        Write-Host "   Content preview: $($response.Content.Substring(0, 100))..."
    }
} catch {
    Write-Host "   ERRO - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# 2. Testar endpoints principais
Write-Host "2. Testando endpoints principais..." -ForegroundColor Yellow

$endpoints = @(
    "/monitoring/backbone/",
    "/NetworkDesign/",
    "/zabbix/lookup/"
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000$endpoint" -UseBasicParsing -TimeoutSec 5
        $hasVue = $response.Content -like '*vue-spa*'
        $hasGoogleMaps = $response.Content -like '*google-maps-api-key*'
        
        if ($response.StatusCode -eq 200 -and $hasVue) {
            $status = "OK"
            if ($hasGoogleMaps) {
                $status += " (Google Maps meta tag presente)"
            }
            Write-Host "   $status - $endpoint" -ForegroundColor Green
        } else {
            Write-Host "   AVISO - $endpoint" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ERRO - $endpoint" -ForegroundColor Red
    }
}

Write-Host ""

# 3. Resumo
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "RESUMO DAS CORRECOES" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Correcoes aplicadas:" -ForegroundColor White
Write-Host "  1. maps_view URLs adicionadas ao core/urls.py" -ForegroundColor Gray
Write-Host "  2. Google Maps loader centralizado criado" -ForegroundColor Gray
Write-Host "  3. App.vue pre-carrega Google Maps no inicio" -ForegroundColor Gray
Write-Host "  4. useMapService usa loader compartilhado" -ForegroundColor Gray
Write-Host ""
Write-Host "Teste manual:" -ForegroundColor White
Write-Host "  1. Abra http://localhost:8000/zabbix/lookup/" -ForegroundColor Gray
Write-Host "  2. Navegue para /monitoring/backbone/" -ForegroundColor Gray
Write-Host "  3. Verifique se o mapa aparece SEM precisar F5" -ForegroundColor Gray
Write-Host "  4. Verifique se o sidebar Hosts carrega os dados" -ForegroundColor Gray
Write-Host ""
