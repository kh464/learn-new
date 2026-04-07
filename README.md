# learn-new

领域精通型自适应教学多 Agent 系统 MVP。

当前实现聚焦后端主链路：

- FastAPI 服务
- LangGraph 编排学习流程
- 本地 `.learn/` 文件系统持久化
- 可选 SQLite / PostgreSQL 会话状态与 checkpoint 元数据存储
- 本地知识上传、分块检索和轻量 RAG
- 可选 Qdrant 向量知识索引
- 可选本地 / Docker 隔离 Python 沙箱执行与代码练习评估
- 研究、课程、技能、讲解、练习、进度六类 agent
- 可通过 `config/llm.yaml` 扩展到真实模型提供商
- 支持可选 admin API key、基础限流、`/metrics` 和请求 ID
- 支持角色化 API token、审计日志和运维接口保护
- 支持 Redis 限流后端
- 默认支持 SiliconFlow，且在无可用 API Key 时自动回退到本地 deterministic 模式

## 项目结构

```text
app/
  agents/           # 各角色 agent
  api/              # API schema
  config.py         # LLM 配置加载
  main.py           # FastAPI 入口
  models.py         # Pydantic 状态模型
  orchestrator.py   # LangGraph 编排器
  workspace.py      # .learn 工作区管理
config/
  llm.yaml          # 大模型配置文件
docs/
  llm-config.md     # LLM 配置说明
tests/              # 单元测试和集成测试
```

## 快速启动

先确认 Python 版本为 3.12+。

安装依赖：

```powershell
python -m pip install -e .[dev]
```

设置硅基流动 API Key：

```powershell
$env:SILICONFLOW_API_KEY="你的真实key"
```

启动服务：

```powershell
.\scripts\dev.ps1
```

如果使用 PostgreSQL 持久化，先执行数据库迁移：

```powershell
.\scripts\migrate.ps1
```

如果需要切换到其他配置文件，可先设置：

```powershell
$env:LEARN_NEW_CONFIG_PATH="config/llm.production.yaml"
```

如果使用挂载式 secrets：

```powershell
$env:LEARN_NEW_SECRET_DIR="D:\\path\\to\\secrets"
```

如果使用 HashiCorp Vault KV v2：

```powershell
$env:LEARN_NEW_VAULT_ADDR="https://vault.internal"
$env:LEARN_NEW_VAULT_TOKEN="your_vault_token"
$env:LEARN_NEW_VAULT_NAMESPACE="platform/team-a"
```

容器方式启动：

```powershell
docker compose up --build
```

带 PostgreSQL + Redis + Qdrant 的生产模板启动：

```powershell
docker compose -f docker-compose.yml -f docker-compose.infra.yml up --build
```

带 Prometheus + Grafana 的观测模板启动：

```powershell
docker compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.observability.yml up --build
```

带 Caddy 边缘反向代理模板启动：

```powershell
docker compose -f docker-compose.yml -f docker-compose.infra.yml -f docker-compose.edge.yml up --build
```

如果你直接在 Windows 终端里运行 Python 命令看到中文显示异常，优先使用 `scripts/dev.ps1` 和 `scripts/test.ps1`。
这两个脚本会先把控制台和 Python I/O 切到 UTF-8，再启动服务或测试。

浏览器可直接打开：

```text
http://127.0.0.1:8000/dashboard
```

仪表盘当前可直接完成这些操作：

- 创建学习 session
- 填写 background、每周时间预算和学习偏好创建更完整的 learner profile
- 上传本地知识片段到当前 session
- 直接导入外部 URL 到当前 session 知识索引
- 检索当前 session 已索引的知识片段
- 提交 learner answer 推进一轮教学
- 将 learner answer 以后台任务方式入队，并在页面内流式查看任务状态
- 启动显式 review 回合
- 查看当前到期复习队列
- 查看当前 session 的 latest feedback
- 在 dashboard 内预览 session export 快照
- 恢复历史 checkpoint
- 导出当前 session JSON
- 查看 `/api/runtime/summary`、`/api/audit`、`/api/logs/app` 聚合后的运行态摘要
- 查看 `/api/config` 暴露的 provider routing 与默认模型配置

更多前端面板和操作说明见：

- [docs/frontend-dashboard.md](docs/frontend-dashboard.md)

服务启动后可访问：

