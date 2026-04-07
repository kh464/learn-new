# Dashboard Frontend

`/dashboard` 现在是一个完整的运维式前端，不再是单块内联页面。

## 页面结构

- `Session Workspace`
  - 创建 session
  - 维护 domain / goal / background / 每周时间预算 / preferences
  - 浏览已有 session 列表并切换上下文
- `Run Sync Turn`
  - 直接调用 `POST /api/sessions/{session_id}/turns`
  - 用于快速验证教学回路
- `Async Task Console`
  - 调用 `POST /api/tasks/turns`
  - 优先通过 `WS /ws/tasks/{task_id}` 订阅任务状态
  - 如果 WebSocket 不可用，可回退到 `GET /api/tasks/{task_id}` 轮询
- `Dead Letter Queue`
  - 调用 `GET /api/tasks/dead-letter`
  - 支持在页面内直接执行 `POST /api/tasks/{task_id}/requeue`
- `Knowledge Pipeline`
  - 支持文本上传
  - 支持 `POST /api/sessions/{session_id}/knowledge/import-url` 导入 URL
  - 支持 `GET /api/sessions/{session_id}/knowledge/search`
- `Runtime Pulse`
  - 汇总 `GET /api/runtime/summary`
  - 尝试拉取 `GET /api/audit` 与 `GET /api/logs/app`
  - 展示 provider routing 与默认模型配置
- `Session Activity / Progress Snapshot / Export`
  - 展示 summary、timeline、due reviews、checkpoints、export preview

## 静态资源

- HTML shell: `app/dashboard.py`
- CSS: `app/static/dashboard.css`
- JS: `app/static/dashboard.js`

FastAPI 在 `/static` 挂载静态目录：

- `/static/dashboard.css`
- `/static/dashboard.js`

## 鉴权说明

页面顶部的 `X-Admin-Key` 输入框会写入 `localStorage`，随后自动附带到所有 HTTP API 请求。

浏览器原生 WebSocket 不能像 `fetch` 一样自定义请求头，所以 dashboard 在连接 `WS /ws/tasks/{task_id}` 时会在 query string 里附带 `api_key`。后端当前同时支持：

- Header: `X-Admin-Key`
- Query: `?api_key=...`

这只是为了浏览器端任务流可用，不影响现有 header 鉴权客户端。

## 回归测试

前端相关最关键的测试是：

- `tests/test_dashboard.py`
- `tests/test_websocket_ops.py`
- `tests/test_task_queue_ops.py`
- `tests/test_security_ops.py`
- `tests/test_observability_ops.py`
