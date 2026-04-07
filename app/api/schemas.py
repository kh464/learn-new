from __future__ import annotations

from pydantic import BaseModel, Field

from app.models import KnowledgeChunk, LearnerProfile, LearnerState


class CreateSessionRequest(BaseModel):
    domain: str
    goal: str
    background: str = ""
    available_time_hours_per_week: int = 5
    preferences: list[str] = Field(default_factory=lambda: ["project", "examples"])

    def to_profile(self) -> LearnerProfile:
        return LearnerProfile(
            goal=self.goal,
            background=self.background,
            available_time_hours_per_week=self.available_time_hours_per_week,
            preferences=self.preferences,
        )


class TurnRequest(BaseModel):
    learner_answer: str


class UploadKnowledgeRequest(BaseModel):
    title: str
    content: str
    source: str = "user://upload"


class UploadKnowledgeResponse(BaseModel):
    session_id: str
    chunks_added: int


class SearchKnowledgeResponse(BaseModel):
    items: list[KnowledgeChunk]


class DueReviewResponse(BaseModel):
    items: list[str]


class TimelineItemResponse(BaseModel):
    timestamp: str
    kind: str
    message: str


class TimelineResponse(BaseModel):
    items: list[TimelineItemResponse]


class MasteryOverviewResponse(BaseModel):
    tracked_concepts: int
    average_score: float
    due_review_count: int
    strongest_concept: str | None = None
    weakest_concept: str | None = None


class SessionSummaryResponse(BaseModel):
    session_id: str
    domain: str
    current_stage: int
    teaching_mode: str
    assessment_score: float
    log_count: int
    due_review_count: int
    active_skills: list[str]
    mastery_overview: MasteryOverviewResponse


class CheckpointItemResponse(BaseModel):
    checkpoint_id: str
    created_at: str
    current_stage: int
    teaching_mode: str
    assessment_score: float


class CheckpointListResponse(BaseModel):
    items: list[CheckpointItemResponse]


class SessionIndexItemResponse(BaseModel):
    session_id: str
    domain: str
    current_stage: int
    teaching_mode: str
    assessment_score: float
    summary: SessionSummaryResponse


class SessionIndexResponse(BaseModel):
    total: int
    items: list[SessionIndexItemResponse]


class StateResponse(BaseModel):
    session_id: str
    domain: str
    current_stage: int
    assessment_score: float
    teaching_mode: str
    lesson: dict | None = None
    practice: dict | None = None
    latest_feedback: str
    active_skills: list[str]
    log_count: int

    @classmethod
    def from_state(cls, state: LearnerState) -> "StateResponse":
        return cls(
            session_id=state.session_id,
            domain=state.domain,
            current_stage=state.current_stage,
            assessment_score=state.assessment_score,
            teaching_mode=state.teaching_mode,
            lesson=state.lesson.model_dump() if state.lesson else None,
            practice=state.practice.model_dump() if state.practice else None,
            latest_feedback=state.latest_feedback,
            active_skills=state.active_skills,
            log_count=len(state.logs),
        )
