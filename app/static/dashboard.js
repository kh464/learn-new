const state = {
  sessions: [],
  activeSessionId: null,
  activeSession: null,
  activeSummary: null,
  activeTimeline: null,
  activeCheckpoints: [],
  activeDueReviews: [],
  activeKnowledgeResults: [],
  activeExportPreview: null,
  activeTaskId: null,
  activeTaskEvents: [],
  deadLetters: [],
  runtimeSummary: null,
  runtimeAudit: null,
  runtimeLogs: null,
  configSummary: null,
};

const sessionList = document.getElementById("session-list");
const createSessionForm = document.getElementById("create-session-form");
const adminKeyInput = document.getElementById("admin-key-input");
const domainInput = document.getElementById("domain-input");
const goalInput = document.getElementById("goal-input");
const backgroundInput = document.getElementById("background-input");
const timeBudgetInput = document.getElementById("time-budget-input");
const preferencesInput = document.getElementById("preferences-input");
const hero = document.getElementById("hero");
const title = document.getElementById("title");
const subtitle = document.getElementById("subtitle");
const actionStatus = document.getElementById("action-status");
const turnForm = document.getElementById("turn-form");
const answerInput = document.getElementById("answer-input");
const taskForm = document.getElementById("task-form");
const taskAnswerInput = document.getElementById("task-answer-input");
const pollTaskStatusButton = document.getElementById("poll-task-status");
const taskStreamStatus = document.getElementById("task-stream-status");
const taskStream = document.getElementById("task-stream");
const refreshDeadLetterButton = document.getElementById("refresh-dead-letter");
const deadLetterList = document.getElementById("dead-letter-list");
const refreshButton = document.getElementById("refresh-data");
const startReviewButton = document.getElementById("start-review");
const loadExportPreviewButton = document.getElementById("load-export-preview");
const exportButton = document.getElementById("export-session");
const lessonText = document.getElementById("lesson-text");
const lessonQuiz = document.getElementById("lesson-quiz");
const practiceText = document.getElementById("practice-text");
const practiceRubric = document.getElementById("practice-rubric");
const latestFeedback = document.getElementById("latest-feedback");
const timeline = document.getElementById("timeline");
const mastery = document.getElementById("mastery");
const dueReviewList = document.getElementById("due-review-list");
const checkpointList = document.getElementById("checkpoint-list");
const knowledgeUrlForm = document.getElementById("knowledge-url-form");
const knowledgeUrlInput = document.getElementById("knowledge-url-input");
const knowledgeForm = document.getElementById("knowledge-form");
const knowledgeTitleInput = document.getElementById("knowledge-title-input");
const knowledgeSourceInput = document.getElementById("knowledge-source-input");
const knowledgeContentInput = document.getElementById("knowledge-content-input");
const knowledgeSearchForm = document.getElementById("knowledge-search-form");
const knowledgeQueryInput = document.getElementById("knowledge-query-input");
const knowledgeResults = document.getElementById("knowledge-results");
const exportPreview = document.getElementById("export-preview");
const runtimeSummaryPanel = document.getElementById("runtime-summary-panel");
const configSummaryPanel = document.getElementById("config-summary-panel");
const sessionFilesPanel = document.getElementById("session-files-panel");
const refreshRuntimeButton = document.getElementById("refresh-runtime");
const loadConfigButton = document.getElementById("load-config");
const adminHeaderName = "X-Admin-Key";

let activeSocket = null;

function getAdminKey() {
  return adminKeyInput.value.trim();
}

function buildHeaders(extraHeaders) {
  const headers = new Headers(extraHeaders || {});
  const adminKey = getAdminKey();
  if (adminKey) {
    headers.set(adminHeaderName, adminKey);
  }
  return headers;
}

async function fetchJson(path, options) {
  const requestOptions = { ...(options || {}) };
  requestOptions.headers = buildHeaders(requestOptions.headers);
  const response = await fetch(path, requestOptions);
  if (!response.ok) {
    throw new Error(await formatResponseError(path, response));
  }
  return response.json();
}

