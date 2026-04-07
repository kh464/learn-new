<template>
  <article class="panel section-card">
    <div class="section-heading">
      <p class="eyebrow">Workspace</p>
      <h2>Session Workspace</h2>
    </div>
    <div class="workspace-tree">
      <div v-if="!sessionFiles.length" class="empty">Select a session to inspect its derived workspace files.</div>
      <div v-for="item in sessionFiles" :key="item.path" class="workspace-node">
        <strong>{{ item.path }}</strong>
        <div class="microcopy">{{ item.detail }}</div>
      </div>
    </div>
  </article>
</template>

<script setup>
defineOptions({ name: "DashboardWorkspacePanel" });

defineProps({
  sessionFiles: { type: Array, required: true },
});
</script>
