# Run from repo root after starting the backend: .\verify_api.ps1
# Confirms the process on port 8000 is this project's API (not another app).
$ErrorActionPreference = "Stop"
$base = if ($env:API_URL) { $env:API_URL.Trim().TrimEnd("/") } else { "http://127.0.0.1:8000" }
$status = "$base/status"
Write-Host "GET $status" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri $status -UseBasicParsing
} catch {
    Write-Host "FAILED: $_" -ForegroundColor Red
    exit 1
}
Write-Host "HTTP $($r.StatusCode)" -ForegroundColor Green
Write-Host $r.Content
$j = $r.Content | ConvertFrom-Json
if ($j.service -ne "careerlens") {
    Write-Host "ERROR: expected service=`"careerlens`", got $($j.service)" -ForegroundColor Red
    exit 1
}
if ($j.post_auth_google_registered -ne $true) {
    Write-Host "ERROR: post_auth_google_registered must be true (start API from this repo: .\start_backend.ps1)" -ForegroundColor Red
    exit 1
}
Write-Host "OK — CareerLens API on $base looks correct." -ForegroundColor Green
exit 0