async function fetchText(path, options) {
  const requestOptions = { ...(options || {}) };
  requestOptions.headers = buildHeaders(requestOptions.headers);
  const response = await fetch(path, requestOptions);
  if (!response.ok) {
    throw new Error(await formatResponseError(path, response));
  }
  return response.text();
}

async function tryFetchJson(path) {
  try {
    return await fetchJson(path);
  } catch (error) {
    return { error: error.message };
  }
}

async function formatResponseError(path, response) {
  const body = await response.text();
  return `${path} -> ${response.status} ${body}`.trim();
}

function setStatus(message) {
  actionStatus.textContent = message;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderMetric(label, value) {
  return `
    <div class="metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(value)}</div>
    </div>
  `;
}

function renderSessionList() {
  if (!state.sessions.length) {
    sessionList.innerHTML = '<div class="empty">No sessions found yet. Create one with <code>POST /api/sessions</code>.</div>';
    return;
  }

  sessionList.innerHTML = state.sessions
    .map((item) => {
      const summary = item.summary || {};
      const isActive = item.session_id === state.activeSessionId ? " active" : "";
      return `
        <button class="session-card${isActive}" type="button" data-session-id="${escapeHtml(item.session_id)}">
          <h3>${escapeHtml(item.domain)}</h3>
          <div class="session-meta">
            <span class="badge">Stage ${escapeHtml(item.current_stage)}</span>
            <span class="badge">${escapeHtml(item.teaching_mode)}</span>
            <span class="badge">Score ${escapeHtml(item.assessment_score)}</span>
          </div>
          <p class="microcopy">Tracked concepts: ${escapeHtml(summary.mastery_overview?.tracked_concepts ?? 0)}</p>
        </button>
      `;
    })
    .join("");

  for (const button of sessionList.querySelectorAll("[data-session-id]")) {
    button.addEventListener("click", () => {
      loadSession(button.dataset.sessionId).catch((error) => setStatus(`Load session failed: ${error.message}`));
    });
  }
}

function renderSessionDetails() {
  const session = state.activeSession;
  const summary = state.activeSummary;

  if (!session || !summary) {
    title.textContent = "No Session Selected";
    subtitle.textContent = "Select a session to inspect the learning loop, queue work, import knowledge, and observe runtime health.";
    hero.innerHTML = "";
    lessonText.textContent = "No lesson yet.";
    lessonQuiz.hidden = true;
    practiceText.textContent = "No practice yet.";
    practiceRubric.hidden = true;
    latestFeedback.textContent = "No feedback yet.";
    timeline.innerHTML = '<div class="empty">No timeline yet.</div>';
    mastery.innerHTML = '<div class="empty">No mastery data yet.</div>';
    dueReviewList.innerHTML = '<div class="empty">No due reviews loaded.</div>';
    checkpointList.innerHTML = '<div class="empty">No checkpoints loaded.</div>';
    knowledgeResults.innerHTML = '<div class="empty">Search knowledge to inspect retrieved chunks.</div>';
    exportPreview.textContent = "Load export preview to inspect the current session bundle.";
    renderSessionWorkspace();
    return;
  }

  title.textContent = session.domain;
  subtitle.textContent = `Session ${session.session_id} | mode=${session.teaching_mode} | stage=${summary.current_stage} | logs=${session.log_count}`;
  hero.innerHTML = [
    renderMetric("Stage", summary.current_stage),
    renderMetric("Mode", summary.teaching_mode),
    renderMetric("Due Reviews", summary.due_review_count),
    renderMetric("Tracked Concepts", summary.mastery_overview.tracked_concepts),
  ].join("");

  lessonText.textContent = session.lesson?.explanation || "No lesson yet.";
  if (session.lesson?.micro_quiz) {
    lessonQuiz.hidden = false;
    lessonQuiz.textContent = JSON.stringify(session.lesson.micro_quiz, null, 2);
  } else {
    lessonQuiz.hidden = true;
    lessonQuiz.textContent = "";
  }

  practiceText.textContent = session.practice?.prompt || "No practice yet.";
  if (session.practice?.rubric) {
    practiceRubric.hidden = false;
    practiceRubric.textContent = JSON.stringify(session.practice.rubric, null, 2);
  } else {
    practiceRubric.hidden = true;
    practiceRubric.textContent = "";
  }

  latestFeedback.textContent = session.latest_feedback || "No feedback yet.";
  renderTimeline();
  renderMastery();
  renderDueReviews();
  renderCheckpoints();
  renderKnowledgeResults();
  renderExportPreview();
  renderSessionWorkspace();
}

function renderTimeline() {
  const items = state.activeTimeline?.items || [];
  if (!items.length) {
    timeline.innerHTML = '<div class="empty">No timeline yet.</div>';
    return;
  }
  timeline.innerHTML = items
    .map(
      (item) => `
        <div class="timeline-item">
          <time>${escapeHtml(item.timestamp)}</time>
          <strong>${escapeHtml(item.kind)}</strong>
          <div>${escapeHtml(item.message)}</div>
        </div>
      `
    )
    .join("");
}

function renderMastery() {
  const overview = state.activeSummary?.mastery_overview;
  if (!overview) {
    mastery.innerHTML = '<div class="empty">No mastery data yet.</div>';
    return;
  }
  mastery.innerHTML = `
    <div>Average score: <strong>${escapeHtml(overview.average_score)}</strong></div>
    <div>Due reviews: <strong>${escapeHtml(overview.due_review_count)}</strong></div>
    <div>Strongest concept: <strong>${escapeHtml(overview.strongest_concept || "-")}</strong></div>
    <div>Weakest concept: <strong>${escapeHtml(overview.weakest_concept || "-")}</strong></div>
  `;
}

function renderDueReviews() {
  if (!state.activeDueReviews.length) {
    dueReviewList.innerHTML = '<div class="empty">No due reviews loaded.</div>';
    return;
  }
  dueReviewList.innerHTML = state.activeDueReviews
    .map(
      (item) => `
        <div class="result-card">
          <strong>${escapeHtml(item)}</strong>
        </div>
      `
    )
    .join("");
}

function renderCheckpoints() {
  if (!state.activeCheckpoints.length) {
    checkpointList.innerHTML = '<div class="empty">No checkpoints loaded.</div>';
    return;
  }
  checkpointList.innerHTML = state.activeCheckpoints
    .map(
      (item) => `
        <div class="result-card">
          <div class="session-meta">
            <strong>${escapeHtml(item.checkpoint_id)}</strong>
            <button class="action ghost checkpoint-restore" type="button" data-checkpoint-id="${escapeHtml(item.checkpoint_id)}">Restore Checkpoint</button>
          </div>
          <div class="microcopy">${escapeHtml(item.created_at)}</div>
          <div class="session-meta">
            <span class="badge">Stage ${escapeHtml(item.current_stage)}</span>
            <span class="badge">${escapeHtml(item.teaching_mode)}</span>
            <span class="badge">Score ${escapeHtml(item.assessment_score)}</span>
          </div>
        </div>
      `
    )
    .join("");

  for (const button of checkpointList.querySelectorAll(".checkpoint-restore")) {
    button.addEventListener("click", () => {
      restoreCheckpoint(button.dataset.checkpointId).catch((error) => setStatus(`Restore checkpoint failed: ${error.message}`));
    });
  }
}

function renderKnowledgeResults() {
  if (!state.activeKnowledgeResults.length) {
    knowledgeResults.innerHTML = '<div class="empty">Search knowledge to inspect retrieved chunks.</div>';
    return;
  }
  knowledgeResults.innerHTML = state.activeKnowledgeResults
    .map(
      (item) => `
        <div class="result-card">
          <div class="session-meta">
            <strong>${escapeHtml(item.title)}</strong>
            <span class="badge">score ${escapeHtml(item.score)}</span>
          </div>
          <div class="microcopy">${escapeHtml(item.text)}</div>
          <div class="session-meta">
            <span class="badge">${escapeHtml(item.source)}</span>
          </div>
        </div>
      `
    )
    .join("");
}

function renderExportPreview() {
  if (!state.activeExportPreview) {
    exportPreview.textContent = "Load export preview to inspect the current session bundle.";
    return;
  }
  exportPreview.textContent = JSON.stringify(state.activeExportPreview, null, 2);
}

function renderTaskEvents() {
  if (!state.activeTaskEvents.length) {
    taskStream.innerHTML = '<div class="empty">Queued task events will appear here.</div>';
    return;
  }
  taskStream.innerHTML = state.activeTaskEvents
    .map(
      (item) => `
        <div class="task-event">
          <time>${escapeHtml(item.timestamp || item.completed_at || item.started_at || item.created_at || "pending")}</time>
          <strong>${escapeHtml(item.status)}</strong>
          <div class="microcopy">task_id=${escapeHtml(item.task_id)} | attempts=${escapeHtml(item.attempt_count ?? 0)}/${escapeHtml(item.max_attempts ?? 1)}</div>
          <div>${escapeHtml(item.error || item.result?.latest_feedback || "Task update received.")}</div>
        </div>
      `
    )
    .join("");
}

function renderDeadLetters() {
  if (!state.deadLetters.length) {
    deadLetterList.innerHTML = '<div class="empty">No failed tasks loaded.</div>';
    return;
  }
  deadLetterList.innerHTML = state.deadLetters
    .map(
      (item) => `
        <div class="result-card">
          <div class="session-meta">
            <strong>${escapeHtml(item.task_id)}</strong>
            <button class="action ghost requeue-task" type="button" data-task-id="${escapeHtml(item.task_id)}">Requeue</button>
          </div>
          <div class="microcopy">${escapeHtml(item.status)} | attempts=${escapeHtml(item.attempt_count)}/${escapeHtml(item.max_attempts)}</div>
          <div>${escapeHtml(item.error || "No error detail available.")}</div>
        </div>
      `
    )
    .join("");

  for (const button of deadLetterList.querySelectorAll(".requeue-task")) {
    button.addEventListener("click", () => {
      requeueDeadLetter(button.dataset.taskId).catch((error) => setStatus(`Requeue task failed: ${error.message}`));
    });
  }
}

function renderRuntimeSummary(runtimeSummary, runtimeAudit, runtimeLogs) {
  const summary = runtimeSummary || state.runtimeSummary;
  if (!summary || summary.error) {
    runtimeSummaryPanel.innerHTML = `<div class="empty">${escapeHtml(summary?.error || "Runtime summary has not been loaded.")}</div>`;
    return;
  }

  const checks = Object.entries(summary.checks || {})
    .map(
      ([name, item]) => `
        <div class="result-card">
          <strong>${escapeHtml(name)}</strong>
          <div class="microcopy">${escapeHtml(item.backend)} | ${item.healthy ? "healthy" : "degraded"}</div>
          <div>${escapeHtml(item.detail)}</div>
        </div>
      `
    )
    .join("");

  runtimeSummaryPanel.innerHTML = `
    <div class="result-card">
      <strong>Health</strong>
      <div class="microcopy">healthy=${escapeHtml(summary.healthy)} | sessions=${escapeHtml(summary.sessions?.total ?? 0)}</div>
      <div>Tasks enabled=${escapeHtml(summary.tasks?.enabled)} | audit=${escapeHtml(summary.audit?.enabled)} | app logs=${escapeHtml(summary.app_logs?.enabled)}</div>
    </div>
    <div class="result-card">
      <strong>Audit Feed</strong>
      <div class="microcopy">${escapeHtml(runtimeAudit?.error || `${runtimeAudit?.items?.length || 0} recent audit event(s)` )}</div>
    </div>
    <div class="result-card">
      <strong>App Logs</strong>
      <div class="microcopy">${escapeHtml(runtimeLogs?.error || `${runtimeLogs?.items?.length || 0} recent app log event(s)` )}</div>
    </div>
    ${checks}
  `;
}

function renderConfigSummary(configSummary) {
  const config = configSummary || state.configSummary;
  if (!config || config.error) {
    configSummaryPanel.innerHTML = `<div class="empty">${escapeHtml(config?.error || "Provider Routing configuration has not been loaded.")}</div>`;
    return;
  }

  const providers = Object.entries(config.providers || {})
    .map(
      ([name, provider]) => `
        <div class="result-card">
          <strong>${escapeHtml(name)}</strong>
          <div class="microcopy">${provider.enabled ? "enabled" : "disabled"} | ${escapeHtml(provider.base_url)}</div>
          <div>${escapeHtml(Object.keys(provider.models || {}).join(", ") || "no models")}</div>
        </div>
      `
    )
    .join("");

  const routes = Object.entries(config.routing_profiles || {})
    .map(
      ([name, route]) => `
        <div class="result-card">
          <strong>${escapeHtml(name)}</strong>
          <div class="microcopy">${escapeHtml(route.provider)}</div>
          <div>${escapeHtml(route.model)}</div>
        </div>
      `
    )
    .join("");

  configSummaryPanel.innerHTML = `
    <div class="result-card">
      <strong>Default Route</strong>
      <div class="microcopy">provider=${escapeHtml(config.default_provider)} | profile=${escapeHtml(config.default_profile)}</div>
      <div>timeout=${escapeHtml(config.timeout_seconds)}s | retries=${escapeHtml(config.max_retries)} | available=${escapeHtml(config.llm_available)}</div>
    </div>
    ${providers || '<div class="empty">No providers configured.</div>'}
    ${routes || '<div class="empty">No routing profiles configured.</div>'}
  `;
}

function renderSessionWorkspace() {
  const session = state.activeSession;
  if (!session) {
    sessionFilesPanel.innerHTML = '<div class="empty">Select a session to inspect its derived workspace files.</div>';
    return;
  }

  const workspacePaths = [
    `.learn/sessions/${session.session_id}/progress.json`,
    `.learn/sessions/${session.session_id}/timeline.json`,
    `.learn/sessions/${session.session_id}/knowledge.json`,
    `.learn/sessions/${session.session_id}/checkpoints/`,
    `.learn/sessions/${session.session_id}/export.json`,
  ];

  sessionFilesPanel.innerHTML = workspacePaths
    .map(
      (path) => `
        <div class="workspace-node">
          <strong>${escapeHtml(path)}</strong>
          <div class="microcopy">Derived from session state, checkpoints=${escapeHtml(state.activeCheckpoints.length)}, due_reviews=${escapeHtml(state.activeDueReviews.length)}</div>
        </div>
      `
    )
    .join("");
}

function closeTaskSocket() {
  if (activeSocket) {
    activeSocket.close();
    activeSocket = null;
  }
}

function connectTaskSocket(taskId) {
  closeTaskSocket();
  const base = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/tasks/${taskId}`;
  const adminKey = getAdminKey();
  const url = adminKey ? `${base}?api_key=${encodeURIComponent(adminKey)}` : base;
  activeSocket = new WebSocket(url);
  activeSocket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    state.activeTaskId = payload.task_id;
    state.activeTaskEvents.push(payload);
    taskStreamStatus.textContent = `Task ${payload.task_id} is ${payload.status}.`;
    renderTaskEvents();
    if (payload.status === "completed" && payload.result?.session_id) {
      taskAnswerInput.value = "";
      loadSession(payload.result.session_id).catch((error) => setStatus(`Queued task refresh failed: ${error.message}`));
    }
  });
  activeSocket.addEventListener("close", () => {
    activeSocket = null;
  });
  activeSocket.addEventListener("error", () => {
    taskStreamStatus.textContent = `Task ${taskId} websocket stream failed. Use Poll Task Status.`;
  });
}

async function loadSessions() {
  const payload = await fetchJson("/api/sessions");
  state.sessions = payload.items || [];
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
  setStatus(`Loading session ${sessionId}...`);

  const [session, summary, sessionTimeline, checkpoints, dueReviews] = await Promise.all([
    fetchJson(`/api/sessions/${sessionId}`),
    fetchJson(`/api/sessions/${sessionId}/summary`),
    fetchJson(`/api/sessions/${sessionId}/timeline?limit=12`),
    fetchJson(`/api/sessions/${sessionId}/checkpoints`),
    fetchJson(`/api/sessions/${sessionId}/reviews/due`),
  ]);

  state.activeSession = session;
  state.activeSummary = summary;
  state.activeTimeline = sessionTimeline;
  state.activeCheckpoints = checkpoints.items || [];
  state.activeDueReviews = dueReviews.items || [];
  state.activeKnowledgeResults = [];
  state.activeExportPreview = null;
  renderSessionDetails();
  setStatus(`Loaded session ${sessionId}.`);
}

async function createSession(event) {
  event.preventDefault();
  const domain = domainInput.value.trim();
  const goal = goalInput.value.trim();
  if (!domain || !goal) {
    setStatus("Create Session requires both domain and goal.");
    return;
  }
  setStatus("Creating session...");
  const created = await fetchJson("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      domain,
      goal,
      background: backgroundInput.value.trim(),
      available_time_hours_per_week: Number(timeBudgetInput.value || 5),
      preferences: preferencesInput.value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    }),
  });
  domainInput.value = "";
  goalInput.value = "";
  backgroundInput.value = "";
  await loadSessions();
  await loadSession(created.session_id);
  setStatus(`Created session ${created.session_id}.`);
}

async function runSyncTurn(event) {
  event.preventDefault();
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  const learnerAnswer = answerInput.value.trim();
  if (!learnerAnswer) {
    setStatus("Run Sync Turn requires a learner answer.");
    return;
  }
  setStatus("Submitting sync turn...");
  await fetchJson(`/api/sessions/${state.activeSessionId}/turns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ learner_answer: learnerAnswer }),
  });
  answerInput.value = "";
  await loadSession(state.activeSessionId);
  setStatus("Sync turn completed.");
}

