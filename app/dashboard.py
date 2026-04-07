from __future__ import annotations

from fastapi.responses import HTMLResponse


def render_dashboard() -> HTMLResponse:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Learn New Dashboard</title>
  <link rel="stylesheet" href="/static/dashboard.css" />
</head>
<body>
  <div id="app-shell" class="app-shell" data-dashboard-version="2">
    <aside class="sidebar">
      <div class="brand-card panel">
        <p class="eyebrow">Learn New</p>
        <h1>Learning Operations Center</h1>
        <p class="lede">A browser control room for sessions, async turns, runtime posture, and knowledge ingestion.</p>
      </div>

      <section class="panel section-card">
        <div class="section-heading">
          <p class="eyebrow">Access</p>
          <h2>Admin Header</h2>
        </div>
        <label class="field">
          <span>X-Admin-Key</span>
          <input id="admin-key-input" name="admin-key" placeholder="Optional X-Admin-Key" />
        </label>
        <p class="microcopy">Requests automatically include the configured admin header when present.</p>
      </section>

      <section class="panel section-card">
        <div class="section-heading">
          <p class="eyebrow">Create</p>
          <h2>Session Workspace</h2>
        </div>
        <form id="create-session-form" class="stack-form">
          <label class="field">
            <span>Domain</span>
            <input id="domain-input" name="domain" placeholder="Python async programming" />
          </label>
          <label class="field">
            <span>Goal</span>
            <input id="goal-input" name="goal" placeholder="Master async/await" />
          </label>
          <label class="field">
            <span>Background</span>
            <textarea id="background-input" name="background" placeholder="Current experience, blockers, and context."></textarea>
          </label>
          <label class="field">
            <span>Hours / Week</span>
            <input id="time-budget-input" name="available_time_hours_per_week" type="number" min="1" value="5" />
          </label>
          <label class="field">
            <span>Preferences</span>
            <input id="preferences-input" name="preferences" placeholder="project, examples, coaching" value="project, examples" />
          </label>
          <button class="action primary" type="submit">Create Session</button>
        </form>
      </section>

      <section class="panel section-card">
        <div class="section-heading">
          <p class="eyebrow">Index</p>
          <h2>Active Sessions</h2>
        </div>
        <div id="session-list" class="session-list">
          <div class="empty">Loading sessions...</div>
        </div>
      </section>
    </aside>

    <main class="main-column">
      <section class="hero panel">
        <div>
          <p class="eyebrow">Mission Control</p>
          <h2 id="title">No Session Selected</h2>
          <p id="subtitle" class="lede">Select a session to inspect the learning loop, queue work, import knowledge, and observe runtime health.</p>
        </div>
        <div class="hero-actions">
          <button id="refresh-data" class="action secondary" type="button">Refresh Session</button>
          <button id="load-export-preview" class="action secondary" type="button">Load Export Preview</button>
          <button id="export-session" class="action ghost" type="button">Open Export JSON</button>
        </div>
        <div id="action-status" class="status-banner">Ready.</div>
        <div id="hero" class="hero-metrics"></div>
      </section>

      <section class="main-grid">
        <div class="column">
          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Turn Loop</p>
              <h2>Run Sync Turn</h2>
            </div>
            <form id="turn-form" class="stack-form">
              <label class="field">
                <span>Learner Answer</span>
                <textarea id="answer-input" name="answer" placeholder="Submit Turn: explain the learner's latest answer, code, or reflection."></textarea>
              </label>
              <div class="action-row">
                <button class="action primary" type="submit">Run Sync Turn</button>
                <button id="start-review" class="action ghost" type="button">Start Review</button>
              </div>
            </form>
          </article>

          <article class="panel section-card" id="async-task-console">
            <div class="section-heading">
              <p class="eyebrow">Queue</p>
              <h2>Async Task Console</h2>
            </div>
            <form id="task-form" class="stack-form">
              <label class="field">
                <span>Queued Learner Answer</span>
                <textarea id="task-answer-input" name="task-answer" placeholder="Queue a turn and stream execution over WebSocket."></textarea>
              </label>
              <div class="action-row">
                <button class="action primary" type="submit">Queue Turn Task</button>
                <button id="poll-task-status" class="action secondary" type="button">Poll Task Status</button>
              </div>
            </form>
            <div id="task-stream-status" class="status-banner muted">No queued task yet.</div>
            <div id="task-stream" class="task-stream">
              <div class="empty">Queued task events will appear here.</div>
            </div>
          </article>

          <article class="panel section-card" id="knowledge-pipeline">
            <div class="section-heading">
              <p class="eyebrow">Knowledge</p>
              <h2>Knowledge Pipeline</h2>
            </div>
            <form id="knowledge-url-form" class="stack-form">
              <label class="field">
                <span>Knowledge URL</span>
                <input id="knowledge-url-input" name="knowledge-url" placeholder="https://example.com/reference" />
              </label>
              <button class="action secondary" type="submit">Import URL</button>
            </form>
            <form id="knowledge-form" class="stack-form">
              <label class="field">
                <span>Title</span>
                <input id="knowledge-title-input" name="title" placeholder="Async Notes" />
              </label>
              <label class="field">
                <span>Source</span>
                <input id="knowledge-source-input" name="source" placeholder="user://dashboard" value="user://dashboard" />
              </label>
              <label class="field">
                <span>Content</span>
                <textarea id="knowledge-content-input" name="content" placeholder="Paste notes, constraints, or excerpts that should bias the next teaching turn."></textarea>
              </label>
              <button class="action primary" type="submit">Upload Knowledge</button>
            </form>
            <form id="knowledge-search-form" class="stack-form">
              <label class="field">
                <span>Query</span>
                <input id="knowledge-query-input" name="query" placeholder="event loop scheduling" />
              </label>
              <button class="action ghost" type="submit">Search Knowledge</button>
            </form>
            <div id="knowledge-results" class="result-stack">
              <div class="empty">Search knowledge to inspect retrieved chunks.</div>
            </div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Workspace</p>
              <h2>Session Workspace</h2>
            </div>
            <div id="session-files-panel" class="workspace-tree">
              <div class="empty">Select a session to inspect its derived workspace files.</div>
            </div>
          </article>
        </div>

        <div class="column">
          <article class="panel section-card" id="runtime-pulse">
            <div class="section-heading">
              <p class="eyebrow">Ops</p>
              <h2>Runtime Pulse</h2>
            </div>
            <div class="action-row">
              <button id="refresh-runtime" class="action secondary" type="button">Refresh Runtime</button>
              <button id="load-config" class="action ghost" type="button">Load Config</button>
            </div>
            <div class="runtime-grid">
              <div id="runtime-summary-panel" class="info-panel">
                <div class="empty">Runtime summary has not been loaded.</div>
              </div>
              <div id="config-summary-panel" class="info-panel">
                <div class="empty">Provider Routing configuration has not been loaded.</div>
              </div>
            </div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Lesson</p>
              <h2>Teaching Output</h2>
            </div>
            <p id="lesson-text" class="copy-block">No lesson yet.</p>
            <pre id="lesson-quiz" class="codebox" hidden></pre>
            <p id="practice-text" class="copy-block">No practice yet.</p>
            <pre id="practice-rubric" class="codebox" hidden></pre>
            <div id="latest-feedback" class="copy-block emphasis">No feedback yet.</div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Timeline</p>
              <h2>Session Activity</h2>
            </div>
            <div id="timeline" class="timeline">
              <div class="empty">No timeline yet.</div>
            </div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Mastery</p>
              <h2>Progress Snapshot</h2>
            </div>
            <div id="mastery" class="info-panel">
              <div class="empty">No mastery data yet.</div>
            </div>
            <div id="due-review-list" class="result-stack">
              <div class="empty">No due reviews loaded.</div>
            </div>
            <div id="checkpoint-list" class="result-stack">
              <div class="empty">No checkpoints loaded.</div>
            </div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Export</p>
              <h2>Session Export Preview</h2>
            </div>
            <pre id="export-preview" class="codebox">Load export preview to inspect the current session bundle.</pre>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Provider Routing</p>
              <h2>Config Surface</h2>
            </div>
            <p class="microcopy">Load Config reads <code>/api/config</code> and summarizes active model routing for this deployment.</p>
          </article>
        </div>
      </section>
    </main>
  </div>

  <script src="/static/dashboard.js" defer></script>
</body>
</html>
"""
    return HTMLResponse(html)
