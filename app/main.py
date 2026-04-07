from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import os
from time import perf_counter
from pathlib import Path
from uuid import uuid4
import importlib

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi import status
from fastapi.websockets import WebSocketDisconnect
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
    TaskAcceptedResponse,
    TaskStatusResponse,
    TimelineResponse,
    TurnRequest,
    TurnTaskRequest,
    UploadKnowledgeRequest,
    UploadKnowledgeResponse,
)
from app.config import AppConfig, load_config
from app.event_stream import EventBroker
from app.knowledge import KnowledgeService
from app.orchestrator import LearningOrchestrator
from app.runtime_health import RuntimeHealthService
from app.runtime_ops import AppEventLogger, AuditLogger, InMemoryRateLimiter, MetricsRegistry, RedisRateLimiter
from app.task_queue import InMemoryTaskQueue, TaskQueueFullError


def create_app(
    workspace_root: Path | str = Path(".learn"),
    config_path: Path | str = Path("config/llm.yaml"),
) -> FastAPI:
    config = load_config(config_path)
    orchestrator = LearningOrchestrator(workspace_root=Path(workspace_root), config=config)
    metrics = MetricsRegistry()
    runtime_health = RuntimeHealthService(config=config, workspace_root=Path(workspace_root))
    event_broker = EventBroker()
    audit_logger = (
        AuditLogger(
            Path(config.observability.audit_log_path),
            max_lines=config.observability.audit_log_max_lines,
        )
        if config.observability.audit_log_path
        else None
    )
    app_logger = (
        AppEventLogger(
            Path(config.observability.app_log_path),
            max_lines=config.observability.app_log_max_lines,
        )
        if config.observability.app_log_path
        else None
    )
    task_queue = (
        InMemoryTaskQueue(
            worker_threads=config.tasks.worker_threads,
            max_queue_size=config.tasks.max_queue_size,
            on_update=lambda record: event_broker.publish(f"task:{record['task_id']}", record),
        )
        if config.tasks.enabled
        else None
    )
    rate_limiter = None
    if config.rate_limit.enabled:
        if config.rate_limit.backend == "redis":
            if not config.rate_limit.redis_url:
                raise RuntimeError("rate_limit.redis_url is required when rate_limit.backend=redis")
            redis_module = importlib.import_module("redis")
            rate_limiter = RedisRateLimiter(
                requests=config.rate_limit.requests,
                window_seconds=config.rate_limit.window_seconds,
                client=redis_module.Redis.from_url(config.rate_limit.redis_url),
                key_prefix=config.rate_limit.key_prefix,
            )
        else:
            rate_limiter = InMemoryRateLimiter(
                requests=config.rate_limit.requests,
                window_seconds=config.rate_limit.window_seconds,
            )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            event_broker.attach_loop(asyncio.get_running_loop())
            if task_queue is not None:
                task_queue.start()
            yield
        finally:
            if task_queue is not None:
                task_queue.shutdown()

    app = FastAPI(title="Learn New MVP", version="0.1.0", lifespan=lifespan)

    app.state.orchestrator = orchestrator
    app.state.config = config
    app.state.metrics = metrics
    app.state.audit_logger = audit_logger
    app.state.app_logger = app_logger
    app.state.runtime_health = runtime_health
    app.state.task_queue = task_queue
    app.state.event_broker = event_broker

    role_levels = {"viewer": 1, "operator": 2, "admin": 3}

    def get_principal(api_key: str | None) -> tuple[str, str] | None:
        if not api_key:
            return None
        if config.security.principals:
            for principal in config.security.principals:
                if api_key == principal.api_key:
                    return principal.name, principal.role
            return None
        if config.security.api_key and api_key == config.security.api_key:
            return "admin", "admin"
        return None

    def required_role_for(request: Request) -> str | None:
        path = request.url.path
        if path in {"/health", "/health/ready", "/dashboard"}:
            return None
        if path in {"/metrics", "/api/audit", "/api/runtime/summary", "/api/logs/app"}:
            return "admin"
        if not path.startswith("/api/"):
            return None
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return "viewer"
        return "operator"

    def can_access_session(principal_name: str, principal_role: str, owner_id: str) -> bool:
        if not config.security.enabled:
            return True
        if principal_role == "admin":
            return True
        if not owner_id:
            return True
        return principal_name == owner_id

    def can_access_task(principal_name: str, principal_role: str, owner_id: str) -> bool:
        return can_access_session(principal_name, principal_role, owner_id)

    def websocket_principal(websocket: WebSocket) -> tuple[str, str] | None:
        provided = websocket.headers.get(config.security.api_key_header)
        if not config.security.enabled:
            return "anonymous", "admin"
        principal = get_principal(provided)
        if principal is None:
            return None
        return principal

    @app.middleware("http")
    async def production_guards(request: Request, call_next):
        request_id = uuid4().hex
        trace_id = _resolve_trace_id(request.headers.get("traceparent")) or request_id
        started = perf_counter()
        request_id_header = config.observability.request_id_header
        trace_id_header = config.observability.trace_id_header
        principal_name = "anonymous"
        principal_role = "anonymous"
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.principal_name = principal_name
        request.state.principal_role = principal_role

        def finalize(response):
            latency_ms = (perf_counter() - started) * 1000
            response.headers[request_id_header] = request_id
            response.headers[trace_id_header] = trace_id
            metrics.record(response.status_code, latency_ms, path=request.url.path)
            if audit_logger is not None and request.url.path not in {"/health", "/health/ready"}:
                audit_logger.append(
                    {
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "principal": principal_name,
                        "role": principal_role,
                        "client": request.client.host if request.client else "unknown",
                    }
                )
            return response

        required_role = required_role_for(request)
        if config.security.enabled and required_role is not None:
            provided = request.headers.get(config.security.api_key_header)
            principal = get_principal(provided)
            if principal is None:
                return finalize(JSONResponse(status_code=401, content={"detail": "Unauthorized"}))
            principal_name, principal_role = principal
            request.state.principal_name = principal_name
            request.state.principal_role = principal_role
            if role_levels[principal_role] < role_levels[required_role]:
                return finalize(JSONResponse(status_code=403, content={"detail": "Forbidden"}))

        if rate_limiter is not None and request.url.path not in {"/health", "/metrics"}:
            client_host = request.client.host if request.client else "unknown"
            rate_limit_key = principal_name if principal_name != "anonymous" else client_host
            if not rate_limiter.allow(rate_limit_key):
                response = JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
                response.headers["Retry-After"] = str(config.rate_limit.window_seconds)
                return finalize(response)

        try:
            response = await call_next(request)
        except Exception as exc:
            if app_logger is not None:
                app_logger.append(
                    {
                        "event": "unhandled_exception",
                        "request_id": request_id,
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                        "principal": principal_name,
                        "role": principal_role,
                        "error": repr(exc),
                    }
                )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error", "request_id": request_id},
            )
        return finalize(response)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def health_ready():
        payload = runtime_health.readiness_payload()
        if payload["status"] != "ok":
            return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
        return payload

    if config.observability.metrics_enabled:
        @app.get("/metrics")
        def get_metrics() -> PlainTextResponse:
            return PlainTextResponse(metrics.render_prometheus())

    @app.get("/api/audit")
    def get_audit_events(limit: int = 100) -> dict:
        if audit_logger is None:
            return {"items": []}
        return {"items": audit_logger.read_recent(limit=limit)}

    @app.get("/api/logs/app")
    def get_app_log_events(limit: int = 100) -> dict:
        if app_logger is None:
            return {"items": []}
        return {"items": app_logger.read_recent(limit=limit)}

    @app.get("/api/runtime/summary")
    def get_runtime_summary() -> dict:
        return runtime_health.runtime_summary(
            metrics_snapshot=metrics.snapshot(),
            audit_enabled=audit_logger is not None,
            audit_recent_count=len(audit_logger.read_recent(limit=20)) if audit_logger is not None else 0,
            app_log_enabled=app_logger is not None,
            app_log_recent_count=len(app_logger.read_recent(limit=20)) if app_logger is not None else 0,
            task_queue_enabled=task_queue is not None,
            task_queue_snapshot=task_queue.snapshot() if task_queue is not None else None,
            session_total=app.state.orchestrator.list_sessions()["total"],
        )

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
    def create_session(payload: CreateSessionRequest, request: Request) -> StateResponse:
        state = app.state.orchestrator.create_session(
            domain=payload.domain,
            profile=payload.to_profile(),
            owner_id=request.state.principal_name if config.security.enabled else "",
        )
        return StateResponse.from_state(state)

    @app.get("/api/sessions", response_model=SessionIndexResponse)
    def list_sessions(request: Request) -> SessionIndexResponse:
        payload = app.state.orchestrator.list_sessions()
        if config.security.enabled and request.state.principal_role != "admin":
            payload["items"] = [
                item
                for item in payload["items"]
                if can_access_session(request.state.principal_name, request.state.principal_role, item.get("owner_id", ""))
            ]
            payload["total"] = len(payload["items"])
        return SessionIndexResponse.model_validate(payload)

    @app.post("/api/sessions/{session_id}/knowledge", response_model=UploadKnowledgeResponse, status_code=201)
    def upload_knowledge(session_id: str, payload: UploadKnowledgeRequest, request: Request) -> UploadKnowledgeResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
            raise HTTPException(status_code=404, detail="Session not found")
        service = KnowledgeService(app.state.orchestrator.workspace)
        chunks = service.ingest_text(
            session_id=session_id,
            title=payload.title,
            content=payload.content,
            source=payload.source,
        )
        return UploadKnowledgeResponse(session_id=session_id, chunks_added=len(chunks))

    @app.get("/api/sessions/{session_id}/knowledge/search", response_model=SearchKnowledgeResponse)
    def search_knowledge(session_id: str, request: Request, query: str, limit: int = 3) -> SearchKnowledgeResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
            raise HTTPException(status_code=404, detail="Session not found")
        service = KnowledgeService(app.state.orchestrator.workspace)
        items = service.retrieve(session_id=session_id, query=query, limit=limit)
        return SearchKnowledgeResponse(items=items)

    @app.get("/api/sessions/{session_id}", response_model=StateResponse)
    def get_session(session_id: str, request: Request) -> StateResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return StateResponse.from_state(state)

    @app.post("/api/sessions/{session_id}/turns", response_model=StateResponse)
    def run_turn(session_id: str, payload: TurnRequest, request: Request) -> StateResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
                raise HTTPException(status_code=404, detail="Session not found")
            state = app.state.orchestrator.run_turn(
                session_id=session_id,
                learner_answer=payload.learner_answer,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return StateResponse.from_state(state)

    @app.post("/api/tasks/turns", response_model=TaskAcceptedResponse, status_code=202)
    def enqueue_turn_task(payload: TurnTaskRequest, request: Request) -> TaskAcceptedResponse:
        if task_queue is None:
            raise HTTPException(status_code=503, detail="Task queue disabled")
        try:
            state = app.state.orchestrator.get_state(payload.session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
            raise HTTPException(status_code=404, detail="Session not found")
        try:
            task = task_queue.submit(
                task_type="turn",
                session_id=payload.session_id,
                owner_id=state.owner_id or request.state.principal_name,
                runner=lambda: StateResponse.from_state(
                    app.state.orchestrator.run_turn(
                        session_id=payload.session_id,
                        learner_answer=payload.learner_answer,
                    )
                ).model_dump(mode="json"),
            )
        except TaskQueueFullError as exc:
            raise HTTPException(status_code=503, detail="Task queue full") from exc
        return TaskAcceptedResponse.model_validate(task)

    @app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
    def get_task_status(task_id: str, request: Request) -> TaskStatusResponse:
        if task_queue is None:
            raise HTTPException(status_code=503, detail="Task queue disabled")
        try:
            task = task_queue.get(task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc
        if not can_access_task(request.state.principal_name, request.state.principal_role, task["owner_id"]):
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskStatusResponse.model_validate(task)

    @app.websocket("/ws/tasks/{task_id}")
    async def stream_task_status(task_id: str, websocket: WebSocket) -> None:
        principal = websocket_principal(websocket)
        if principal is None:
            await websocket.close(code=1008)
            return
        principal_name, principal_role = principal
        if task_queue is None:
            await websocket.close(code=1013)
            return
        try:
            task = task_queue.get(task_id)
        except FileNotFoundError:
            await websocket.close(code=1008)
            return
        if not can_access_task(principal_name, principal_role, task["owner_id"]):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        subscriber_id, queue = await event_broker.subscribe(f"task:{task_id}")
        try:
            current = task_queue.get(task_id)
            await websocket.send_json(current)
            if current["status"] in {"completed", "failed"}:
                await websocket.close()
                return
            while True:
                update = await queue.get()
                await websocket.send_json(update)
                if update["status"] in {"completed", "failed"}:
                    await websocket.close()
                    return
        except WebSocketDisconnect:
            return
        finally:
            await event_broker.unsubscribe(f"task:{task_id}", subscriber_id)

    @app.get("/api/sessions/{session_id}/reviews/due", response_model=DueReviewResponse)
    def get_due_reviews(session_id: str, request: Request) -> DueReviewResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
                raise HTTPException(status_code=404, detail="Session not found")
            items = app.state.orchestrator.get_due_reviews(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return DueReviewResponse(items=items)

    @app.post("/api/sessions/{session_id}/reviews", response_model=StateResponse)
    def start_review(session_id: str, request: Request) -> StateResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
                raise HTTPException(status_code=404, detail="Session not found")
            state = app.state.orchestrator.start_review(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return StateResponse.from_state(state)

    @app.get("/api/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
    def get_session_summary(session_id: str, request: Request) -> SessionSummaryResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
                raise HTTPException(status_code=404, detail="Session not found")
            summary = app.state.orchestrator.get_session_summary(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return SessionSummaryResponse.model_validate(summary)

    @app.get("/api/sessions/{session_id}/timeline", response_model=TimelineResponse)
    def get_session_timeline(session_id: str, request: Request, limit: int = 20) -> TimelineResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
                raise HTTPException(status_code=404, detail="Session not found")
            timeline = app.state.orchestrator.get_session_timeline(session_id, limit=limit)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return TimelineResponse.model_validate(timeline)

    @app.get("/api/sessions/{session_id}/checkpoints", response_model=CheckpointListResponse)
    def list_checkpoints(session_id: str, request: Request) -> CheckpointListResponse:
        try:
            state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
                raise HTTPException(status_code=404, detail="Session not found")
            payload = app.state.orchestrator.list_checkpoints(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc
        return CheckpointListResponse.model_validate(payload)

    @app.post("/api/sessions/{session_id}/checkpoints/{checkpoint_id}/restore", response_model=StateResponse)
    def restore_checkpoint(session_id: str, checkpoint_id: str, request: Request) -> StateResponse:
        try:
            owner_state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, owner_state.owner_id):
                raise HTTPException(status_code=404, detail="Checkpoint not found")
            state = app.state.orchestrator.restore_checkpoint(session_id, checkpoint_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Checkpoint not found") from exc
        return StateResponse.from_state(state)

    @app.get("/api/sessions/{session_id}/export")
    def export_session(session_id: str, request: Request) -> dict:
        try:
            state = app.state.orchestrator.get_state(session_id)
            if not can_access_session(request.state.principal_name, request.state.principal_role, state.owner_id):
                raise HTTPException(status_code=404, detail="Session not found")
            return app.state.orchestrator.export_session(session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Session not found") from exc

    return app


app = create_app(config_path=Path(os.getenv("LEARN_NEW_CONFIG_PATH", "config/llm.yaml")))


def _resolve_trace_id(traceparent: str | None) -> str | None:
    if not traceparent:
        return None
    parts = traceparent.split("-")
    if len(parts) != 4:
        return None
    candidate = parts[1]
    if len(candidate) != 32:
        return None
    if any(char not in "0123456789abcdef" for char in candidate.lower()):
        return None
    return candidate.lower()