async function queueTurnTask(event) {
  event.preventDefault();
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  const learnerAnswer = taskAnswerInput.value.trim();
  if (!learnerAnswer) {
    setStatus("Queue Turn Task requires a learner answer.");
    return;
  }
  setStatus("Queueing turn task...");
  const accepted = await fetchJson("/api/tasks/turns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: state.activeSessionId,
      learner_answer: learnerAnswer,
    }),
  });
  state.activeTaskId = accepted.task_id;
  state.activeTaskEvents = [{ ...accepted, timestamp: accepted.created_at }];
  taskStreamStatus.textContent = `Task ${accepted.task_id} queued.`;
  renderTaskEvents();
  connectTaskSocket(accepted.task_id);
  setStatus(`Queued task ${accepted.task_id}.`);
}

async function pollTaskStatus() {
  if (!state.activeTaskId) {
    setStatus("No queued task available for polling.");
    return;
  }
  setStatus(`Polling task ${state.activeTaskId}...`);
  const task = await fetchJson(`/api/tasks/${state.activeTaskId}`);
  state.activeTaskEvents.push(task);
  taskStreamStatus.textContent = `Task ${task.task_id} is ${task.status}.`;
  renderTaskEvents();
  if (task.status === "completed" && task.result?.session_id) {
    await loadSession(task.result.session_id);
  }
  setStatus(`Polled task ${task.task_id}.`);
}

