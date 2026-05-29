# Run from repo root: .\start_mcp.ps1
$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "backend"
Set-Location $backend

if (-not $env:MCP_PORT) { $env:MCP_PORT = "8090" }
if (-not $env:MCP_HOST) { $env:MCP_HOST = "0.0.0.0" }

Write-Host "CareerLens MCP server: http://127.0.0.1:$($env:MCP_PORT)/mcp" -ForegroundColor Cyan
Write-Host "Health: http://127.0.0.1:$($env:MCP_PORT)/health" -ForegroundColor Cyan
python tools/mcp_server.py
