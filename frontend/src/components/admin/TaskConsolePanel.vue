<template>
  <div class="column">
    <article class="panel section-card">
      <div class="section-heading">
        <p class="eyebrow">Turn Loop</p>
        <h2>Run Sync Turn</h2>
      </div>
      <form class="stack-form" @submit.prevent="$emit('runSyncTurn')">
        <label class="field">
          <span>Learner Answer</span>
          <textarea :value="turnAnswer" placeholder="Submit Turn: explain the learner's latest answer, code, or reflection." @input="$emit('update:turnAnswer', $event.target.value)"></textarea>
        </label>
        <div class="action-row">
          <button class="action primary" type="submit">Run Sync Turn</button>
          <button class="action ghost" type="button" @click="$emit('startReview')">Start Review</button>
        </div>
      </form>
    </article>

    <article class="panel section-card">
      <div class="section-heading">
        <p class="eyebrow">Queue</p>
        <h2>Async Task Console</h2>
      </div>
      <form class="stack-form" @submit.prevent="$emit('queueTask')">
        <label class="field">
          <span>Queued Learner Answer</span>
          <textarea :value="taskAnswer" placeholder="Queue a turn and stream execution over WebSocket." @input="$emit('update:taskAnswer', $event.target.value)"></textarea>
        </label>
        <div class="action-row">
          <button class="action primary" type="submit">Queue Turn Task</button>
          <button class="action secondary" type="button" @click="$emit('pollTask')">Poll Task Status</button>
        </div>
      </form>
      <div class="status-banner muted">{{ taskStreamStatus }}</div>
      <div class="task-stream">
        <div v-if="!taskEvents.length" class="empty">Queued task events will appear here.</div>
        <div v-for="item in taskEvents" :key="`${item.task_id}-${item.status}-${item.completed_at || item.started_at || item.created_at}`" class="task-event">
          <time>{{ item.timestamp || item.completed_at || item.started_at || item.created_at || "pending" }}</time>
          <strong>TaskConsolePanel</strong>
          <div class="microcopy">task_id={{ item.task_id }} | status={{ item.status }} | attempts={{ item.attempt_count ?? 0 }}/{{ item.max_attempts ?? 1 }}</div>
          <div>{{ item.error || item.result?.latest_feedback || "Task update received." }}</div>
        </div>
      </div>
    </article>

    <article class="panel section-card">
      <div class="section-heading">
        <p class="eyebrow">Recovery</p>
        <h2>Dead Letter Queue</h2>
      </div>
      <div class="action-row">
        <button class="action secondary" type="button" @click="$emit('refreshDeadLetters')">Refresh Dead Letter Queue</button>
      </div>
      <div class="result-stack">
        <div v-if="!deadLetters.length" class="empty">No failed tasks loaded.</div>
        <div v-for="item in deadLetters" :key="item.task_id" class="result-card">
          <div class="session-meta">
            <strong>{{ item.task_id }}</strong>
            <button class="action ghost" type="button" @click="$emit('requeueTask', item.task_id)">Requeue</button>
          </div>
          <div class="microcopy">{{ item.status }} | attempts={{ item.attempt_count }}/{{ item.max_attempts }}</div>
          <div>{{ item.error || "No error detail available." }}</div>
        </div>
      </div>
    </article>
  </div>
</template>

<script setup>
defineOptions({ name: "TaskConsolePanel" });

defineProps({
  turnAnswer: { type: String, required: true },
  taskAnswer: { type: String, required: true },
  taskEvents: { type: Array, required: true },
  taskStreamStatus: { type: String, required: true },
  deadLetters: { type: Array, required: true },
});

defineEmits([
  "update:turnAnswer",
  "update:taskAnswer",
  "runSyncTurn",
  "startReview",
  "queueTask",
  "pollTask",
  "refreshDeadLetters",
  "requeueTask",
]);
</script>
