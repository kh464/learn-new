$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001 | Out-Null
$env:PYTHONUTF8='1'

param(
  [Parameter(Mandatory = $true)]
  [string]$ArchivePath,
  [string]$TargetDir = ".",
  [switch]$Force
)

$resolvedArchive = Resolve-Path -LiteralPath $ArchivePath -ErrorAction Stop
$targetPath = Resolve-Path -LiteralPath $TargetDir -ErrorAction Stop
$workspacePath = Join-Path $targetPath ".learn"
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("learn-new-restore-" + [System.Guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null

try {
  Expand-Archive -LiteralPath $resolvedArchive -DestinationPath $stagingRoot -Force

  $manifestPath = Join-Path $stagingRoot "backup-manifest.json"
  if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Backup archive does not contain backup-manifest.json"
  }

  $restoredWorkspace = Join-Path $stagingRoot ".learn"
  if (-not (Test-Path -LiteralPath $restoredWorkspace)) {
    throw "Backup archive does not contain .learn workspace data"
  }

  if ((Test-Path -LiteralPath $workspacePath) -and (-not $Force)) {
    throw "Refusing to remove existing .learn without -Force."
  }

  if (Test-Path -LiteralPath $workspacePath) {
    Remove-Item -LiteralPath $workspacePath -Recurse -Force
  }

  Copy-Item -LiteralPath $restoredWorkspace -Destination $targetPath -Recurse -Force

  $restoredConfig = Join-Path $stagingRoot "config"
  if (Test-Path -LiteralPath $restoredConfig) {
    Copy-Item -LiteralPath $restoredConfig -Destination $targetPath -Recurse -Force
  }
}
finally {
  if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
  }
}

Write-Host "Restored workspace from $resolvedArchive to $targetPath"
