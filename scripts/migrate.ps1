$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001 | Out-Null
$env:PYTHONUTF8='1'

param(
  [string]$PostgresDsn = $env:LEARN_NEW_POSTGRES_DSN
)

if (-not $PostgresDsn) {
  throw "LEARN_NEW_POSTGRES_DSN is required to run alembic upgrade head."
}

$env:LEARN_NEW_POSTGRES_DSN = $PostgresDsn
alembic upgrade head
