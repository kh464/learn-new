# LLM Configuration

The project uses `config/llm.yaml` as the runtime configuration file.

## Current default

- Default provider: `siliconflow`
- API key source: environment variable `SILICONFLOW_API_KEY`
- Recommended local template: `.env.example`

## File structure

`config/llm.yaml` is split into these sections:

1. `llm.default_provider` and `llm.default_profile`
2. `llm.providers.<provider>` for provider connection details
3. `llm.routing.profiles` for task-to-model mapping
4. `storage` for session metadata persistence
5. `security` for admin API key protection
6. `rate_limit` for in-process request throttling
7. `observability` for request id and metrics behavior
8. `sandbox` for practice execution isolation

## How to set the API key

Temporary for the current PowerShell session:

```powershell
$env:SILICONFLOW_API_KEY="your_real_api_key"
```

Permanent for the current Windows user:

```powershell
[Environment]::SetEnvironmentVariable("SILICONFLOW_API_KEY", "your_real_api_key", "User")
```

After setting it, restart the terminal or reload the shell before starting the app.

## How to switch models

Edit `config/llm.yaml` and replace the values under:

- `llm.providers.siliconflow.models`
- `llm.routing.profiles`

Keep the provider name and model mapping aligned.

## How to add another provider later

1. Add a new block under `llm.providers`
2. Use an environment variable for `api_key`
3. Add matching entries under `llm.routing.profiles`

Example environment variables:

```powershell
$env:OPENAI_API_KEY="your_openai_key"
$env:ANTHROPIC_API_KEY="your_anthropic_key"
$env:DEEPSEEK_API_KEY="your_deepseek_key"
$env:LEARN_NEW_ADMIN_KEY="your_admin_key"
```

## Storage backend

Use file-backed metadata by default:

```yaml
storage:
  backend: file
  sqlite_path: .learn/sessions.db
```

Switch to SQLite-backed session metadata:

```yaml
storage:
  backend: sqlite
  sqlite_path: .learn/sessions.db
```

When `backend=sqlite`, session state and checkpoint metadata can still be loaded even if local `state.json` or checkpoint files are missing. The `.learn/` workspace is still mirrored for artifacts and exports.

## Admin API key protection

Protect all routes except `GET /health`:

```yaml
security:
  enabled: true
  api_key_header: X-Admin-Key
  api_key: ${LEARN_NEW_ADMIN_KEY}
```

Send the header on protected requests:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri http://127.0.0.1:8000/api/config `
  -Headers @{ "X-Admin-Key" = $env:LEARN_NEW_ADMIN_KEY }
```

## Rate limiting

Enable simple in-process throttling:

```yaml
rate_limit:
  enabled: true
  requests: 120
  window_seconds: 60
```

This limiter is process-local. It is useful for single-node hardening, but not a substitute for Redis or gateway-level rate limiting in production.

## Metrics and request ids

`/metrics` exposes a small Prometheus-style text payload.
Every response gets the header configured by `observability.request_id_header`.

```yaml
observability:
  metrics_enabled: true
  request_id_header: X-Request-ID
```

## Sandbox backend

Local development default:

```yaml
sandbox:
  backend: local
  timeout_seconds: 10
  docker_image: python:3.12-slim
  memory_mb: 256
  cpu_limit: 1.0
```

Docker-isolated execution:

```yaml
sandbox:
  backend: docker
  timeout_seconds: 10
  docker_image: python:3.12-slim
  memory_mb: 256
  cpu_limit: 1.0
```

When `backend=docker`, the practice evaluator runs Python code inside an ephemeral container with `--network none`, `--read-only`, CPU limits, and memory limits.
