Param(
  [string]$Url = "http://localhost:8000/celery/status",
  [int]$TimeoutSec = 8
)
try {
  $Response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing
} catch {
  Write-Host "ERROR: Failed to reach Celery status endpoint: $($_.Exception.Message)"; exit 3
}
try { $Json = $Response.Content | ConvertFrom-Json } catch { Write-Host "ERROR: Unable to parse JSON payload"; exit 3 }
$status = $Json.status
$available = $Json.worker.available
if ($Response.StatusCode -eq 200 -and $status -eq 'ok') {
  Write-Host "OK: Celery healthy (latency=$($Json.latency_ms)ms)"
  exit 0
} elseif ($available -eq $true) {
  Write-Host "WARN: Celery worker responding but statistics are unavailable"; exit 1
} else {
  Write-Host "ERROR: Celery unavailable (no worker reporting)"; exit 2
}
