# Run from repo root: .\start_backend.ps1
# Fails fast if port 8000 is taken — otherwise an OLD Python process keeps serving and
# routes like POST /api/auth/google return 404 while /api/auth/login may still exist.
$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "backend"
if (-not (Test-Path $backend)) {
    Write-Error "Expected folder not found: $backend"
}
Set-Location $backend

# If Postgres in .env is not running, start anyway with local SQLite for this session:
#   PowerShell:  $env:FORCE_SQLITE = "1";  .\start_backend.ps1
if ($env:FORCE_SQLITE -eq "1") {
    $dbFile = Join-Path $backend "careerlens.db"
    $env:DATABASE_URL = $dbFile
    Write-Host "FORCE_SQLITE=1 → using SQLite: $dbFile" -ForegroundColor Cyan
}

$port = 8000
if ($env:PORT) {
    try { $port = [int]$env:PORT.Trim() } catch { $port = 8000 }
}

$listeners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
if ($listeners) {
    $pids = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    Write-Host ""
    Write-Host "Port $port is already in use (PID: $($pids -join ', '))." -ForegroundColor Yellow
    Write-Host "Stop that process first, e.g. Task Manager -> Details -> end that PID," -ForegroundColor Yellow
    Write-Host "or:  Stop-Process -Id $($pids[0]) -Force" -ForegroundColor Yellow
    Write-Host "Then run .\start_backend.ps1 again. A leftover server often causes 404 on Google auth." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Bind 0.0.0.0 so both IPv4 localhost and 127.0.0.1 reach the server (Vite proxy uses localhost:8000).
$bindHost = "0.0.0.0"
if ($env:HOST) {
    $t = $env:HOST.Trim()
    if ($t) { $bindHost = $t }
}
python -m uvicorn app.main:app --reload --host $bindHost --port $port
