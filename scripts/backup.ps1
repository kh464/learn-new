$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001 | Out-Null
$env:PYTHONUTF8='1'

param(
  [string]$WorkspaceRoot = ".learn",
  [string]$OutputDir = "backups"
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$workspacePath = Resolve-Path -LiteralPath $WorkspaceRoot -ErrorAction Stop
$outputPath = Join-Path $OutputDir "learn-new-backup-$timestamp.zip"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if (Test-Path $outputPath) {
  Remove-Item -LiteralPath $outputPath -Force
}

Compress-Archive -Path $workspacePath -DestinationPath $outputPath -Force
Write-Host "Backup written to $outputPath"
