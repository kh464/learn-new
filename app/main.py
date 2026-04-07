from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.dashboard import render_dashboard
from app.api.schemas import (
    CheckpointListResponse,
    CreateSessionRequest,
    DueReviewResponse,
    SessionIndexResponse,
    SessionSummaryResponse,
    SearchKnowledgeResponse,
    StateResponse,
    TimelineResponse,
    TurnRequest,
    UploadKnowledgeRequest,
    UploadKnowledgeResponse,
)
from app.config import AppConfig, load_config
from app.knowledge import KnowledgeService
from app.orchestrator import LearningOrchestrator


def create_app(
    workspace_root: Path | str = Path(".learn"),
    config_path: Path | str = Path("config/llm.yaml"),
) -> FastAPI:
    app = FastAPI(title="Learn New MVP", version="0.1.0")
    config = load_config(config_path)
    orchestrator = LearningOrchestrator(workspace_root=Path(workspace_root), config=config)

    app.state.orchestrator = orchestrator
    app.state.config = config

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/dashboard")
    def dashboard() -> HTMLResponse:
        return render_dashboard()

    @app.get("/api/config")
    def get_config() -> dict[str, str | int | bool | None]:
        cfg: AppConfig = app.state.config
        return {
            "default_provider": cfg.llm.default_provider,
            "default_profile": cfg.llm.default_profile,
            "timeout_seconds": cfg.llm.timeout_seconds,
            "llm_available": orchestrator.llm.is_available(cfg.llm.default_profile) if orchestrator.llm else False,
        }

    @app.post("/api/sessions", response_model=StateResponse, status_code=201)
    def create_session(payload: CreateSessionRequest) -> StateResponse:
        state = app.state.orchestrator.create_session(
            domain=payload.domain,
            profile=payload.to_profile(),
        )
        return StateResponse.from_state(state)

    @app.get("/api/sessions", response_model=SessionIndexResponse)
    def list_sessions() -> SessionIndexResponse:
        payload = app.state.orchestrator.list_sessions()
        return SessionIndexResponse.model_validate(payload)

    @app.post("/api/sessions/{session_id}/knowledge", response_model=UploadKnowledgeResponse, status_code=201)
    def upload_knowledge(session_id: str, payload: UploadKnowledgeRequest) -> UploadKnowledgeResponse:
        try:
            app.state.orchestrator.get_state(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        service = KnowledgeService(app.state.orchestrator.workspace)
        chunks = service.ingest_text(
            session_id=session_id,
            title=payload.title,
            content=payload.content,
            source=payload.source,
        )
        return UploadKnowledgeResponse(session_id=session_id, chunks_added=len(chunks))

    @app.get("/api/sessions/{session_id}/knowledge/search", response_model=SearchKnowledgeResponse)
    def search_knowledge(session_id: str, query: str, limit: int = 3) -> SearchKnowledgeResponse:
        try:
            app.state.orchestrator.get_state(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        service = KnowledgeService(app.state.orchestrator.workspace)
        items = service.retrieve(session_id=session_id, query=query, limit=limit)
        return SearchKnowledgeResponse(items=items)

    @app.get("/api/sessions/{session_id}", response_model=StateResponse)
    def get_session(session_id: str) -> StateResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return StateResponse.from_state(state)

    @app.post("/api/sessions/{session_id}/turns", response_model=StateResponse)
    def run_turn(session_id: str, payload: TurnRequest) -> StateResponse:
        try:
            state = app.state.orchestrator.run_turn(
                session_id=session_id,
                learner_answer=payload.learner_answer,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return StateResponse.from_state(state)

    @app.get("/api/sessions/{session_id}/reviews/due", response_model=DueReviewResponse)
    def get_due_reviews(session_id: str) -> DueReviewResponse:
        try:
            items = app.state.orchestrator.get_due_reviews(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return DueReviewResponse(items=items)

    @app.post("/api/sessions/{session_id}/reviews", response_model=StateResponse)
    def start_review(session_id: str) -> StateResponse:
        try:
            state = app.state.orchestrator.start_review(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return StateResponse.from_state(state)

    @app.get("/api/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
    def get_session_summary(session_id: str) -> SessionSummaryResponse:
        try:
            summary = app.state.orchestrator.get_session_summary(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return SessionSummaryResponse.model_validate(summary)

    @app.get("/api/sessions/{session_id}/timeline", response_model=TimelineResponse)
    def get_session_timeline(session_id: str, limit: int = 20) -> TimelineResponse:
        try:
            timeline = app.state.orchestrator.get_session_timeline(session_id, limit=limit)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return TimelineResponse.model_validate(timeline)

    @app.get("/api/sessions/{session_id}/checkpoints", response_model=CheckpointListResponse)
    def list_checkpoints(session_id: str) -> CheckpointListResponse:
        try:
            payload = app.state.orchestrator.list_checkpoints(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return CheckpointListResponse.model_validate(payload)

    @app.post("/api/sessions/{session_id}/checkpoints/{checkpoint_id}/restore", response_model=StateResponse)
    def restore_checkpoint(session_id: str, checkpoint_id: str) -> StateResponse:
        try:
            state = app.state.orchestrator.restore_checkpoint(session_id, checkpoint_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Checkpoint not found") from exc
        return StateResponse.from_state(state)

    @app.get("/api/sessions/{session_id}/export")
    def export_session(session_id: str) -> dict:
        try:
            return app.state.orchestrator.export_session(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc

    return app


app = create_app()
