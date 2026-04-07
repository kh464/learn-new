# Frontend Dashboard

当前前端已拆成两个角色明确的入口，仍然保持前后端完全分离：

- 用户端：`/user.html`
- 管理端：`/admin.html`

## 目录结构

- 后端 API: `app/main.py`
- 后端说明页: `app/dashboard.py`
- 前端工程根目录: `frontend/`
- 导航页: `frontend/index.html`
- 用户端入口: `frontend/user.html`
- 管理端入口: `frontend/admin.html`
- 用户端挂载入口: `frontend/src/user-main.js`
- 管理端挂载入口: `frontend/src/admin-main.js`
- 用户端应用: `frontend/src/apps/user/UserApp.vue`
- 管理端应用: `frontend/src/apps/admin/AdminApp.vue`
- 共享 API 访问层: `frontend/src/lib/api.js`

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

- 导航页: `http://127.0.0.1:5173`
- 用户端: `http://127.0.0.1:5173/user.html`
- 管理端: `http://127.0.0.1:5173/admin.html`
- 后端 API: `http://127.0.0.1:8000`
- 后端说明页: `http://127.0.0.1:8000/dashboard`

## 角色边界

用户端只保留学习者会直接使用的能力：

- 创建和选择 session
- 提交 learner answer
- 查看 lesson、practice、feedback
- 查看 progress、due reviews、timeline

管理端承接运营和诊断能力：

- `X-Admin-Key`
- 异步 task queue、dead-letter、requeue
- runtime summary、config summary
- knowledge import / search
- checkpoint restore
- export preview

## 代理规则

`frontend/vite.config.js` 已代理这些路径到后端：

- `/api`
- `/health`
- `/metrics`
- `/ws`

因此前端本地开发时不需要额外配置 CORS。

## 构建命令

在 `frontend/` 目录下可直接使用：

```powershell
npm install
npm run dev
npm run dev:user
npm run dev:admin
npm run build
```

## 回归测试

- `tests/test_dashboard.py`
- `tests/test_dev_scripts.py`
- `tests/test_task_queue_ops.py`
- `tests/test_websocket_ops.py`
