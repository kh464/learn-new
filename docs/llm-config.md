# LLM Configuration

The project uses `config/llm.yaml` as the runtime configuration file.
You can override the runtime file with `LEARN_NEW_CONFIG_PATH`.

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
9. `knowledge` for vector index integration

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
$env:LEARN_NEW_VIEWER_KEY="your_viewer_key"
$env:LEARN_NEW_OPERATOR_KEY="your_operator_key"
$env:LEARN_NEW_POSTGRES_DSN="postgresql://learn_new:learn_new@localhost:5432/learn_new"
$env:LEARN_NEW_REDIS_URL="redis://localhost:6379/0"
$env:LEARN_NEW_QDRANT_URL="http://localhost:6333"
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

Switch to PostgreSQL-backed session metadata:

```yaml
storage:
  backend: postgres
  postgres_dsn: ${LEARN_NEW_POSTGRES_DSN}
```

The PostgreSQL store persists session state and checkpoint metadata in SQL tables while the `.learn/` workspace continues to mirror artifacts for exports and local inspection.
The repository also includes `config/llm.production.yaml` as a ready-made template that wires PostgreSQL, Redis, Qdrant, Docker sandboxing, and role-based tokens together.

## Admin API key protection

Protect all routes except `GET /health`:

```yaml
security:
  enabled: true
  api_key_header: X-Admin-Key
  api_key: ${LEARN_NEW_ADMIN_KEY}
```

For role-based access, prefer `principals` over a single shared key:

```yaml
security:
  enabled: true
  api_key_header: X-Admin-Key
  principals:
    - name: viewer
      api_key: ${LEARN_NEW_VIEWER_KEY}
      role: viewer
    - name: operator
      api_key: ${LEARN_NEW_OPERATOR_KEY}
      role: operator
    - name: admin
      api_key: ${LEARN_NEW_ADMIN_KEY}
      role: admin
```

Role behavior:

- `viewer`: read-only API access
- `operator`: read + write learning APIs
- `admin`: read + write + operational APIs such as `/metrics` and `/api/audit`

When role-based access is enabled, newly created sessions are scoped to the creating principal. Non-admin principals only see and fetch their own sessions.
Runtime rate limiting is also keyed by authenticated principal first, so different operators do not consume the same bucket when they share an ingress IP.

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
  backend: redis
  requests: 120
  window_seconds: 60
  redis_url: ${LEARN_NEW_REDIS_URL}
  key_prefix: learn-new:rate
```

With `backend=memory`, the limiter is process-local and useful for single-node hardening.
With `backend=redis`, counters are stored in Redis instead of process memory.
When a request is throttled, the API responds with `429` and a `Retry-After` header.

## Metrics and request ids

`/metrics` exposes a small Prometheus-style text payload.
Every response gets the header configured by `observability.request_id_header`.

```yaml
observability:
  metrics_enabled: true
  request_id_header: X-Request-ID
  audit_log_path: .learn/audit/events.jsonl
  app_log_path: .learn/logs/app.jsonl
```

`/api/audit` returns recent audit entries when accessed with an admin token.
`/api/runtime/summary` returns backend selection, metric snapshots, live backend probe results, security summary, and audit summary for admin operators.
`/health/ready` actively probes configured storage, rate-limit, knowledge, and sandbox backends. It returns `503` when a required backend is configured but unavailable.
Unhandled exceptions return a JSON `500` response containing the active request id, and the event is appended to `observability.app_log_path`.

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

When `backend=docker`, the practice evaluator runs Python code inside an ephemeral container with `--network none`, `--read-only`, `--cap-drop=ALL`, `no-new-privileges`, a nobody user, pid/file descriptor limits, CPU limits, and memory limits.

## Knowledge backend

Default file-backed chunk storage:

```yaml
knowledge:
  backend: file
  qdrant_url: ${LEARN_NEW_QDRANT_URL}
  collection_name: learn-new
  vector_size: 16
```

Qdrant-backed retrieval:

```yaml
knowledge:
  backend: qdrant
  qdrant_url: ${LEARN_NEW_QDRANT_URL}
  collection_name: learn-new
  vector_size: 16
```

When `backend=qdrant`, ingested chunks are upserted into Qdrant with a deterministic in-process embedding and searched through the Qdrant HTTP API.