async function loadDeadLetters() {
  state.deadLetters = [];
  const payload = await tryFetchJson("/api/tasks/dead-letter?limit=10");
  if (payload.error) {
    deadLetterList.innerHTML = `<div class="empty">${escapeHtml(payload.error)}</div>`;
    return;
  }
  state.deadLetters = payload.items || [];
  renderDeadLetters();
}

async function requeueDeadLetter(taskId) {
  setStatus(`Requeueing failed task ${taskId}...`);
  const accepted = await fetchJson(`/api/tasks/${taskId}/requeue`, { method: "POST" });
  state.activeTaskId = accepted.task_id;
  state.activeTaskEvents = [{ ...accepted, timestamp: accepted.created_at }];
  taskStreamStatus.textContent = `Task ${accepted.task_id} queued from dead letter.`;
  renderTaskEvents();
  await loadDeadLetters();
  connectTaskSocket(accepted.task_id);
  setStatus(`Requeued task ${accepted.task_id}.`);
}

async function startReview() {
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  setStatus("Starting review...");
  await fetchJson(`/api/sessions/${state.activeSessionId}/reviews`, { method: "POST" });
  await loadSession(state.activeSessionId);
  setStatus("Review round created.");
}

async function restoreCheckpoint(checkpointId) {
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  setStatus(`Restoring ${checkpointId}...`);
  await fetchJson(`/api/sessions/${state.activeSessionId}/checkpoints/${checkpointId}/restore`, { method: "POST" });
  await loadSession(state.activeSessionId);
  setStatus(`Restored checkpoint ${checkpointId}.`);
}

