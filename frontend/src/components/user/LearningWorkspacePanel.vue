<template>
  <section class="main-grid learner-grid">
    <div class="column">
      <article class="panel section-card">
        <div class="section-heading">
          <p class="eyebrow">Answer</p>
          <h2>Submit Learner Answer</h2>
        </div>
        <form class="stack-form" @submit.prevent="$emit('runSyncTurn')">
          <label class="field">
            <span>Learner Answer</span>
            <textarea :value="turnAnswer" placeholder="Explain what you understood, where you got stuck, or how you would solve the task." @input="$emit('update:turnAnswer', $event.target.value)"></textarea>
          </label>
          <button class="action primary" type="submit">Run Sync Turn</button>
        </form>
      </article>

      <article class="panel section-card">
        <div class="section-heading">
          <p class="eyebrow">Lesson</p>
          <h2>Teaching Output</h2>
        </div>
        <p class="copy-block">{{ activeSession?.lesson?.explanation || "No lesson yet." }}</p>
        <pre v-if="formattedLessonQuiz" class="codebox">{{ formattedLessonQuiz }}</pre>
        <p class="copy-block">{{ activeSession?.practice?.prompt || "No practice yet." }}</p>
        <pre v-if="formattedPracticeRubric" class="codebox">{{ formattedPracticeRubric }}</pre>
        <div class="copy-block emphasis">{{ activeSession?.latest_feedback || "No latest_feedback yet." }}</div>
      </article>
    </div>

    <div class="column">
      <article class="panel section-card">
        <div class="section-heading">
          <p class="eyebrow">Progress</p>
          <h2>Mastery Snapshot</h2>
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
      </article>

      <article class="panel section-card">
        <div class="section-heading">
          <p class="eyebrow">Timeline</p>
          <h2>Learning Activity</h2>
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
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

defineOptions({ name: "LearningWorkspacePanel" });

const props = defineProps({
  turnAnswer: { type: String, required: true },
  activeSession: { type: Object, default: null },
  activeSummary: { type: Object, default: null },
  activeTimeline: { type: Object, default: null },
  activeDueReviews: { type: Array, required: true },
});

defineEmits(["update:turnAnswer", "runSyncTurn"]);

const formattedLessonQuiz = computed(() => props.activeSession?.lesson?.micro_quiz ? JSON.stringify(props.activeSession.lesson.micro_quiz, null, 2) : "");
const formattedPracticeRubric = computed(() => props.activeSession?.practice?.rubric ? JSON.stringify(props.activeSession.practice.rubric, null, 2) : "");
</script>
