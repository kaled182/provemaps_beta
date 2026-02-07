# TESTE MANUAL - Navegacao Zabbix -> Maps
# Execute este script e siga as instrucoes passo a passo

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "TESTE MANUAL - NAVEGACAO DE ZABBIX PARA MAPS" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "PREPARACAO:" -ForegroundColor Yellow
Write-Host "1. Abra o navegador (Chrome ou Edge)" -ForegroundColor White
Write-Host "2. Abra DevTools (F12)" -ForegroundColor White
Write-Host "3. Va para a aba Console" -ForegroundColor White
Write-Host "4. Limpe o console (Ctrl+L)" -ForegroundColor White
Write-Host ""

Write-Host "TESTE 1: Zabbix -> Network Design" -ForegroundColor Yellow
Write-Host "----------------------------------------------" -ForegroundColor Gray
Write-Host "1. Acesse: http://localhost:8000/zabbix/lookup/" -ForegroundColor White
Write-Host "2. AGUARDE carregar completamente" -ForegroundColor White
Write-Host "3. Verifique no console:" -ForegroundColor White
Write-Host "   - Procure por: [App] Mounting application..." -ForegroundColor Gray
Write-Host "   - Procure por: [App] Pre-loading Google Maps API..." -ForegroundColor Gray
Write-Host "   - Procure por: [GoogleMapsLoader] loadGoogleMaps() called" -ForegroundColor Gray
Write-Host "   - Procure por: [App] ✅ Google Maps pre-loaded successfully" -ForegroundColor Gray
Write-Host ""
Write-Host "4. ANOTE no console se o Google Maps foi carregado (SIM/NAO):" -ForegroundColor Cyan
Read-Host "   Pressione ENTER quando pronto"
Write-Host ""

Write-Host "5. Clique no menu lateral em 'Network Design'" -ForegroundColor White
Write-Host "6. AGUARDE 3-5 segundos" -ForegroundColor White
Write-Host "7. Verifique no console:" -ForegroundColor White
Write-Host "   - Procure por: [NetworkDesignView] Component mounting..." -ForegroundColor Gray
Write-Host "   - Procure por: [NetworkDesignView] Waiting for Google Maps..." -ForegroundColor Gray
Write-Host "   - Procure por: [NetworkDesignView] Google Maps ready!" -ForegroundColor Gray
Write-Host ""
Write-Host "8. Verifique na TELA:" -ForegroundColor Cyan
Write-Host "   - O mapa do Google Maps apareceu? (SIM/NAO):" -ForegroundColor Cyan
$teste1 = Read-Host
Write-Host ""

Write-Host "TESTE 2: Zabbix -> Monitoring Backbone" -ForegroundColor Yellow
Write-Host "----------------------------------------------" -ForegroundColor Gray
Write-Host "1. Volte para http://localhost:8000/zabbix/lookup/" -ForegroundColor White
Write-Host "2. Limpe o console (Ctrl+L)" -ForegroundColor White
Write-Host "3. Clique no menu lateral em 'Backbone' (dentro de Monitoring)" -ForegroundColor White
Write-Host "4. AGUARDE 3-5 segundos" -ForegroundColor White
Write-Host "5. Verifique na TELA:" -ForegroundColor Cyan
Write-Host "   - O mapa do Google Maps apareceu? (SIM/NAO):" -ForegroundColor Cyan
$teste2 = Read-Host
Write-Host "   - O sidebar com lista de Hosts apareceu? (SIM/NAO):" -ForegroundColor Cyan
$teste3 = Read-Host
Write-Host ""

Write-Host "TESTE 3: Refresh (F5)" -ForegroundColor Yellow
Write-Host "----------------------------------------------" -ForegroundColor Gray
Write-Host "1. Ainda em /monitoring/backbone/" -ForegroundColor White
Write-Host "2. Aperte F5 para recarregar a pagina" -ForegroundColor White
Write-Host "3. AGUARDE carregar completamente" -ForegroundColor White
Write-Host "4. Verifique:" -ForegroundColor Cyan
Write-Host "   - O mapa continua aparecendo? (SIM/NAO):" -ForegroundColor Cyan
$teste4 = Read-Host
Write-Host ""

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "RESULTADO DOS TESTES" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Teste 1 - Zabbix -> Network Design: $teste1" -ForegroundColor $(if ($teste1 -eq "SIM") { "Green" } else { "Red" })
Write-Host "Teste 2 - Zabbix -> Monitoring Backbone: $teste2" -ForegroundColor $(if ($teste2 -eq "SIM") { "Green" } else { "Red" })
Write-Host "Teste 3 - Sidebar Hosts: $teste3" -ForegroundColor $(if ($teste3 -eq "SIM") { "Green" } else { "Red" })
Write-Host "Teste 4 - Refresh (F5): $teste4" -ForegroundColor $(if ($teste4 -eq "SIM") { "Green" } else { "Red" })
Write-Host ""

if ($teste1 -eq "NAO" -or $teste2 -eq "NAO") {
    Write-Host "INFORMACOES PARA DEBUG:" -ForegroundColor Yellow
    Write-Host "----------------------------------------------" -ForegroundColor Gray
    Write-Host "Copie e cole aqui os logs do console que aparecem:" -ForegroundColor White
    Write-Host ""
    Write-Host "Logs do [App]:" -ForegroundColor Cyan
    Read-Host "Cole aqui e pressione ENTER"
    Write-Host ""
    Write-Host "Logs do [GoogleMapsLoader]:" -ForegroundColor Cyan
    Read-Host "Cole aqui e pressione ENTER"
    Write-Host ""
    Write-Host "Logs do [NetworkDesignView]:" -ForegroundColor Cyan
    Read-Host "Cole aqui e pressione ENTER"
    Write-Host ""
    Write-Host "Algum erro em vermelho no console? (SIM/NAO):" -ForegroundColor Red
    $temErro = Read-Host
    if ($temErro -eq "SIM") {
        Write-Host "Cole o erro completo aqui:" -ForegroundColor Red
        Read-Host
    }
}

Write-Host ""
Write-Host "Teste concluido!" -ForegroundColor Green
Write-Host "Compartilhe estes resultados para analise." -ForegroundColor White