- `GET /dashboard`
- `GET /health`
- `GET /health/ready`
- `GET /metrics`
- `GET /api/config`
- `GET /api/audit`
- `GET /api/logs/app`
- `GET /api/runtime/summary`
- `POST /api/tasks/turns`
- `GET /api/tasks/{task_id}`
- `WS /ws/tasks/{task_id}`
- `GET /api/sessions`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/summary`
- `GET /api/sessions/{session_id}/timeline`
- `GET /api/sessions/{session_id}/checkpoints`
- `POST /api/sessions/{session_id}/checkpoints/{checkpoint_id}/restore`
- `GET /api/sessions/{session_id}/export`
- `POST /api/sessions/{session_id}/knowledge`
- `POST /api/sessions/{session_id}/knowledge/import-url`
- `GET /api/sessions/{session_id}/knowledge/search`
- `GET /api/sessions/{session_id}/reviews/due`
- `POST /api/sessions/{session_id}/reviews`
- `POST /api/sessions/{session_id}/turns`

`GET /health/ready` 现在会主动探测当前配置的 SQLite/PostgreSQL、Redis、Qdrant、Docker 等后端。
当必需后端不可达时会返回 `503`，并在响应体的 `checks` 字段里给出逐项诊断。

`GET /api/config` 会返回当前默认 provider、默认 profile、provider 列表、routing profile，以及 `llm_available`，用于判断当前是否会走真实模型。
`GET /api/logs/app` 可供 admin 拉取最近结构化应用日志。
`POST /api/tasks/turns` 可把一轮教学推进提交到后台 worker；随后用 `GET /api/tasks/{task_id}` 轮询状态和结果。
`WS /ws/tasks/{task_id}` 可流式接收后台任务的状态变化；dashboard 为了兼容浏览器环境，支持通过 query string 传递 `api_key` 连接该 WebSocket。
`POST /api/sessions/{session_id}/knowledge/import-url` 可抓取外部 URL 文本并直接入库到当前 session 知识索引。
URL 导入目前只接受 `http/https`，并按 `source + content` 指纹做幂等去重，重复导入不会重复写入 chunk。
配置中的 secret 现在除了环境变量、挂载文件和 `LEARN_NEW_SECRET_DIR` 之外，也支持 HashiCorp Vault KV v2 引用，例如 `${vault:secret/data/learn-new#siliconflow_api_key}`。

如果启用了 `security.enabled=true`，除 `GET /health`、`GET /health/ready`、`GET /dashboard` 之外的接口都需要携带 `X-Admin-Key`。
可以继续使用单个共享 key，也可以配置 `viewer / operator / admin` 三类 token。
启用角色化 token 后，非 admin 默认只能看到自己创建的 session。
如果启用了 `rate_limit.enabled=true`，服务会按鉴权后的 principal 优先限流；匿名流量则退回到 client IP 维度。
触发限流时会返回 `429`，并带上 `Retry-After` 响应头。
未处理的服务端异常会返回 `500` JSON，并在响应体里附带 `request_id`；同时会写入结构化应用日志，便于按请求回溯。
审计日志和应用日志默认都会自动裁剪，只保留最近配置条数，避免单文件无限增长。
如果请求携带 `traceparent`，服务会提取并回传 `X-Trace-ID`，同时写入审计日志和应用日志。

## API 示例

创建学习会话：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/sessions `
  -ContentType "application/json" `
  -Body '{"domain":"Python 异步编程","goal":"掌握 async/await"}'
```

列出所有会话：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri http://127.0.0.1:8000/api/sessions
```

推进一轮学习：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/sessions/<session_id>/turns `
  -ContentType "application/json" `
  -Body '{"learner_answer":"asyncio 可以调度协程并管理并发任务，因为它让等待 IO 时不阻塞主流程。"}'
```

上传知识资料：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/sessions/<session_id>/knowledge `
  -ContentType "application/json" `
  -Body '{"title":"Async Notes","content":"asyncio.create_task 可以并发调度多个协程任务。","source":"user://manual"}'
```

检索知识片段：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/sessions/<session_id>/knowledge/search?query=create_task 调度任务"
```

查看到期复习项：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/sessions/<session_id>/reviews/due"
```

开启一轮显式复习：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/sessions/<session_id>/reviews
```

查看 session 概览：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/sessions/<session_id>/summary"
```

查看最近事件时间线：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/sessions/<session_id>/timeline?limit=20"
```

列出可恢复快照：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/sessions/<session_id>/checkpoints"
```

恢复到指定快照：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/sessions/<session_id>/checkpoints/<checkpoint_id>/restore"
```

导出完整 session bundle：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/sessions/<session_id>/export"
```

## `.learn` 工作区

每个 session 会写入 `.learn/sessions/<session_id>/`，包括：

- `state.json`
- `progress.json`
- `curriculum.md`
- `lesson.json`
- `knowledge/indexed/knowledge.json`
- `knowledge/indexed/chunks.json`
- `skills/*.yaml`
- `labs/latest_practice.json`
- `checkpoints/*.json`

## 测试

运行测试：

```powershell
.\scripts\test.ps1
```

备份工作区：

```powershell
.\scripts\backup.ps1
```

如果需要同时把受版本控制的配置模板一起打包：

```powershell
.\scripts\backup.ps1 -IncludeConfig
```

恢复工作区：

```powershell
.\scripts\restore.ps1 -ArchivePath .\backups\learn-new-backup-YYYYMMDD-HHMMSS.zip -Force
```

构建生产镜像：

```powershell
docker build -t learn-new:local .
```

## 实现说明

这个版本是可运行 MVP，不是完整生产版。为了把架构文档里的核心思想尽快落到代码里，当前做了这些取舍：

- 默认使用确定性本地 agent 逻辑，避免没有外部服务时项目无法运行
- 已接入 `config/llm.yaml` 和真实 LLM 网关；当 SiliconFlow key 可用时，`Researcher`、`Instructor`、`Practice` 会优先调用真实模型
- 仍以本地文件系统为主，但已支持可选 SQLite 会话元数据存储，便于向正式数据库演进
- 已支持 PostgreSQL 会话元数据存储、Redis 限流后端、Qdrant 知识索引接入路径
- 默认使用本地轻量 Python 沙箱，适合开发期验证，不是完整生产级隔离
- 已支持可切换 Docker 沙箱后端，可用 `sandbox.backend=docker` 启用容器隔离练习执行
- 用 LangGraph 保留父 agent 主控和阶段流转结构
- 已实现基础间隔复习和显式 review 回合入口，连续低分会切到 remedial 教学模式
- 已实现 timeline/summary 可观察性接口，前端可以直接读取 session 概览、掌握度和事件流
- 已实现基础 admin API key 鉴权、进程内限流、`/metrics` 指标和 request id 响应头
- 已实现角色化 token 访问控制，`viewer` 只读，`operator` 可写业务接口，`admin` 额外拥有 `/metrics` 与 `/api/audit`
- 已实现基于 session owner 的可见性隔离，非 admin 默认只能访问自己创建的 session
- 已实现 JSONL 审计日志落盘与 `/api/audit` 最近记录查询
- 已实现按 path/status 聚合的 metrics，以及 `/api/runtime/summary` 运行时摘要
- 已实现主动式 readiness probe，`/health/ready` 可返回各后端逐项健康诊断
- 已实现结构化应用日志落盘，未处理异常会附带 request id 并写入 `app_log_path`
- 已为 audit/app 日志补充按行数自动裁剪的 retention 配置
- 已实现 checkpoint 列表与恢复接口，可从 `.learn/checkpoints` 显式回滚 session 状态
- 已实现 session export 接口，可导出 summary、timeline、checkpoint 和核心工件
- 已实现 session index 接口，前端仪表盘可以直接列出全部学习会话
- 已实现轻量 dashboard 页面，可直接消费现有 API 展示 session list、summary、timeline、lesson、practice、latest feedback、due review queue、knowledge search、export preview，并支持创建 session、上传知识、检索知识、提交回答、启动 review、恢复 checkpoint、预览导出、导出 session
- 已补充 `Dockerfile`、`.dockerignore`、`docker-compose.yml` 作为单节点部署底座
- 已补充 `config/llm.production.yaml` 和 `docker-compose.infra.yml`，可直接拉起 PostgreSQL、Redis、Qdrant 的基础生产模板
- 容器模板已补充 healthcheck、只读根文件系统、`no-new-privileges`、`cap_drop=ALL`、`tmpfs` 与 `pids_limit`
- 已补充 Alembic 迁移目录、首个 PostgreSQL schema migration、`scripts/migrate.ps1`，以及容器启动前自动 `alembic upgrade head`
- 已补充内存型异步 task queue 和后台 worker，可把 turn 执行从请求线程移到后台并按 owner 隔离任务查询
- 已补充可切换的 SQLite 持久化任务队列后端，任务状态可跨进程重启保留，并支持有限次自动重试
- 已补充可切换的 PostgreSQL 持久化任务队列后端，适合和多实例共享同一任务账本，并支持租约过期后的任务重抢占
- PostgreSQL 任务队列的租约时长与轮询间隔现已配置化，可按环境调优 worker 抢占与恢复节奏
- 已补充任务状态 WebSocket 推送接口，后台任务可流式返回状态变化
- 已补充 `docker-compose.observability.yml`、Prometheus 抓取配置和 Grafana datasource provisioning
- 已补充 trace id 透传和 Prometheus alert rules 模板
- 已补充 Caddy 反向代理模板和 K8s deployment/service/ingress 清单
- 已补充 URL 抓取式外部知识导入，并带 `http/https` 护栏和幂等去重
- 已补充 Helm chart 模板，并覆盖 ConfigMap、Secret、HPA、PDB、ServiceAccount、RBAC、NetworkPolicy、探针、resources 和 secret 挂载参数
- 已补充基础备份与恢复脚本，带 manifest 校验与显式 `-Force` 护栏，便于单节点灾备和本地恢复

后续扩展优先级建议：

1. 接入真实 LLM provider
2. 接入向量检索与外部知识采集
3. 接入沙箱执行器
4. 补 WebSocket 流式和前端界面
