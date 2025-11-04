# PowerShell script to update imports from zabbix_api.models to inventory.models

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
    Write-Host "Updating: $file" -ForegroundColor Cyan
        
        $content = Get-Content $filePath -Raw
        
        # Substituir import completo
        $content = $content -replace 'from zabbix_api\.models import ([^`n]*Site|Device|Port|FiberCable|FiberEvent[^`n]*)', 'from inventory.models import $1'
        
        Set-Content -Path $filePath -Value $content -NoNewline
        
        Write-Host "OK: Completed $file" -ForegroundColor Green
    } else {
        Write-Host "ERROR: File not found $file" -ForegroundColor Red
    }
}

Write-Host "`nAll imports updated!" -ForegroundColor Yellow
