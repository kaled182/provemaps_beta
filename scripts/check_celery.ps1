Param(
  [string]$Url = "http://localhost:8000/celery/status",
  [int]$TimeoutSec = 8
)
try {
  $Response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing
} catch {
  Write-Host "✗ Falha ao obter status: $($_.Exception.Message)"; exit 3
}
try { $Json = $Response.Content | ConvertFrom-Json } catch { Write-Host "✗ Erro parse JSON"; exit 3 }
$status = $Json.status
$available = $Json.worker.available
if ($Response.StatusCode -eq 200 -and $status -eq 'ok') {
  Write-Host "✓ Celery OK (latency=$($Json.latency_ms)ms)"
  exit 0
} elseif ($available -eq $true) {
  Write-Host "⚠ Celery degradado (worker ativo, stats indisponíveis)"; exit 1
} else {
  Write-Host "✗ Celery indisponível (sem worker)"; exit 2
}
