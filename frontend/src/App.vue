<template>
  <div class="app-shell">
    <SessionSidebar
      :admin-key="adminKey"
      :form="createForm"
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @update:admin-key="setAdminKey"
      @update:form="updateCreateForm"
      @create-session="createSession"
      @select-session="loadSession"
    />

    <main class="main-column">
      <section class="hero panel">
        <div>
          <p class="eyebrow">Mission Control</p>
          <h2>{{ heroTitle }}</h2>
          <p class="lede">{{ heroSubtitle }}</p>
        </div>
        <div class="hero-actions">
          <button class="action secondary" type="button" @click="refreshSession">Refresh Session</button>
          <button class="action secondary" type="button" @click="loadExportPreview">Load Export Preview</button>
          <button class="action ghost" type="button" @click="openExport">Open Export JSON</button>
        </div>
        <div class="status-banner">{{ statusMessage }}</div>
        <div class="hero-metrics">
          <div v-for="metric in heroMetrics" :key="metric.label" class="metric-card">
            <div class="metric-label">{{ metric.label }}</div>
            <div class="metric-value">{{ metric.value }}</div>
          </div>
        </div>
      </section>

      <section class="main-grid">
        <div class="column">
          <TaskConsolePanel
            :turn-answer="turnAnswer"
            :task-answer="taskAnswer"
            :task-events="activeTaskEvents"
            :task-stream-status="taskStreamStatus"
            :dead-letters="deadLetters"
            @update:turn-answer="turnAnswer = $event"
            @update:task-answer="taskAnswer = $event"
            @run-sync-turn="runSyncTurn"
            @start-review="startReview"
            @queue-task="queueTask"
            @poll-task="pollTask"
            @refresh-dead-letters="loadDeadLetters"
            @requeue-task="requeueTask"
          />

          <KnowledgePipelinePanel
            :knowledge-url="knowledgeUrl"
            :knowledge-form="knowledgeForm"
            :search-query="searchQuery"
            :knowledge-results="activeKnowledgeResults"
            @update:knowledge-url="knowledgeUrl = $event"
            @update:knowledge-form="updateKnowledgeForm"
            @update:search-query="searchQuery = $event"
            @import-url="importUrl"
            @upload-knowledge="uploadKnowledge"
            @search-knowledge="searchKnowledge"
          />

          <DashboardWorkspacePanel :session-files="sessionFiles" />
        </div>

        <div class="column">
          <RuntimePulsePanel
            :runtime-summary="runtimeSummary"
            :config-summary="configSummary"
            @refresh-runtime="loadRuntime"
            @load-config="loadConfig"
          />

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Lesson</p>
              <h2>Teaching Output</h2>
            </div>
            <p class="copy-block">{{ activeSession?.lesson?.explanation || "No lesson yet." }}</p>
            <pre v-if="formattedLessonQuiz" class="codebox">{{ formattedLessonQuiz }}</pre>
            <p class="copy-block">{{ activeSession?.practice?.prompt || "No practice yet." }}</p>
            <pre v-if="formattedPracticeRubric" class="codebox">{{ formattedPracticeRubric }}</pre>
            <div class="copy-block emphasis">{{ activeSession?.latest_feedback || "No feedback yet." }}</div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Timeline</p>
              <h2>Session Activity</h2>
            </div>
            <div class="timeline">
              <div v-if="!(activeTimeline?.items?.length)" class="empty">No timeline yet.</div>
              <div v-for="item in activeTimeline?.items || []" :key="item.timestamp + item.kind + item.message" class="timeline-item">
                <time>{{ item.timestamp }}</time>
                <strong>{{ item.kind }}</strong>
                <div>{{ item.message }}</div>
              </div>
            </div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Mastery</p>
              <h2>Progress Snapshot</h2>
            </div>
            <div class="info-panel">
              <div v-if="!activeSummary" class="empty">No mastery data yet.</div>
              <template v-else>
                <div>Average score: <strong>{{ activeSummary.mastery_overview.average_score }}</strong></div>
                <div>Due reviews: <strong>{{ activeSummary.mastery_overview.due_review_count }}</strong></div>
                <div>Strongest concept: <strong>{{ activeSummary.mastery_overview.strongest_concept || "-" }}</strong></div>
                <div>Weakest concept: <strong>{{ activeSummary.mastery_overview.weakest_concept || "-" }}</strong></div>
              </template>
            </div>
            <div class="result-stack">
              <div v-if="!activeDueReviews.length" class="empty">No due reviews loaded.</div>
              <div v-for="item in activeDueReviews" :key="item" class="result-card">
                <strong>{{ item }}</strong>
              </div>
            </div>
            <div class="result-stack">
              <div v-if="!activeCheckpoints.length" class="empty">No checkpoints loaded.</div>
              <div v-for="item in activeCheckpoints" :key="item.checkpoint_id" class="result-card">
                <div class="session-meta">
                  <strong>{{ item.checkpoint_id }}</strong>
                  <button class="action ghost" type="button" @click="restoreCheckpoint(item.checkpoint_id)">Restore Checkpoint</button>
                </div>
                <div class="microcopy">{{ item.created_at }}</div>
              </div>
            </div>
          </article>

          <article class="panel section-card">
            <div class="section-heading">
              <p class="eyebrow">Export</p>
              <h2>Session Export Preview</h2>
            </div>
            <pre class="codebox">{{ formattedExportPreview }}</pre>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import DashboardWorkspacePanel from "./components/DashboardWorkspacePanel.vue";
