from __future__ import annotations

from time import perf_counter
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

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
from app.runtime_ops import InMemoryRateLimiter, MetricsRegistry


def create_app(
    workspace_root: Path | str = Path(".learn"),
    config_path: Path | str = Path("config/llm.yaml"),
) -> FastAPI:
    app = FastAPI(title="Learn New MVP", version="0.1.0")
    config = load_config(config_path)
    orchestrator = LearningOrchestrator(workspace_root=Path(workspace_root), config=config)
    metrics = MetricsRegistry()
    rate_limiter = (
        InMemoryRateLimiter(
            requests=config.rate_limit.requests,
            window_seconds=config.rate_limit.window_seconds,
        )
        if config.rate_limit.enabled
        else None
    )

    app.state.orchestrator = orchestrator
    app.state.config = config
    app.state.metrics = metrics

    @app.middleware("http")
    async def production_guards(request: Request, call_next):
        request_id = uuid4().hex
        started = perf_counter()
        request_id_header = config.observability.request_id_header

        def finalize(response):
            latency_ms = (perf_counter() - started) * 1000
            response.headers[request_id_header] = request_id
            metrics.record(response.status_code, latency_ms)
            return response

        protected = request.url.path != "/health"
        if config.security.enabled and protected:
            provided = request.headers.get(config.security.api_key_header)
            if not config.security.api_key or provided != config.security.api_key:
                return finalize(JSONResponse(status_code=401, content={"detail": "Unauthorized"}))

        if rate_limiter is not None and request.url.path not in {"/health", "/metrics"}:
            client_host = request.client.host if request.client else "unknown"
            if not rate_limiter.allow(client_host):
                return finalize(JSONResponse(status_code=429, content={"detail": "Too Many Requests"}))

        response = await call_next(request)
        return finalize(response)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def health_ready() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "storage_backend": config.storage.backend,
            "sandbox_backend": config.sandbox.backend,
            "metrics_enabled": config.observability.metrics_enabled,
            "security_enabled": config.security.enabled,
            "rate_limit_enabled": config.rate_limit.enabled,
        }

    if config.observability.metrics_enabled:
        @app.get("/metrics")
        def get_metrics() -> PlainTextResponse:
            return PlainTextResponse(metrics.render_prometheus())

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
