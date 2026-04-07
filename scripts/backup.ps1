$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001 | Out-Null
$env:PYTHONUTF8='1'

param(
  [string]$WorkspaceRoot = ".learn",
  [string]$OutputDir = "backups",
  [switch]$IncludeConfig
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$workspacePath = Resolve-Path -LiteralPath $WorkspaceRoot -ErrorAction Stop
$outputPath = Join-Path $OutputDir "learn-new-backup-$timestamp.zip"
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("learn-new-backup-" + [System.Guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null

if (Test-Path $outputPath) {
  Remove-Item -LiteralPath $outputPath -Force
}

try {
  Copy-Item -LiteralPath $workspacePath -Destination (Join-Path $stagingRoot ".learn") -Recurse -Force

  $configFiles = @()
  if ($IncludeConfig) {
    foreach ($configFile in @("config\\llm.yaml", "config\\llm.production.yaml")) {
      if (Test-Path -LiteralPath $configFile) {
        $destinationDir = Join-Path $stagingRoot "config"
        New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
        Copy-Item -LiteralPath (Resolve-Path -LiteralPath $configFile) -Destination $destinationDir -Force
        $configFiles += [System.IO.Path]::GetFileName($configFile)
      }
    }
  }

  $manifest = @{
    created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    workspace_root = $workspacePath.Path
    include_config = [bool]$IncludeConfig
    config_files = $configFiles
  }
  $manifestPath = Join-Path $stagingRoot "backup-manifest.json"
  $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

  $archiveInputs = Get-ChildItem -Force -LiteralPath $stagingRoot | Select-Object -ExpandProperty FullName
  Compress-Archive -LiteralPath $archiveInputs -DestinationPath $outputPath -Force
}
finally {
  if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
  }
}

Write-Host "Backup written to $outputPath"