async function uploadKnowledge(event) {
  event.preventDefault();
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  const title = knowledgeTitleInput.value.trim();
  const content = knowledgeContentInput.value.trim();
  const source = knowledgeSourceInput.value.trim() || "user://dashboard";
  if (!title || !content) {
    setStatus("Upload Knowledge requires both title and content.");
    return;
  }
  setStatus("Uploading knowledge...");
  await fetchJson(`/api/sessions/${state.activeSessionId}/knowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content, source }),
  });
  knowledgeTitleInput.value = "";
  knowledgeContentInput.value = "";
  knowledgeSourceInput.value = source;
  await loadSession(state.activeSessionId);
  setStatus("Knowledge uploaded.");
}

async function importKnowledgeUrl(event) {
  event.preventDefault();
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  const url = knowledgeUrlInput.value.trim();
  if (!url) {
    setStatus("Import URL requires a URL.");
    return;
  }
  setStatus("Importing URL knowledge...");
  const payload = await fetchJson(`/api/sessions/${state.activeSessionId}/knowledge/import-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  knowledgeUrlInput.value = "";
  await loadSession(state.activeSessionId);
  setStatus(`Imported ${payload.chunks_added} chunk(s) from URL.`);
}

async function searchKnowledge(event) {
  event.preventDefault();
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  const query = knowledgeQueryInput.value.trim();
  if (!query) {
    setStatus("Search Knowledge requires a query.");
    return;
  }
  setStatus("Searching knowledge...");
  const payload = await fetchJson(`/api/sessions/${state.activeSessionId}/knowledge/search?query=${encodeURIComponent(query)}`);
  state.activeKnowledgeResults = payload.items || [];
  renderKnowledgeResults();
  setStatus(`Knowledge search returned ${state.activeKnowledgeResults.length} result(s).`);
}

async function loadExportPreview() {
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  setStatus("Loading export preview...");
  state.activeExportPreview = await fetchJson(`/api/sessions/${state.activeSessionId}/export`);
  renderExportPreview();
  renderSessionWorkspace();
  setStatus("Export preview loaded.");
}

async function openExportJson() {
  if (!state.activeSessionId) {
    setStatus("Select or create a session first.");
    return;
  }
  setStatus("Opening export JSON...");
  const payload = await fetchText(`/api/sessions/${state.activeSessionId}/export`);
  const blob = new Blob([payload], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  setStatus("Opened export JSON.");
}

async function loadRuntime() {
  setStatus("Refreshing runtime summary...");
  const [summary, audit, logs] = await Promise.all([
    tryFetchJson("/api/runtime/summary"),
    tryFetchJson("/api/audit?limit=5"),
    tryFetchJson("/api/logs/app?limit=5"),
  ]);
  state.runtimeSummary = summary;
  state.runtimeAudit = audit;
  state.runtimeLogs = logs;
  renderRuntimeSummary(summary, audit, logs);
  setStatus("Runtime summary refreshed.");
}

async function loadConfigSummary() {
  setStatus("Loading config summary...");
  state.configSummary = await tryFetchJson("/api/config");
  renderConfigSummary(state.configSummary);
  setStatus("Config summary refreshed.");
}

function bootstrapAdminKey() {
  const storedAdminKey = window.localStorage.getItem("learn-new.admin-key") || "";
  adminKeyInput.value = storedAdminKey;
  adminKeyInput.addEventListener("change", () => {
    window.localStorage.setItem("learn-new.admin-key", getAdminKey());
    setStatus("Updated admin key for API requests.");
  });
}

function registerEvents() {
  createSessionForm.addEventListener("submit", (event) => {
    createSession(event).catch((error) => setStatus(`Create Session failed: ${error.message}`));
  });
  turnForm.addEventListener("submit", (event) => {
    runSyncTurn(event).catch((error) => setStatus(`Run Sync Turn failed: ${error.message}`));
  });
  taskForm.addEventListener("submit", (event) => {
    queueTurnTask(event).catch((error) => setStatus(`Queue Turn Task failed: ${error.message}`));
  });
  knowledgeUrlForm.addEventListener("submit", (event) => {
    importKnowledgeUrl(event).catch((error) => setStatus(`Import URL failed: ${error.message}`));
  });
  knowledgeForm.addEventListener("submit", (event) => {
    uploadKnowledge(event).catch((error) => setStatus(`Upload Knowledge failed: ${error.message}`));
  });
  knowledgeSearchForm.addEventListener("submit", (event) => {
    searchKnowledge(event).catch((error) => setStatus(`Search Knowledge failed: ${error.message}`));
  });
  refreshButton.addEventListener("click", () => {
    const promise = state.activeSessionId ? loadSession(state.activeSessionId) : loadSessions();
    promise.catch((error) => setStatus(`Refresh Session failed: ${error.message}`));
  });
  startReviewButton.addEventListener("click", () => {
    startReview().catch((error) => setStatus(`Start Review failed: ${error.message}`));
  });
  loadExportPreviewButton.addEventListener("click", () => {
    loadExportPreview().catch((error) => setStatus(`Load Export Preview failed: ${error.message}`));
  });
  exportButton.addEventListener("click", () => {
    openExportJson().catch((error) => setStatus(`Open Export JSON failed: ${error.message}`));
  });
  refreshRuntimeButton.addEventListener("click", () => {
    loadRuntime().catch((error) => setStatus(`Refresh Runtime failed: ${error.message}`));
  });
  refreshDeadLetterButton.addEventListener("click", () => {
    loadDeadLetters().catch((error) => setStatus(`Refresh Dead Letter Queue failed: ${error.message}`));
  });
  loadConfigButton.addEventListener("click", () => {
    loadConfigSummary().catch((error) => setStatus(`Load Config failed: ${error.message}`));
  });
  pollTaskStatusButton.addEventListener("click", () => {
    pollTaskStatus().catch((error) => setStatus(`Poll Task Status failed: ${error.message}`));
  });
}

async function initDashboard() {
  bootstrapAdminKey();
  registerEvents();
  renderSessionDetails();
  renderTaskEvents();
  renderDeadLetters();
  renderRuntimeSummary({ error: "Runtime summary has not been loaded." });
  renderConfigSummary({ error: "Provider Routing configuration has not been loaded." });
  await Promise.all([loadSessions(), loadRuntime(), loadConfigSummary(), loadDeadLetters()]);
}

window.addEventListener("beforeunload", () => {
  closeTaskSocket();
});

initDashboard().catch((error) => {
  sessionList.innerHTML = `<div class="empty">Dashboard load failed: ${escapeHtml(error.message)}</div>`;
  setStatus(`Dashboard bootstrap failed: ${error.message}`);
});
