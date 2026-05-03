param(
  [string]$Database = "od_approval_db",
  [string]$User = "postgres",
  [string]$OutputDir = "database/backups"
)
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $OutputDir "$Database`_$timestamp.sql"
pg_dump -U $User -d $Database -f $out
Write-Host "Backup saved to $out"
