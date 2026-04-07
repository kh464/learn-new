from __future__ import annotations

from fastapi.responses import HTMLResponse


def render_dashboard() -> HTMLResponse:
    return HTMLResponse(
        r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Learn New Frontend Workspace</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, #f7f1e7 0%, #ebe3d3 100%);
      color: #192235;
      font-family: "Segoe UI", sans-serif;
    }
    main {
      width: min(760px, calc(100vw - 32px));
      padding: 32px;
      background: rgba(255, 250, 241, 0.94);
      border: 1px solid rgba(25, 34, 53, 0.12);
      border-radius: 24px;
      box-shadow: 0 24px 60px rgba(22, 28, 39, 0.12);
    }
    h1, p, pre { margin: 0; }
    h1 { margin-bottom: 12px; font-size: 32px; }
    p { margin-top: 12px; line-height: 1.6; }
    pre {
      margin-top: 18px;
      padding: 16px;
      background: #202a39;
      color: #f4f0e9;
      border-radius: 16px;
      overflow: auto;
    }
    code { font-family: Consolas, monospace; }
  </style>
</head>
<body>
  <main>
    <h1>Frontend Workspace</h1>
    <p>The dashboard frontend now lives in <code>frontend/</code> as a standard Vue + Vite project.</p>
    <p>Start the backend API first, then run the frontend dev server separately.</p>
    <pre>backend  -> .\scripts\dev.ps1
frontend -> cd frontend
frontend -> npm install
frontend -> npm run dev

or:

frontend -> .\scripts\dev-frontend.ps1

or:

fullstack -> .\scripts\dev-fullstack.ps1

frontend home:  http://127.0.0.1:5173
learner app:    http://127.0.0.1:5173/user.html
admin app:      http://127.0.0.1:5173/admin.html
api base:       http://127.0.0.1:8000

used APIs:
- /api/sessions
- /api/tasks/turns</pre>
  </main>
</body>
</html>"""
    )
