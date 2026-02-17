<#
EKA – End-to-End reset & run (Docker)

What it does:
  1) docker compose down -v --remove-orphans
  2) docker compose pull (base images)
  3) docker compose build (api/ui/web)
  4) docker compose up -d
  5) waits for http://localhost:8000/health to be OK

Run from repo root (Windows PowerShell):
  powershell -ExecutionPolicy Bypass -File .\scripts\e2e_reset.ps1

Optional flags:
  -NoCache        Build images with --no-cache
  -SkipModelPull  Skip explicit ollama pulls (ollama-init already pulls by default)
#>

[CmdletBinding()]
Param(
  [switch]$NoCache,
  [switch]$SkipModelPull
)

$ErrorActionPreference = 'Stop'

function Require-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $name"
  }
}

Require-Command docker

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$composeDir = Join-Path $repoRoot 'docker'
$composeFile = Join-Path $composeDir 'docker-compose.yml'

Write-Host "==> Repo root: $repoRoot"
Write-Host "==> Compose:   $composeFile"

Push-Location $composeDir
try {
  Write-Host "\n==> [1/5] Stop + remove containers/volumes" -ForegroundColor Cyan
  docker compose -f $composeFile down -v --remove-orphans

  Write-Host "\n==> [2/5] Pull base images" -ForegroundColor Cyan
  docker compose -f $composeFile pull qdrant ollama ollama-init

  Write-Host "\n==> [3/5] Build local images (api/ui/web)" -ForegroundColor Cyan
  if ($NoCache) {
    docker compose -f $composeFile build --no-cache --pull
  } else {
    docker compose -f $composeFile build --pull
  }

  Write-Host "\n==> [4/5] Start stack" -ForegroundColor Cyan
  docker compose -f $composeFile up -d

  if (-not $SkipModelPull) {
    Write-Host "\n==> (Optional) Ensure Ollama models are present" -ForegroundColor Cyan
    # ollama-init already pulls on startup; this is a best-effort safety net.
    try {
      docker compose -f $composeFile exec -T ollama ollama pull llama3.1 | Out-Host
      docker compose -f $composeFile exec -T ollama ollama pull nomic-embed-text | Out-Host
    } catch {
      Write-Warning "Model pull step failed (can ignore if ollama-init already pulled): $($_.Exception.Message)"
    }
  }

  Write-Host "\n==> [5/5] Wait for API health" -ForegroundColor Cyan
  $healthUrl = 'http://localhost:8000/health'
  $ok = $false
  for ($i=1; $i -le 90; $i++) {
    try {
      $resp = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 2
      if ($resp.ok -eq $true) { $ok = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
  }

  if (-not $ok) {
    Write-Warning "API health check did not turn OK yet. Check logs: docker compose logs -f api"
  } else {
    Write-Host "\n✅ System is up." -ForegroundColor Green
    Write-Host "   Web UI:      http://localhost:3000"
    Write-Host "   Streamlit:   http://localhost:8501"
    Write-Host "   API Swagger: http://localhost:8000/docs"
    Write-Host "   Qdrant:      http://localhost:6333/dashboard"
  }

} finally {
  Pop-Location
}
