from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import LearnerState, MasteryRecord


class ProgressMonitorAgent:
    def update_progress(self, state: LearnerState) -> LearnerState:
        if state.curriculum is None:
            return state

        stage_index = max(0, state.current_stage - 1)
        concepts = state.curriculum.stages[stage_index].concepts
        now = datetime.now(UTC)
        state.review_queue = []

        for concept in concepts:
            previous = state.mastery_matrix.get(concept, MasteryRecord())
            reviews = previous.reviews + 1
            interval_days = self._next_interval_days(previous.interval_days, state.assessment_score)
            next_due = now + timedelta(days=interval_days)
            confidence = self._next_confidence(previous.confidence_score, state.assessment_score)
            state.mastery_matrix[concept] = MasteryRecord(
                score=state.assessment_score,
                reviews=reviews,
                interval_days=interval_days,
                next_due=next_due,
                confidence_score=confidence,
            )

        if state.assessment_score < 60:
            state.consecutive_low_scores += 1
            state.review_queue = concepts[:]
        else:
            state.consecutive_low_scores = 0
            state.needs_intervention = False
            state.teaching_mode = "standard"

        if state.consecutive_low_scores >= 2:
            state.needs_intervention = True
            state.teaching_mode = "remedial"
            state.add_log(
                "intervention",
                "Two consecutive low scores detected. Switch to remedial teaching with simpler examples and review tasks.",
            )

        if state.assessment_score >= 85 and state.current_stage < len(state.curriculum.stages):
            state.current_stage += 1
            state.needs_intervention = False
            state.teaching_mode = "standard"
            state.add_log("stage_advanced", f"Advanced to stage {state.current_stage}.")
        elif state.assessment_score < 60:
            if not state.needs_intervention:
                state.add_log("stage_repeat", "Low score detected. Repeat current stage and schedule near-term review.")
        else:
            state.add_log("stage_repeat", f"Remain on stage {state.current_stage} for reinforcement.")

        return state

    def collect_due_concepts(self, state: LearnerState, now: datetime | None = None) -> list[str]:
        now = now or datetime.now(UTC)
        return [
            concept
            for concept, record in state.mastery_matrix.items()
            if record.next_due <= now
        ]

    def _next_interval_days(self, previous_interval: int, score: float) -> int:
        if score >= 90:
            return max(previous_interval * 2, 3)
        if score >= 75:
            return max(previous_interval + 1, 2)
        if score >= 60:
            return 1
        return 1

    def _next_confidence(self, previous_confidence: float, score: float) -> float:
        current_confidence = max(0.0, min(1.0, score / 100))
        if previous_confidence == 0:
            return current_confidence
        return round((previous_confidence * 0.4) + (current_confidence * 0.6), 4)
