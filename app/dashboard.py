from __future__ import annotations

from fastapi.responses import HTMLResponse


def render_dashboard() -> HTMLResponse:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Learn New Dashboard</title>
  <style>
    :root {
      --bg: #f6f1e8;
      --panel: rgba(255, 250, 241, 0.9);
      --ink: #172033;
      --muted: #68707e;
      --accent: #bc4f2b;
      --accent-soft: #f0cab9;
      --line: #ddd1bf;
      --surface: rgba(255,255,255,0.56);
      --shadow: 0 18px 45px rgba(27, 31, 37, 0.08);
      --mono: "IBM Plex Mono", Consolas, monospace;
      --serif: Georgia, "Times New Roman", serif;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(188, 79, 43, 0.16), transparent 26%),
        linear-gradient(135deg, #f8f0e7 0%, #efe5d8 100%);
      color: var(--ink);
      font-family: var(--serif);
    }

    .shell {
      width: min(1440px, calc(100vw - 28px));
      margin: 14px auto;
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 18px;
    }

    .panel {
      background: var(--panel);
      backdrop-filter: blur(10px);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .sidebar, .content {
      min-height: calc(100vh - 28px);
    }

    .sidebar header, .content header {
      padding: 22px 24px 16px;
      border-bottom: 1px solid rgba(221, 209, 191, 0.7);
    }

    .eyebrow {
      margin: 0;
      color: var(--accent);
      font: 700 11px/1 var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.16em;
    }

    h1, h2, h3, h4, p, pre { margin: 0; }

    h1 { margin-top: 10px; font-size: 30px; line-height: 1; }
    h2 { margin-top: 8px; font-size: 28px; }
    h3 { font-size: 20px; margin-bottom: 10px; }

    .subtle {
      margin-top: 8px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
    }

    .session-list {
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      overflow: auto;
    }

    .create-form {
      padding: 14px;
      border-bottom: 1px solid rgba(221, 209, 191, 0.7);
      display: grid;
      gap: 10px;
    }

    .field {
      display: grid;
      gap: 6px;
    }

    .field label {
      color: var(--muted);
      font: 700 11px/1 var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }

    .field input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(255,255,255,0.74);
      padding: 12px 14px;
      font: 15px/1.3 var(--serif);
      color: var(--ink);
    }

    .session-card {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255,255,255,0.82), rgba(244, 237, 227, 0.92));
      border-radius: 18px;
      padding: 14px;
      cursor: pointer;
      transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
      color: inherit;
    }

    .session-card:hover, .session-card.active {
      transform: translateY(-2px);
      border-color: var(--accent);
      box-shadow: 0 12px 28px rgba(188, 79, 43, 0.14);
    }

    .session-card h3 {
      font-size: 18px;
      margin-bottom: 8px;
    }

    .session-meta, .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 9px;
      background: rgba(188, 79, 43, 0.09);
      color: var(--accent);
      font: 600 11px/1.4 var(--mono);
    }

    .content { display: flex; flex-direction: column; }

    .hero {
      padding: 24px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      border-bottom: 1px solid rgba(221, 209, 191, 0.7);
    }

    .metric, .block {
      background: var(--surface);
      border: 1px solid rgba(221, 209, 191, 0.7);
      border-radius: 22px;
    }

    .metric {
      padding: 16px;
    }

    .metric .label {
      color: var(--muted);
      font: 600 11px/1.3 var(--mono);
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }

    .metric .value {
      margin-top: 10px;
      font-size: 28px;
      font-weight: 700;
    }

    .grid {
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 16px;
      padding: 18px;
    }

    .stack { display: grid; gap: 16px; }
    .block { padding: 18px; }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }

    .turn-form {
      margin-top: 14px;
      display: grid;
      gap: 10px;
    }

    .turn-form textarea {
      width: 100%;
      min-height: 120px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.72);
      padding: 14px;
      font: 14px/1.6 var(--mono);
      color: var(--ink);
    }

    button.action {
      border: 0;
      border-radius: 999px;
      padding: 10px 14px;
      background: var(--accent);
      color: white;
      font: 700 12px/1 var(--mono);
      cursor: pointer;
    }

    button.action.secondary {
      background: rgba(23, 32, 51, 0.82);
    }

    button.action.ghost {
      background: rgba(188, 79, 43, 0.1);
      color: var(--accent);
      border: 1px solid rgba(188, 79, 43, 0.18);
    }

    .status {
      margin-top: 12px;
      padding: 11px 12px;
      border-radius: 14px;
      background: rgba(188, 79, 43, 0.08);
      color: var(--accent);
      font: 600 12px/1.5 var(--mono);
      min-height: 42px;
    }

    .timeline { display: grid; gap: 10px; }
    .timeline-item {
      padding-left: 14px;
      border-left: 2px solid var(--accent-soft);
    }

    .timeline-item time {
      display: block;
      color: var(--muted);
      font: 600 11px/1.4 var(--mono);
      margin-bottom: 4px;
    }

    .codebox {
      margin-top: 12px;
      padding: 14px;
      border-radius: 16px;
      background: #1c2430;
      color: #f2efe8;
      font: 13px/1.6 var(--mono);
      white-space: pre-wrap;
      overflow: auto;
    }

    .checkpoint-list {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }

    .checkpoint-item {
      padding: 12px;
      border-radius: 16px;
      border: 1px solid rgba(221, 209, 191, 0.7);
      background: rgba(255,255,255,0.45);
    }

    .checkpoint-item header {
      padding: 0;
      border: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }

    .empty {
      padding: 28px;
      color: var(--muted);
      text-align: center;
      font-size: 15px;
    }

    @media (max-width: 1040px) {
      .shell { grid-template-columns: 1fr; }
      .sidebar, .content { min-height: auto; }
      .hero { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }

    @media (max-width: 640px) {
      .hero { grid-template-columns: 1fr; }
      .shell { width: min(100vw - 16px, 1440px); margin: 8px auto; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="panel sidebar">
      <header>
        <p class="eyebrow">Learn New</p>
        <h1>Session Index</h1>
        <p class="subtle">Reads <code>/api/sessions</code> and turns the existing APIs into a lightweight control room.</p>
      </header>
      <form id="create-session-form" class="create-form">
        <div class="field">
          <label for="domain-input">Domain</label>
          <input id="domain-input" name="domain" placeholder="Python 异步编程" />
        </div>
        <div class="field">
          <label for="goal-input">Goal</label>
          <input id="goal-input" name="goal" placeholder="掌握 async/await" />
        </div>
        <button class="action" type="submit">Create Session</button>
      </form>
      <div id="session-list" class="session-list">
        <div class="empty">Loading sessions...</div>
      </div>
    </aside>

    <main class="panel content">
      <header>
        <p class="eyebrow">Dashboard</p>
        <h2 id="title">No Session Selected</h2>
        <p id="subtitle" class="subtle">Select a session to load summary, timeline, lesson, practice, review controls, and checkpoints.</p>
        <div class="toolbar">
          <button id="start-review" class="action">Start Review</button>
          <button id="refresh-data" class="action secondary">Refresh</button>
          <button id="export-session" class="action ghost">Open Export JSON</button>
        </div>
        <form id="turn-form" class="turn-form">
          <label class="eyebrow" for="answer-input">Learner Answer</label>
          <textarea id="answer-input" name="answer" placeholder="Submit Turn: paste a learner answer or code snippet here."></textarea>
          <div class="actions">
            <button class="action" type="submit">Submit Turn</button>
          </div>
        </form>
        <div id="action-status" class="status">Ready.</div>
      </header>

      <section id="hero" class="hero"></section>

      <section class="grid">
        <div class="stack">
          <article class="block">
            <h3>Lesson</h3>
            <p id="lesson-text" class="subtle">No lesson yet.</p>
            <div id="lesson-quiz" class="codebox" hidden></div>
          </article>

          <article class="block">
            <h3>Practice</h3>
            <p id="practice-text" class="subtle">No practice yet.</p>
            <div id="practice-rubric" class="codebox" hidden></div>
          </article>

          <article class="block">
            <h3>Checkpoints</h3>
            <p class="subtle">Restore any previously recorded state snapshot.</p>
            <div id="checkpoint-list" class="checkpoint-list">
              <div class="empty">No checkpoints loaded.</div>
            </div>
          </article>
        </div>

        <div class="stack">
          <article class="block">
            <h3>Timeline</h3>
            <div id="timeline" class="timeline">
              <div class="empty">No timeline yet.</div>
            </div>
          </article>

          <article class="block">
            <h3>Mastery Snapshot</h3>
            <div id="mastery" class="subtle">No mastery data yet.</div>
          </article>
        </div>
      </section>
    </main>
  </div>

  <script>
    const state = {
      sessions: [],
      activeSessionId: null,
      activeSession: null,
      activeSummary: null,
      activeTimeline: null,
      activeCheckpoints: [],
    };

    const sessionList = document.getElementById('session-list');
    const createSessionForm = document.getElementById('create-session-form');
    const domainInput = document.getElementById('domain-input');
    const goalInput = document.getElementById('goal-input');
    const hero = document.getElementById('hero');
    const title = document.getElementById('title');
    const subtitle = document.getElementById('subtitle');
    const turnForm = document.getElementById('turn-form');
    const answerInput = document.getElementById('answer-input');
    const lessonText = document.getElementById('lesson-text');
    const lessonQuiz = document.getElementById('lesson-quiz');
    const practiceText = document.getElementById('practice-text');
    const practiceRubric = document.getElementById('practice-rubric');
    const timeline = document.getElementById('timeline');
    const mastery = document.getElementById('mastery');
    const checkpointList = document.getElementById('checkpoint-list');
    const actionStatus = document.getElementById('action-status');
    const startReviewButton = document.getElementById('start-review');
    const refreshButton = document.getElementById('refresh-data');
    const exportButton = document.getElementById('export-session');

    async function fetchJson(path, options) {
      const response = await fetch(path, options);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`${path} -> ${response.status} ${text}`);
      }
      return response.json();
    }

    function setStatus(message) {
      actionStatus.textContent = message;
    }

    function renderMetric(label, value) {
      return `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`;
    }

    function renderSessionList() {
      if (!state.sessions.length) {
        sessionList.innerHTML = '<div class="empty">No sessions found yet. Create one with <code>POST /api/sessions</code>.</div>';
        return;
      }

      sessionList.innerHTML = state.sessions.map((item) => `
        <button class="session-card ${item.session_id === state.activeSessionId ? 'active' : ''}" data-session-id="${item.session_id}">
          <h3>${item.domain}</h3>
          <div class="session-meta">
            <span class="badge">Stage ${item.current_stage}</span>
            <span class="badge">${item.teaching_mode}</span>
            <span class="badge">Score ${item.assessment_score}</span>
          </div>
        </button>
      `).join('');

      for (const button of sessionList.querySelectorAll('[data-session-id]')) {
        button.addEventListener('click', () => loadSession(button.dataset.sessionId));
      }
    }

    function renderSessionDetails() {
      const session = state.activeSession;
      const summary = state.activeSummary;
      const timelineData = state.activeTimeline;

      if (!session || !summary) {
        title.textContent = 'No Session Selected';
        subtitle.textContent = 'Select a session to load summary, timeline, lesson, practice, review controls, and checkpoints.';
        hero.innerHTML = '';
        lessonText.textContent = 'No lesson yet.';
        lessonQuiz.hidden = true;
        practiceText.textContent = 'No practice yet.';
        practiceRubric.hidden = true;
        timeline.innerHTML = '<div class="empty">No timeline yet.</div>';
        mastery.textContent = 'No mastery data yet.';
        checkpointList.innerHTML = '<div class="empty">No checkpoints loaded.</div>';
        return;
      }

      title.textContent = session.domain;
      subtitle.textContent = `Session ${session.session_id} · mode=${session.teaching_mode} · skills=${session.active_skills.length}`;
      hero.innerHTML = [
        renderMetric('Stage', summary.current_stage),
        renderMetric('Mode', summary.teaching_mode),
        renderMetric('Due Reviews', summary.due_review_count),
        renderMetric('Tracked Concepts', summary.mastery_overview.tracked_concepts),
      ].join('');

      lessonText.textContent = session.lesson?.explanation ?? 'No lesson yet.';
      if (session.lesson?.micro_quiz) {
        lessonQuiz.hidden = false;
        lessonQuiz.textContent = JSON.stringify(session.lesson.micro_quiz, null, 2);
      } else {
        lessonQuiz.hidden = true;
        lessonQuiz.textContent = '';
      }

      practiceText.textContent = session.practice?.prompt ?? 'No practice yet.';
      if (session.practice?.rubric) {
        practiceRubric.hidden = false;
        practiceRubric.textContent = JSON.stringify(session.practice.rubric, null, 2);
      } else {
        practiceRubric.hidden = true;
        practiceRubric.textContent = '';
      }

      if (!timelineData?.items?.length) {
        timeline.innerHTML = '<div class="empty">No timeline yet.</div>';
      } else {
        timeline.innerHTML = timelineData.items.map((item) => `
          <div class="timeline-item">
            <time>${item.timestamp}</time>
            <strong>${item.kind}</strong>
            <div>${item.message}</div>
          </div>
        `).join('');
      }

      mastery.innerHTML = `
        <div>average_score: <strong>${summary.mastery_overview.average_score}</strong></div>
        <div>due_review_count: <strong>${summary.mastery_overview.due_review_count}</strong></div>
        <div>strongest: <strong>${summary.mastery_overview.strongest_concept ?? '-'}</strong></div>
        <div>weakest: <strong>${summary.mastery_overview.weakest_concept ?? '-'}</strong></div>
      `;

      renderCheckpoints();
    }

    function renderCheckpoints() {
      if (!state.activeCheckpoints.length) {
        checkpointList.innerHTML = '<div class="empty">No checkpoints loaded.</div>';
        return;
      }

      checkpointList.innerHTML = state.activeCheckpoints.map((item) => `
        <div class="checkpoint-item">
          <header>
            <strong>${item.checkpoint_id}</strong>
            <button class="action ghost restore-button" data-checkpoint-id="${item.checkpoint_id}">Restore Checkpoint</button>
          </header>
          <div class="session-meta">
            <span class="badge">Stage ${item.current_stage}</span>
            <span class="badge">${item.teaching_mode}</span>
            <span class="badge">Score ${item.assessment_score}</span>
          </div>
          <p class="subtle">${item.created_at}</p>
        </div>
      `).join('');

      for (const button of checkpointList.querySelectorAll('.restore-button')) {
        button.addEventListener('click', async () => {
          await restoreCheckpoint(button.dataset.checkpointId);
        });
      }
    }

    async function loadSessions() {
      const payload = await fetchJson('/api/sessions');
      state.sessions = payload.items;
      if (!state.activeSessionId && state.sessions.length) {
        state.activeSessionId = state.sessions[0].session_id;
      }
      renderSessionList();
      if (state.activeSessionId) {
        await loadSession(state.activeSessionId);
      } else {
        renderSessionDetails();
      }
    }

    async function loadSession(sessionId) {
      state.activeSessionId = sessionId;
      renderSessionList();
      setStatus(`Loading ${sessionId}...`);

      const [session, summary, timelineData, checkpoints] = await Promise.all([
        fetchJson(`/api/sessions/${sessionId}`),
        fetchJson(`/api/sessions/${sessionId}/summary`),
        fetchJson(`/api/sessions/${sessionId}/timeline?limit=12`),
        fetchJson(`/api/sessions/${sessionId}/checkpoints`),
      ]);

      state.activeSession = session;
      state.activeSummary = summary;
      state.activeTimeline = timelineData;
      state.activeCheckpoints = checkpoints.items;
      renderSessionDetails();
      setStatus(`Loaded session ${sessionId}.`);
    }

    async function startReview() {
      if (!state.activeSessionId) return;
      setStatus('Starting review...');
      await fetchJson(`/api/sessions/${state.activeSessionId}/reviews`, { method: 'POST' });
      await loadSession(state.activeSessionId);
      setStatus('Review round created.');
    }

    async function submitTurn() {
      if (!state.activeSessionId) {
        setStatus('Select or create a session first.');
        return;
      }
      const learnerAnswer = answerInput.value.trim();
      if (!learnerAnswer) {
        setStatus('Submit Turn requires a learner answer.');
        return;
      }
      setStatus('Submitting turn...');
      await fetchJson(`/api/sessions/${state.activeSessionId}/turns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ learner_answer: learnerAnswer }),
      });
      answerInput.value = '';
      await loadSession(state.activeSessionId);
      setStatus('Turn submitted.');
    }

    async function restoreCheckpoint(checkpointId) {
      if (!state.activeSessionId) return;
      setStatus(`Restoring ${checkpointId}...`);
      await fetchJson(`/api/sessions/${state.activeSessionId}/checkpoints/${checkpointId}/restore`, { method: 'POST' });
      await loadSession(state.activeSessionId);
      setStatus(`Restored checkpoint ${checkpointId}.`);
    }

    function openExport() {
      if (!state.activeSessionId) return;
      window.open(`/api/sessions/${state.activeSessionId}/export`, '_blank');
    }

    startReviewButton.addEventListener('click', () => {
      startReview().catch((error) => setStatus(`Start Review failed: ${error.message}`));
    });

    createSessionForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const domain = domainInput.value.trim();
      const goal = goalInput.value.trim();
      if (!domain || !goal) {
        setStatus('Create Session requires both domain and goal.');
        return;
      }
      setStatus('Creating session...');
      try {
        const created = await fetchJson('/api/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ domain, goal }),
        });
        domainInput.value = '';
        goalInput.value = '';
        await loadSessions();
        await loadSession(created.session_id);
        setStatus(`Created session ${created.session_id}.`);
      } catch (error) {
        setStatus(`Create Session failed: ${error.message}`);
      }
    });

    turnForm.addEventListener('submit', (event) => {
      event.preventDefault();
      submitTurn().catch((error) => setStatus(`Submit Turn failed: ${error.message}`));
    });

    refreshButton.addEventListener('click', () => {
      if (!state.activeSessionId) {
        loadSessions().catch((error) => setStatus(`Refresh failed: ${error.message}`));
        return;
      }
      loadSession(state.activeSessionId).catch((error) => setStatus(`Refresh failed: ${error.message}`));
    });

    exportButton.addEventListener('click', openExport);

    loadSessions().catch((error) => {
      sessionList.innerHTML = `<div class="empty">Dashboard load failed: ${error.message}</div>`;
      setStatus(`Load failed: ${error.message}`);
    });
  </script>
</body>
</html>
"""
    return HTMLResponse(html)
