$ErrorActionPreference = "Stop"
chcp 65001 > $null
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"

Write-Host "==> Running test suite"
pytest tests -q

Write-Host "==> Building container image"
docker build -t learn-new:verify .

Write-Host "==> Rendering Helm chart"
helm template learn-new ops/helm/learn-new | Out-Null

Write-Host "Production verification completed."
