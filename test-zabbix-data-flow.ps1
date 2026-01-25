# Script de teste completo para verificar fluxo de dados Zabbix
# Executar: .\test-zabbix-data-flow.ps1

Write-Host "`n=== TESTE COMPLETO DO FLUXO DE DADOS ZABBIX ===" -ForegroundColor Cyan
Write-Host "Data/Hora: $(Get-Date)" -ForegroundColor Gray

$baseUrl = "http://localhost:8000"

# Função para exibir JSON formatado
function Show-Json {
    param($data, $title)
    Write-Host "`n$title" -ForegroundColor Yellow
    Write-Host "─────────────────────────────────────────────────" -ForegroundColor Gray
    $data | ConvertTo-Json -Depth 5 | Write-Host
}

try {
    # Teste 1: Sites
    Write-Host "`n[1/4] Testando endpoint de Sites..." -ForegroundColor Cyan
    $sitesResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/sites/" -Method Get
    Write-Host "  Sites encontrados: $($sitesResponse.Count)" -ForegroundColor Green
    
    if ($sitesResponse.Count -gt 0) {
        Show-Json -data $sitesResponse[0] -title "Exemplo do primeiro site:"
    }

    # Teste 2: Devices
    Write-Host "`n[2/4] Testando endpoint de Devices..." -ForegroundColor Cyan
    $devicesResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/devices/" -Method Get
    Write-Host "  Devices encontrados: $($devicesResponse.Count)" -ForegroundColor Green
    
    # Contagem de devices com Zabbix ID
    $devicesWithZabbix = @($devicesResponse | Where-Object { $_.zabbix_hostid })
    Write-Host "  Devices com Zabbix ID: $($devicesWithZabbix.Count)" -ForegroundColor Green
    
    if ($devicesWithZabbix.Count -gt 0) {
        Write-Host "`n  Primeiros 5 devices com Zabbix ID:" -ForegroundColor Yellow
        $devicesWithZabbix | Select-Object -First 5 name, zabbix_hostid | Format-Table
    }

    # Teste 3: Dashboard Data (CRÍTICO)
    Write-Host "`n[3/4] Testando endpoint do Dashboard..." -ForegroundColor Cyan
    $dashboardResponse = Invoke-RestMethod -Uri "$baseUrl/maps_view/api/dashboard/data/" -Method Get
    
    Write-Host "  Estrutura do Dashboard:" -ForegroundColor Yellow
    $dashboardResponse.PSObject.Properties.Name | ForEach-Object {
        Write-Host "    - $_" -ForegroundColor Gray
    }
    
    # Verificar hosts_status
    if ($dashboardResponse.PSObject.Properties.Name -contains 'hosts_status') {
        if ($dashboardResponse.hosts_status) {
            Write-Host "`n  hosts_status: $($dashboardResponse.hosts_status.Count) hosts" -ForegroundColor Green
            
            if ($dashboardResponse.hosts_status.Count -gt 0) {
                Show-Json -data $dashboardResponse.hosts_status[0] -title "Exemplo do primeiro host:"
            } else {
                Write-Host "  ✗ hosts_status está VAZIO!" -ForegroundColor Red
            }
        } else {
            Write-Host "  ✗ hosts_status é NULL!" -ForegroundColor Red
        }
    } else {
        Write-Host "  ✗ hosts_status NÃO EXISTE na resposta!" -ForegroundColor Red
    }

    # Teste 4: Análise Cruzada
    Write-Host "`n[4/4] Análise Cruzada de Dados..." -ForegroundColor Cyan
    
    Write-Host "`n  Resumo Geral:" -ForegroundColor Yellow
    Write-Host "    - Sites: $($sitesResponse.Count)" -ForegroundColor Gray
    Write-Host "    - Devices: $($devicesResponse.Count)" -ForegroundColor Gray
    Write-Host "    - Devices com Zabbix ID: $($devicesWithZabbix.Count)" -ForegroundColor Gray
    
    $hostsCount = 0
    if ($dashboardResponse.hosts_status) {
        $hostsCount = $dashboardResponse.hosts_status.Count
    }
    Write-Host "    - Hosts no Dashboard: $hostsCount" -ForegroundColor Gray
    
    # Diagnóstico
    Write-Host "`n  Diagnóstico:" -ForegroundColor Yellow
    if ($devicesWithZabbix.Count -gt 0 -and $hostsCount -eq 0) {
        Write-Host "    ✗ PROBLEMA: Há devices com Zabbix ID mas dashboard vazio!" -ForegroundColor Red
        Write-Host "    ⚠ Possível problema na integração Zabbix" -ForegroundColor Red
    } elseif ($hostsCount -gt 0) {
        Write-Host "    ✓ Dashboard OK: retornando $hostsCount hosts" -ForegroundColor Green
    } else {
        Write-Host "    ⚠ Sem dados de Zabbix" -ForegroundColor Yellow
    }

} catch {
    Write-Host "`n✗ ERRO:" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== FIM DOS TESTES ===`n" -ForegroundColor Cyan