import KnowledgePipelinePanel from "./components/KnowledgePipelinePanel.vue";
import RuntimePulsePanel from "./components/RuntimePulsePanel.vue";
import SessionSidebar from "./components/SessionSidebar.vue";
import TaskConsolePanel from "./components/TaskConsolePanel.vue";
import { apiPaths, createTaskSocket, requestJson, requestText } from "./lib/api.js";

const adminKey = ref(window.localStorage.getItem("learn-new.admin-key") || "");
const statusMessage = ref("Ready.");
const createForm = reactive({
  domain: "",
  goal: "",
  background: "",
  available_time_hours_per_week: 5,
  preferences: "project, examples",
});
const knowledgeForm = reactive({
  title: "",
  source: "user://dashboard",
  content: "",
});
const sessions = ref([]);
const activeSessionId = ref(null);
const activeSession = ref(null);
const activeSummary = ref(null);
const activeTimeline = ref(null);
const activeCheckpoints = ref([]);
const activeDueReviews = ref([]);
const activeKnowledgeResults = ref([]);
const activeExportPreview = ref(null);
const activeTaskId = ref(null);
const activeTaskEvents = ref([]);
const deadLetters = ref([]);
const runtimeSummary = ref({ error: "Runtime summary has not been loaded." });
const configSummary = ref({ error: "Provider Routing configuration has not been loaded." });
const turnAnswer = ref("");
const taskAnswer = ref("");
const knowledgeUrl = ref("");
const searchQuery = ref("");

let activeSocket = null;

const heroTitle = computed(() => activeSession.value?.domain || "No Session Selected");
const heroSubtitle = computed(() => {
  if (!activeSession.value || !activeSummary.value) {
    return "Select a session to inspect the learning loop, queue work, import knowledge, and observe runtime health.";
  }
  return `Session ${activeSession.value.session_id} | mode=${activeSession.value.teaching_mode} | stage=${activeSummary.value.current_stage} | logs=${activeSession.value.log_count}`;
});
const heroMetrics = computed(() => {
  if (!activeSummary.value) {
    return [];
  }
  return [
    { label: "Stage", value: activeSummary.value.current_stage },
    { label: "Mode", value: activeSummary.value.teaching_mode },
    { label: "Due Reviews", value: activeSummary.value.due_review_count },
    { label: "Tracked Concepts", value: activeSummary.value.mastery_overview.tracked_concepts },
  ];
});
const taskStreamStatus = computed(() => {
  if (!activeTaskId.value) {
    return "No queued task yet.";
  }
  const latest = activeTaskEvents.value[activeTaskEvents.value.length - 1];
  return latest ? `Task ${latest.task_id} is ${latest.status}.` : `Task ${activeTaskId.value} queued.`;
});
const formattedLessonQuiz = computed(() => activeSession.value?.lesson?.micro_quiz ? JSON.stringify(activeSession.value.lesson.micro_quiz, null, 2) : "");
const formattedPracticeRubric = computed(() => activeSession.value?.practice?.rubric ? JSON.stringify(activeSession.value.practice.rubric, null, 2) : "");
const formattedExportPreview = computed(() => activeExportPreview.value ? JSON.stringify(activeExportPreview.value, null, 2) : "Load export preview to inspect the current session bundle.");
const sessionFiles = computed(() => {
  if (!activeSession.value) {
    return [];
  }
  return [
    { path: `.learn/sessions/${activeSession.value.session_id}/progress.json`, detail: `Derived state with current_stage=${activeSummary.value?.current_stage ?? "-"}` },
    { path: `.learn/sessions/${activeSession.value.session_id}/timeline.json`, detail: `Recent timeline items=${activeTimeline.value?.items?.length ?? 0}` },
    { path: `.learn/sessions/${activeSession.value.session_id}/knowledge.json`, detail: `Knowledge results=${activeKnowledgeResults.value.length}` },
    { path: `.learn/sessions/${activeSession.value.session_id}/checkpoints/`, detail: `Checkpoint count=${activeCheckpoints.value.length}` },
    { path: `.learn/sessions/${activeSession.value.session_id}/export.json`, detail: `Export preview ${activeExportPreview.value ? "loaded" : "not loaded"}` },
  ];
});

