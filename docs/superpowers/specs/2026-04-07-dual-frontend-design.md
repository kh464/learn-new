# Dual Frontend Design

## Goal

将当前混合了学习流与运维流的单一前端，拆成两个清晰入口：

- 用户端：面向学习者
- 管理端：面向管理者/开发者/运维

保持前后端完全分离，继续使用同一个 `frontend/` 标准 Vue + Vite 工程。

## Chosen Approach

采用单仓双入口方案，而不是再建两套独立前端仓。

- `frontend/index.html` 作为入口导航页
- `frontend/user.html` 加载学习者前端
- `frontend/admin.html` 加载管理后台
- 共享 `frontend/src/lib/api.js` 和通用样式

这样可以在不引入额外工程复杂度的前提下，把角色边界立即拉清。

## Information Architecture

### 用户端

只保留学习者会直接使用的能力：

- 创建或选择 session
- 提交 learner answer
- 查看 lesson / practice / latest feedback
- 查看 progress summary / timeline / due reviews

不暴露这些管理能力：

- `X-Admin-Key`
- runtime/config 面板
- async task queue / dead-letter
- knowledge import / knowledge search
- checkpoint restore
- export preview

### 管理端

保留现有运营与诊断能力：

- session 索引与创建
- task queue / websocket / dead-letter / requeue
- runtime summary / config summary
- knowledge import / search
- checkpoint restore
- export preview
- `X-Admin-Key`

## File Boundaries

- `frontend/src/apps/user/`：学习者前端
- `frontend/src/apps/admin/`：管理后台
- `frontend/src/components/admin/`：仅管理端组件
- `frontend/src/components/user/`：仅用户端组件
- `frontend/src/lib/`：共享 API 和通用工具

## Routing and Runtime

不引入 Vue Router。

原因：

- 当前需求是入口级拆分，不是复杂 SPA 信息架构
- 多页面入口已经足够满足“用户端”和“管理端”分离
- 可以减少重构面，优先解决角色混乱问题

开发时继续使用 Vite dev server；通过不同页面访问不同入口：

- `/`
- `/user.html`
- `/admin.html`

## Error Handling

- 用户端请求失败时只展示学习流相关的错误信息
- 管理端保留更详细的状态与诊断提示
- 共享 API 层继续负责 HTTP 错误抛出和 WebSocket 建连

## Testing

需要覆盖这些行为：

- `/dashboard` 说明页同时指向用户端和管理端入口
- `frontend/package.json` 暴露双入口相关脚本
- `frontend/` 存在 `user.html` 和 `admin.html`
- 用户端源码不再引用管理组件
- 管理端源码继续包含任务、运行态、知识、导出能力

## Scope Guard

这次只做前端角色拆分，不改后端 API 权限模型，不引入真正的 learner auth，也不引入新的状态管理库。
