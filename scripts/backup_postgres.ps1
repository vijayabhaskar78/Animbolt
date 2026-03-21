$ErrorActionPreference = "Stop"

param(
  [string]$OutputDir = ".\backups"
)

if (!(Test-Path $OutputDir)) {
  New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $OutputDir "cursor2d-$stamp.sql"

docker compose exec -T postgres pg_dump -U $env:POSTGRES_USER $env:POSTGRES_DB > $target
Write-Output "Backup written to $target"