function setStatus(message) {
  statusMessage.value = message;
}

function setAdminKey(value) {
  adminKey.value = value;
  window.localStorage.setItem("learn-new.admin-key", String(value || "").trim());
}

function updateCreateForm({ key, value }) {
  createForm[key] = value;
}

function updateKnowledgeForm({ key, value }) {
  knowledgeForm[key] = value;
}

async function safeJson(path, options = {}) {
  return requestJson(path, adminKey.value, options);
}

async function loadSessions() {
  const payload = await safeJson(apiPaths.sessions);
  sessions.value = payload.items || [];
  if (!activeSessionId.value && sessions.value.length) {
    activeSessionId.value = sessions.value[0].session_id;
  }
  if (activeSessionId.value) {
    await loadSession(activeSessionId.value);
  }
}

async function loadSession(sessionId) {
  activeSessionId.value = sessionId;
  setStatus(`Loading session ${sessionId}...`);
  const [session, summary, timeline, checkpoints, dueReviews] = await Promise.all([
    safeJson(`/api/sessions/${sessionId}`),
    safeJson(`/api/sessions/${sessionId}/summary`),
    safeJson(`/api/sessions/${sessionId}/timeline?limit=12`),
    safeJson(`/api/sessions/${sessionId}/checkpoints`),
    safeJson(`/api/sessions/${sessionId}/reviews/due`),
  ]);
  activeSession.value = session;
  activeSummary.value = summary;
  activeTimeline.value = timeline;
  activeCheckpoints.value = checkpoints.items || [];
  activeDueReviews.value = dueReviews.items || [];
  activeKnowledgeResults.value = [];
  activeExportPreview.value = null;
  setStatus(`Loaded session ${sessionId}.`);
}

async function refreshSession() {
  if (activeSessionId.value) {
    await loadSession(activeSessionId.value);
  } else {
    await loadSessions();
  }
}

async function createSession() {
  if (!createForm.domain.trim() || !createForm.goal.trim()) {
    setStatus("Create Session requires both domain and goal.");
    return;
  }
  const created = await safeJson(apiPaths.sessions, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      domain: createForm.domain.trim(),
      goal: createForm.goal.trim(),
      background: createForm.background.trim(),
      available_time_hours_per_week: Number(createForm.available_time_hours_per_week || 5),
      preferences: createForm.preferences.split(",").map((item) => item.trim()).filter(Boolean),
    }),
  });
  createForm.domain = "";
  createForm.goal = "";
  createForm.background = "";
  await loadSessions();
  await loadSession(created.session_id);
  setStatus(`Created session ${created.session_id}.`);
}

