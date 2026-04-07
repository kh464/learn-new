# Frontend

这是 `learn-new` 的独立前端工程，采用 Vue 3 + Vite。

## 本地开发

先启动后端：

```powershell
..\scripts\dev.ps1
```

再在当前目录运行：

```powershell
npm install
npm run dev
```

前端默认地址：`http://127.0.0.1:5173`

## 生产构建

```powershell
npm run build
```

## 代理说明

开发服务器会把以下路径代理到 `http://127.0.0.1:8000`：

- `/api`
- `/health`
- `/metrics`
- `/ws`
