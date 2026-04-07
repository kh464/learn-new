$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001 | Out-Null
$env:PYTHONUTF8='1'

uvicorn app.main:app --reload