async function runSyncTurn() {
  if (!activeSessionId.value || !turnAnswer.value.trim()) {
    setStatus("Run Sync Turn requires an active session and learner answer.");
    return;
  }
  await safeJson(`/api/sessions/${activeSessionId.value}/turns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ learner_answer: turnAnswer.value.trim() }),
  });
  turnAnswer.value = "";
  await loadSession(activeSessionId.value);
  setStatus("Sync turn completed.");
}

function closeTaskSocket() {
  if (activeSocket) {
    activeSocket.close();
    activeSocket = null;
  }
}

function connectTaskSocket(taskId) {
  closeTaskSocket();
  activeSocket = createTaskSocket(taskId, adminKey.value, {
    message: (event) => {
      const payload = JSON.parse(event.data);
      activeTaskId.value = payload.task_id;
      activeTaskEvents.value.push(payload);
      if (payload.status === "completed" && payload.result?.session_id) {
        taskAnswer.value = "";
        loadSession(payload.result.session_id).catch((error) => setStatus(`Queued task refresh failed: ${error.message}`));
        loadDeadLetters().catch(() => null);
      }
    },
    error: () => {
      setStatus(`Task ${taskId} websocket stream failed. Use Poll Task Status.`);
    },
  });
}

async function queueTask() {
  if (!activeSessionId.value || !taskAnswer.value.trim()) {
    setStatus("Queue Turn Task requires an active session and learner answer.");
    return;
  }
  const accepted = await safeJson(apiPaths.taskTurns, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: activeSessionId.value, learner_answer: taskAnswer.value.trim() }),
  });
  activeTaskId.value = accepted.task_id;
  activeTaskEvents.value = [{ ...accepted, timestamp: accepted.created_at }];
  connectTaskSocket(accepted.task_id);
  setStatus(`Queued task ${accepted.task_id}.`);
}

async function pollTask() {
  if (!activeTaskId.value) {
    setStatus("No queued task available for polling.");
    return;
  }
  const task = await safeJson(`/api/tasks/${activeTaskId.value}`);
  activeTaskEvents.value.push(task);
  if (task.status === "completed" && task.result?.session_id) {
    await loadSession(task.result.session_id);
  }
  setStatus(`Polled task ${task.task_id}.`);
}

async function loadDeadLetters() {
  try {
    const payload = await safeJson(`${apiPaths.deadLetter}?limit=10`);
    deadLetters.value = payload.items || [];
  } catch (_error) {
    deadLetters.value = [];
  }
}

async function requeueTask(taskId) {
  const accepted = await safeJson(`/api/tasks/${taskId}/requeue`, { method: "POST" });
  activeTaskId.value = accepted.task_id;
  activeTaskEvents.value = [{ ...accepted, timestamp: accepted.created_at }];
  await loadDeadLetters();
  connectTaskSocket(accepted.task_id);
  setStatus(`Requeued task ${accepted.task_id}.`);
}

async function startReview() {
  if (!activeSessionId.value) {
    setStatus("Select or create a session first.");
    return;
  }
  await safeJson(`/api/sessions/${activeSessionId.value}/reviews`, { method: "POST" });
  await loadSession(activeSessionId.value);
  setStatus("Review round created.");
}

async function importUrl() {
  if (!activeSessionId.value || !knowledgeUrl.value.trim()) {
    setStatus("Import URL requires an active session and URL.");
    return;
  }
  const payload = await safeJson(`/api/sessions/${activeSessionId.value}/knowledge/import-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: knowledgeUrl.value.trim() }),
  });
  knowledgeUrl.value = "";
  await loadSession(activeSessionId.value);
  setStatus(`Imported ${payload.chunks_added} chunk(s) from URL.`);
}

async function uploadKnowledge() {
  if (!activeSessionId.value || !knowledgeForm.title.trim() || !knowledgeForm.content.trim()) {
    setStatus("Upload Knowledge requires an active session plus title and content.");
    return;
  }
  await safeJson(`/api/sessions/${activeSessionId.value}/knowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: knowledgeForm.title.trim(),
      source: knowledgeForm.source.trim() || "user://dashboard",
      content: knowledgeForm.content.trim(),
    }),
  });
  knowledgeForm.title = "";
  knowledgeForm.content = "";
  await loadSession(activeSessionId.value);
  setStatus("Knowledge uploaded.");
}

async function searchKnowledge() {
  if (!activeSessionId.value || !searchQuery.value.trim()) {
    setStatus("Search Knowledge requires an active session and query.");
    return;
  }
  const payload = await safeJson(`/api/sessions/${activeSessionId.value}/knowledge/search?query=${encodeURIComponent(searchQuery.value.trim())}`);
  activeKnowledgeResults.value = payload.items || [];
  setStatus(`Knowledge search returned ${activeKnowledgeResults.value.length} result(s).`);
}

async function restoreCheckpoint(checkpointId) {
  await safeJson(`/api/sessions/${activeSessionId.value}/checkpoints/${checkpointId}/restore`, { method: "POST" });
  await loadSession(activeSessionId.value);
  setStatus(`Restored checkpoint ${checkpointId}.`);
}

async function loadExportPreview() {
  activeExportPreview.value = await safeJson(`/api/sessions/${activeSessionId.value}/export`);
  setStatus("Export preview loaded.");
}

async function openExport() {
  const payload = await requestText(`/api/sessions/${activeSessionId.value}/export`, adminKey.value);
  const blob = new Blob([payload], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  setStatus("Opened export JSON.");
}

async function loadRuntime() {
  runtimeSummary.value = await safeJson(apiPaths.runtimeSummary).catch((error) => ({ error: error.message }));
  setStatus("Runtime summary refreshed.");
}

async function loadConfig() {
  configSummary.value = await safeJson("/api/config").catch((error) => ({ error: error.message }));
  setStatus("Config summary refreshed.");
}

onMounted(async () => {
  window.addEventListener("beforeunload", closeTaskSocket);
  try {
    await Promise.all([loadSessions(), loadRuntime(), loadConfig(), loadDeadLetters()]);
  } catch (error) {
    setStatus(`Frontend bootstrap failed: ${error.message}`);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", closeTaskSocket);
  closeTaskSocket();
});
</script>
