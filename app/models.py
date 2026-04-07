from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class LearnerProfile(BaseModel):
    goal: str
    background: str = ""
    available_time_hours_per_week: int = 5
    preferences: list[str] = Field(default_factory=lambda: ["project", "examples"])


class LogEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    kind: str
    message: str


class KnowledgeItem(BaseModel):
    title: str
    summary: str
    source: str
    confidence: float = 0.8


class KnowledgeChunk(BaseModel):
    chunk_id: str
    title: str
    content: str
    source: str
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0


class DomainMeta(BaseModel):
    type: str
    pedagogy: str
    core_primitives: list[str]
    assessment_style: str
    difficulty_curve: str


class CurriculumStage(BaseModel):
    stage: int
    title: str
    objective: str
    concepts: list[str]
    practice_format: str
    exit_criteria: str


class Curriculum(BaseModel):
    domain: str
    stages: list[CurriculumStage]


class LessonArtifact(BaseModel):
    explanation: str
    key_takeaways: list[str]
    micro_quiz: dict[str, Any]
    next_step: str


class PracticeArtifact(BaseModel):
    title: str
    prompt: str
    expected_answer: str
    rubric: list[str]
    reference_code: str = ""
    evaluation_mode: str = "freeform"
    test_code: str = ""


class SandboxResult(BaseModel):
    passed: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


class MasteryRecord(BaseModel):
    score: float = 0.0
    reviews: int = 0
    interval_days: int = 1
    next_due: datetime = Field(default_factory=utc_now)
    confidence_score: float = 0.0


class LearnerState(BaseModel):
    session_id: str
    domain: str
    learner_profile: LearnerProfile
    owner_id: str = ""
    current_stage: int = 1
    curriculum_version: int = 1
    active_skills: list[str] = Field(default_factory=list)
    logs: list[LogEvent] = Field(default_factory=list)
    mastery_matrix: dict[str, MasteryRecord] = Field(default_factory=dict)
    domain_meta: DomainMeta | None = None
    curriculum: Curriculum | None = None
    knowledge_items: list[KnowledgeItem] = Field(default_factory=list)
    lesson: LessonArtifact | None = None
    practice: PracticeArtifact | None = None
    assessment_score: float = 0.0
    latest_answer: str = ""
    latest_feedback: str = ""
    consecutive_low_scores: int = 0
    needs_intervention: bool = False
    teaching_mode: str = "standard"
    review_queue: list[str] = Field(default_factory=list)

    @classmethod
    def new(cls, domain: str, profile: LearnerProfile, owner_id: str = "") -> "LearnerState":
        return cls(
            session_id=uuid4().hex,
            domain=domain,
            owner_id=owner_id,
            learner_profile=profile,
            logs=[
                LogEvent(
                    kind="session_created",
                    message=f"Session created for domain {domain}.",
                )
            ],
        )

    def add_log(self, kind: str, message: str) -> None:
        self.logs.append(LogEvent(kind=kind, message=message))
