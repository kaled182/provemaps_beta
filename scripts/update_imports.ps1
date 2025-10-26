# Script PowerShell para atualizar imports de zabbix_api.models para inventory.models

$files = @(
    "tests\test_inventory_endpoints.py",
    "routes_builder\views_old.py",
    "routes_builder\views.py",
    "maps_view\views.py",
    "maps_view\views_old.py",
    "maps_view\management\commands\profile_endpoints.py"
)

foreach ($file in $files) {
    $filePath = "d:\Gemini\Provemaps_GPT-Tier2\mapsprovefiber\$file"
    if (Test-Path $filePath) {
        Write-Host "Atualizando: $file" -ForegroundColor Cyan
        
        $content = Get-Content $filePath -Raw
        
        # Substituir import completo
        $content = $content -replace 'from zabbix_api\.models import ([^`n]*Site|Device|Port|FiberCable|FiberEvent[^`n]*)', 'from inventory.models import $1'
        
        Set-Content -Path $filePath -Value $content -NoNewline
        
        Write-Host "✓ Concluído: $file" -ForegroundColor Green
    } else {
        Write-Host "✗ Arquivo não encontrado: $file" -ForegroundColor Red
    }
}

Write-Host "`nTodos os imports atualizados!" -ForegroundColor Yellow
