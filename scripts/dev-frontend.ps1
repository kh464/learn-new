$ErrorActionPreference = "Stop"
chcp 65001 > $null
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

Push-Location frontend
try {
    if (-not (Test-Path -LiteralPath "node_modules")) {
        npm install
    }
    npm run dev
}
finally {
    Pop-Location
}
