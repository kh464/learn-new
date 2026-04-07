<template>
  <div class="app-shell">
    <UserSessionSidebar
      :access-key="accessKey"
      :form="createForm"
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @update:access-key="setAccessKey"
      @update:form="updateCreateForm"
      @create-session="createSession"
      @select-session="loadSession"
    />

    <main class="main-column">
      <section class="hero panel">
        <div>
          <p class="eyebrow">Learner Workspace</p>
          <h2>{{ heroTitle }}</h2>
          <p class="lede">{{ heroSubtitle }}</p>
        </div>
        <div class="hero-actions">
          <button class="action secondary" type="button" @click="refreshSession">Refresh Session</button>
          <button class="action ghost" type="button" @click="startReview">Start Review</button>
        </div>
        <div class="status-banner">{{ statusMessage }}</div>
        <div class="hero-metrics">
          <div v-for="metric in heroMetrics" :key="metric.label" class="metric-card">
            <div class="metric-label">{{ metric.label }}</div>
            <div class="metric-value">{{ metric.value }}</div>
          </div>
        </div>
      </section>

      <LearningWorkspacePanel
        :turn-answer="turnAnswer"
        :active-session="activeSession"
        :active-summary="activeSummary"
        :active-timeline="activeTimeline"
        :active-due-reviews="activeDueReviews"
        @update:turn-answer="turnAnswer = $event"
        @run-sync-turn="runSyncTurn"
      />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import LearningWorkspacePanel from "../../components/user/LearningWorkspacePanel.vue";
import UserSessionSidebar from "../../components/user/UserSessionSidebar.vue";
import { apiPaths, requestJson } from "../../lib/api.js";

const accessKey = ref(window.localStorage.getItem("learn-new.access-key") || "");
const statusMessage = ref("Ready.");
const createForm = reactive({
  domain: "",
  goal: "",
  background: "",
  available_time_hours_per_week: 5,
  preferences: "project, examples",
});
const sessions = ref([]);
const activeSessionId = ref(null);
const activeSession = ref(null);
const activeSummary = ref(null);
const activeTimeline = ref(null);
const activeDueReviews = ref([]);
const turnAnswer = ref("");

const heroTitle = computed(() => activeSession.value?.domain || "Start A Learning Session");
const heroSubtitle = computed(() => {
  if (!activeSession.value || !activeSummary.value) {
    return "Create or pick a session, answer prompts, and follow the teaching feedback loop without any operational controls.";
  }
  return `Mode=${activeSession.value.teaching_mode} | Stage=${activeSummary.value.current_stage} | Due reviews=${activeSummary.value.due_review_count}`;
});
const heroMetrics = computed(() => {
  if (!activeSummary.value) {
    return [];
  }
  return [
    { label: "Stage", value: activeSummary.value.current_stage },
    { label: "Mode", value: activeSession.value?.teaching_mode || "-" },
    { label: "Due Reviews", value: activeSummary.value.due_review_count },
    { label: "Tracked Concepts", value: activeSummary.value.mastery_overview.tracked_concepts },
  ];
});

function setStatus(message) {
  statusMessage.value = message;
}

function setAccessKey(value) {
  accessKey.value = value;
  window.localStorage.setItem("learn-new.access-key", String(value || "").trim());
}

function updateCreateForm({ key, value }) {
  createForm[key] = value;
}

async function safeJson(path, options = {}) {
  return requestJson(path, accessKey.value, options);
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
  const [session, summary, timeline, dueReviews] = await Promise.all([
    safeJson(`/api/sessions/${sessionId}`),
    safeJson(`/api/sessions/${sessionId}/summary`),
    safeJson(`/api/sessions/${sessionId}/timeline?limit=12`),
    safeJson(`/api/sessions/${sessionId}/reviews/due`),
  ]);
  activeSession.value = session;
  activeSummary.value = summary;
  activeTimeline.value = timeline;
  activeDueReviews.value = dueReviews.items || [];
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

async function startReview() {
  if (!activeSessionId.value) {
    setStatus("Select or create a session first.");
    return;
  }
  await safeJson(`/api/sessions/${activeSessionId.value}/reviews`, { method: "POST" });
  await loadSession(activeSessionId.value);
  setStatus("Review round created.");
}

onMounted(async () => {
  try {
    await loadSessions();
  } catch (error) {
    setStatus(`Learner bootstrap failed: ${error.message}`);
  }
});
</script>
