<template>
  <article class="panel section-card">
    <div class="section-heading">
      <p class="eyebrow">Ops</p>
      <h2>RuntimePulsePanel</h2>
    </div>
    <div class="action-row">
      <button class="action secondary" type="button" @click="$emit('refreshRuntime')">Refresh Runtime</button>
      <button class="action ghost" type="button" @click="$emit('loadConfig')">Load Config</button>
    </div>
    <div class="runtime-grid">
      <div class="info-panel">
        <div v-if="!runtimeSummary || runtimeSummary.error" class="empty">{{ runtimeSummary?.error || "Runtime summary has not been loaded." }}</div>
        <template v-else>
          <div class="result-card">
            <strong>Health</strong>
            <div class="microcopy">healthy={{ runtimeSummary.healthy }} | sessions={{ runtimeSummary.sessions?.total ?? 0 }}</div>
            <div>Tasks enabled={{ runtimeSummary.tasks?.enabled }} | audit={{ runtimeSummary.audit?.enabled }} | app logs={{ runtimeSummary.app_logs?.enabled }}</div>
          </div>
          <div v-for="(item, name) in runtimeSummary.checks || {}" :key="name" class="result-card">
            <strong>{{ name }}</strong>
            <div class="microcopy">{{ item.backend }} | {{ item.healthy ? "healthy" : "degraded" }}</div>
            <div>{{ item.detail }}</div>
          </div>
        </template>
      </div>
      <div class="info-panel">
        <div v-if="!configSummary || configSummary.error" class="empty">{{ configSummary?.error || "Provider Routing configuration has not been loaded." }}</div>
        <template v-else>
          <div class="result-card">
            <strong>Default Route</strong>
            <div class="microcopy">provider={{ configSummary.default_provider }} | profile={{ configSummary.default_profile }}</div>
            <div>timeout={{ configSummary.timeout_seconds }}s | retries={{ configSummary.max_retries }} | available={{ configSummary.llm_available }}</div>
          </div>
          <div v-for="(provider, name) in configSummary.providers || {}" :key="name" class="result-card">
            <strong>{{ name }}</strong>
            <div class="microcopy">{{ provider.enabled ? "enabled" : "disabled" }} | {{ provider.base_url }}</div>
            <div>{{ Object.keys(provider.models || {}).join(", ") || "no models" }}</div>
          </div>
        </template>
      </div>
    </div>
  </article>
</template>

<script setup>
defineOptions({ name: "RuntimePulsePanel" });

defineProps({
  runtimeSummary: { type: Object, default: null },
  configSummary: { type: Object, default: null },
});

defineEmits(["refreshRuntime", "loadConfig"]);
</script>
