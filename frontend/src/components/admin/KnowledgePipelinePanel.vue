<template>
  <article class="panel section-card" id="knowledge-pipeline">
    <div class="section-heading">
      <p class="eyebrow">Knowledge</p>
      <h2>Knowledge Pipeline</h2>
    </div>
    <form class="stack-form" @submit.prevent="$emit('importUrl')">
      <label class="field">
        <span>Knowledge URL</span>
        <input :value="knowledgeUrl" placeholder="https://example.com/reference" @input="$emit('update:knowledgeUrl', $event.target.value)" />
      </label>
      <button class="action secondary" type="submit">Import URL</button>
    </form>
    <form class="stack-form" @submit.prevent="$emit('uploadKnowledge')">
      <label class="field">
        <span>Title</span>
        <input :value="knowledgeForm.title" placeholder="Async Notes" @input="$emit('update:knowledgeForm', { key: 'title', value: $event.target.value })" />
      </label>
      <label class="field">
        <span>Source</span>
        <input :value="knowledgeForm.source" placeholder="user://dashboard" @input="$emit('update:knowledgeForm', { key: 'source', value: $event.target.value })" />
      </label>
      <label class="field">
        <span>Content</span>
        <textarea :value="knowledgeForm.content" placeholder="Paste notes, constraints, or excerpts that should bias the next teaching turn." @input="$emit('update:knowledgeForm', { key: 'content', value: $event.target.value })"></textarea>
      </label>
      <button class="action primary" type="submit">Upload Knowledge</button>
    </form>
    <form class="stack-form" @submit.prevent="$emit('searchKnowledge')">
      <label class="field">
        <span>Query</span>
        <input :value="searchQuery" placeholder="event loop scheduling" @input="$emit('update:searchQuery', $event.target.value)" />
      </label>
      <button class="action ghost" type="submit">Search Knowledge</button>
    </form>
    <div class="result-stack">
      <div v-if="!knowledgeResults.length" class="empty">Search knowledge to inspect retrieved chunks.</div>
      <div v-for="item in knowledgeResults" :key="item.chunk_id || item.title + item.source" class="result-card">
        <div class="session-meta">
          <strong>{{ item.title }}</strong>
          <span class="badge">score {{ item.score }}</span>
        </div>
        <div class="microcopy">{{ item.text }}</div>
        <div class="session-meta">
          <span class="badge">{{ item.source }}</span>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
defineOptions({ name: "KnowledgePipelinePanel" });

defineProps({
  knowledgeUrl: { type: String, required: true },
  knowledgeForm: { type: Object, required: true },
  searchQuery: { type: String, required: true },
  knowledgeResults: { type: Array, required: true },
});

defineEmits([
  "update:knowledgeUrl",
  "update:knowledgeForm",
  "update:searchQuery",
  "importUrl",
  "uploadKnowledge",
  "searchKnowledge",
]);
</script>
