<template>
  <aside class="sidebar">
    <div class="brand-card panel">
      <p class="eyebrow">Learn New</p>
      <h1>Learner Workspace</h1>
      <p class="lede">A simplified workspace for creating sessions, answering prompts, and following the lesson-feedback loop.</p>
    </div>

    <section class="panel section-card">
      <div class="section-heading">
        <p class="eyebrow">Access</p>
        <h2>Access Key</h2>
      </div>
      <label class="field">
        <span>Optional Token</span>
        <input :value="accessKey" placeholder="Only needed when backend security is enabled" @input="$emit('update:accessKey', $event.target.value)" />
      </label>
      <p class="microcopy">This entry avoids operational controls. The access field is only here so the learner UI can still work when the backend is protected.</p>
    </section>

    <section class="panel section-card">
      <div class="section-heading">
        <p class="eyebrow">Create</p>
        <h2>Session Workspace</h2>
      </div>
      <form class="stack-form" @submit.prevent="$emit('createSession')">
        <label class="field">
          <span>Domain</span>
          <input :value="form.domain" placeholder="Python async programming" @input="$emit('update:form', { key: 'domain', value: $event.target.value })" />
        </label>
        <label class="field">
          <span>Goal</span>
          <input :value="form.goal" placeholder="Master async/await" @input="$emit('update:form', { key: 'goal', value: $event.target.value })" />
        </label>
        <label class="field">
          <span>Background</span>
          <textarea :value="form.background" placeholder="Current experience, blockers, and context." @input="$emit('update:form', { key: 'background', value: $event.target.value })"></textarea>
        </label>
        <label class="field">
          <span>Hours / Week</span>
          <input :value="form.available_time_hours_per_week" type="number" min="1" @input="$emit('update:form', { key: 'available_time_hours_per_week', value: Number($event.target.value || 5) })" />
        </label>
        <label class="field">
          <span>Preferences</span>
          <input :value="form.preferences" placeholder="project, examples, coaching" @input="$emit('update:form', { key: 'preferences', value: $event.target.value })" />
        </label>
        <button class="action primary" type="submit">Create Session</button>
      </form>
    </section>

    <section class="panel section-card">
      <div class="section-heading">
        <p class="eyebrow">Sessions</p>
        <h2>My Learning Sessions</h2>
      </div>
      <div class="session-list">
        <div v-if="!sessions.length" class="empty">No sessions found yet.</div>
        <button
          v-for="item in sessions"
          :key="item.session_id"
          class="session-card"
          :class="{ active: item.session_id === activeSessionId }"
          type="button"
          @click="$emit('selectSession', item.session_id)"
        >
          <h3>{{ item.domain }}</h3>
          <div class="session-meta">
            <span class="badge">Stage {{ item.current_stage }}</span>
            <span class="badge">{{ item.teaching_mode }}</span>
          </div>
          <p class="microcopy">Current score {{ item.assessment_score }}</p>
        </button>
      </div>
    </section>
  </aside>
</template>

<script setup>
defineOptions({ name: "UserSessionSidebar" });

defineProps({
  accessKey: { type: String, required: true },
  form: { type: Object, required: true },
  sessions: { type: Array, required: true },
  activeSessionId: { type: String, default: null },
});

defineEmits(["update:accessKey", "update:form", "createSession", "selectSession"]);
</script>
