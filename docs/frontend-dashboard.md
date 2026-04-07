# Frontend Dashboard

当前前端已经改为前后端完全分离的标准 Vue 工程。

## 目录结构

- 后端 API: `app/main.py`
- 后端说明页: `app/dashboard.py`
- 前端工程根目录: `frontend/`
- Vite 入口: `frontend/index.html`
- Vue 挂载入口: `frontend/src/main.js`
- 主应用: `frontend/src/App.vue`
- 组件目录: `frontend/src/components/`
- API 访问层: `frontend/src/lib/api.js`

## 开发运行

先启动后端：

```powershell
.\scripts\dev.ps1
```

再启动前端：

```powershell
.\scripts\dev-frontend.ps1
```

或者直接双开：

```powershell
.\scripts\dev-fullstack.ps1
```

默认地址：

- 前端: `http://127.0.0.1:5173`
- 后端 API: `http://127.0.0.1:8000`
- 后端说明页: `http://127.0.0.1:8000/dashboard`

## 代理规则

`frontend/vite.config.js` 已代理这些路径到后端：

- `/api`
- `/health`
- `/metrics`
- `/ws`

因此前端本地开发时不需要额外配置 CORS。

## 页面能力

当前 Vue 前端保留了原 dashboard 的核心能力：

- session 创建与切换
- 同步 turn 提交
- 异步 task 入队、轮询、WebSocket 状态流
- dead-letter 列表与 requeue
- URL 导入知识、文本上传、knowledge search
- runtime summary 与 config summary
- checkpoints 与 export preview

## 构建命令

在 `frontend/` 目录下可直接使用：

```powershell
npm install
npm run dev
npm run build
```

## 回归测试

- `tests/test_dashboard.py`
- `tests/test_dev_scripts.py`
- `tests/test_task_queue_ops.py`
- `tests/test_websocket_ops.py`
