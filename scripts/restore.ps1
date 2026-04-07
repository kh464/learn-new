$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001 | Out-Null
$env:PYTHONUTF8='1'

param(
  [Parameter(Mandatory = $true)]
  [string]$ArchivePath,
  [string]$TargetDir = "."
)

$resolvedArchive = Resolve-Path -LiteralPath $ArchivePath -ErrorAction Stop
$targetPath = Resolve-Path -LiteralPath $TargetDir -ErrorAction Stop
$workspacePath = Join-Path $targetPath ".learn"

if (Test-Path $workspacePath) {
  Remove-Item -LiteralPath $workspacePath -Recurse -Force
}

Expand-Archive -LiteralPath $resolvedArchive -DestinationPath $targetPath -Force
Write-Host "Restored workspace from $resolvedArchive to $targetPath"
