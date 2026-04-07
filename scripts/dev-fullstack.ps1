$ErrorActionPreference = "Stop"
chcp 65001 > $null
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

Start-Process powershell -ArgumentList "-NoExit", "-File", "scripts/dev.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", "scripts/dev-frontend.ps1"
