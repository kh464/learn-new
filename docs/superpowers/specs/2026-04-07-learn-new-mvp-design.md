# Learn New MVP Design

## Goal

Build a runnable MVP of the domain-adaptive teaching multi-agent system described in `vibe coding-新领域学习agent.md`. The first version prioritizes a reliable local development loop over full production infrastructure.

## Scope Decision

The source architecture spans multiple independent subsystems: orchestration, knowledge ingestion, dynamic skills, practice evaluation, progress tracking, storage, and frontend delivery. Implementing all of them at production depth in one pass would produce a weak and untestable codebase, so this MVP narrows scope to a complete backend learning loop with pluggable adapters.

Included in this MVP:

- FastAPI backend
- LangGraph orchestration graph
- Local `.learn/` workspace manager
- File-backed learner state and checkpoints
- Research, curriculum, skill, instructor, practice, and progress agents
- Deterministic fallback behavior without a live LLM
- REST endpoints to bootstrap a session and advance one learning turn
- Tests for state, storage, orchestration, and API behavior

Deferred behind clear interfaces:

- Real web search and crawling
- Vector database integration
- Redis/PostgreSQL persistence
- Docker/E2B sandbox execution
- WebSocket streaming frontend

## Approaches Considered

### Approach 1: Full production stack immediately

Implement FastAPI, LangGraph, Redis, PostgreSQL, Qdrant, crawler, and sandbox integrations up front.

Trade-offs:

- Most faithful to the original architecture
- Highest implementation risk in an empty repository
- Slowest path to a verified end-to-end loop
- Hardest to test without external services

### Approach 2: Backend-first local MVP with adapter seams

Implement the architecture as a local, runnable backend with ports for future providers.

Trade-offs:

- Best balance of speed, correctness, and extensibility
- Preserves the core state machine and `.learn/` contract
- Makes future integration work incremental instead of structural

### Approach 3: Pure CLI prototype

Skip the service layer and build only a command-line runner around the teaching loop.

Trade-offs:

- Fastest to build
- Misses the HTTP interface expected by productization
- Would require rework to become the intended backend

## Recommended Approach

Approach 2. It preserves the architecture's central ideas while keeping the system runnable in the current repository without external infrastructure.

## Architecture

### Runtime shape

- `FastAPI` provides session creation and learning-loop endpoints.
- `LangGraph` models the orchestration flow from initialization through teaching and assessment.
- A file-backed workspace rooted at `.learn/sessions/<session_id>` stores state, curriculum, skills, checkpoints, and practice history.
- Agent classes implement the six roles from the design document and exchange typed data through a shared `LearnerState`.

### Data model

Core entities:

- `LearnerProfile`: user intent, experience, time budget, preferences
- `DomainMeta`: inferred domain type, pedagogy, primitives, assessment style, difficulty curve
- `CurriculumStage`: per-stage goal, concepts, exit criteria, practice format
- `MasteryRecord`: score, reviews, next review time, confidence
- `LearnerState`: session-wide orchestration state, logs, active skills, current lesson artifacts

### Learning loop

1. Initialize workspace and state
2. Research agent produces local knowledge notes from seed domain text
3. Curriculum agent derives domain metadata and a staged curriculum
4. Skill agent writes runtime skill YAML into `.learn/skills`
5. Instructor agent produces explanation and a micro-quiz
6. Practice agent generates a lab or quiz and deterministic reference answer
7. Assessment step scores the learner submission or simulated answer
8. Progress agent updates mastery and decides whether to repeat, advance, or review

### Error handling

- Missing workspace files are recreated from typed defaults
- Invalid provider config falls back to deterministic local mode
- Graph execution records error events in state logs before surfacing exceptions
- API endpoints return structured error payloads and never expose raw tracebacks by default

### Testing strategy

- Unit tests for workspace bootstrap and state persistence
- Unit tests for curriculum and progress rules
- Integration test for one graph execution cycle
- API tests for session creation and turn execution

## File Layout

- `app/main.py`: FastAPI application and route registration
- `app/config.py`: load and validate `config/llm.yaml`
- `app/models.py`: Pydantic state and domain models
- `app/workspace.py`: `.learn/` file system manager
- `app/agents/*.py`: agent role implementations
- `app/orchestrator.py`: LangGraph builder and orchestration service
- `app/api/schemas.py`: request and response schemas
- `tests/*`: unit and integration tests

## Explicit Non-Goals For This MVP

- Real LLM calls in the default path
- Multi-user authentication
- Browser frontend
- External queue workers
- Production deployment manifests

## Success Criteria

- `pytest` passes
- A session can be created via API
- A learning turn writes files into `.learn/`
- A learner state persists across turns
- The graph can advance or repeat based on score
