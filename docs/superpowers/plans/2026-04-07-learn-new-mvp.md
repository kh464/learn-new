# Learn New MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable backend MVP of the adaptive teaching multi-agent system with local state persistence and a LangGraph orchestration loop.

**Architecture:** The system will use FastAPI for transport, LangGraph for workflow orchestration, and a file-backed `.learn/` workspace for all persistent state. Each agent role from the source design will be implemented as a focused Python module with deterministic local behavior so the project is fully testable without external services.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, LangGraph, PyYAML, pytest

---

### Task 1: Bootstrap state and workspace layer

**Files:**
- Create: `app/models.py`
- Create: `app/workspace.py`
- Create: `tests/test_workspace.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from app.models import LearnerProfile, LearnerState
from app.workspace import WorkspaceManager


def test_workspace_bootstraps_and_persists_state(tmp_path: Path) -> None:
    manager = WorkspaceManager(root=tmp_path / ".learn")
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )

    manager.bootstrap_session(state)
    manager.save_state(state)
    loaded = manager.load_state(state.session_id)

    assert loaded.session_id == state.session_id
    assert (tmp_path / ".learn" / "sessions" / state.session_id / "progress.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workspace.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write minimal implementation**

Create typed models for learner profile and state, then implement a workspace manager that creates the session directory tree and persists state to JSON.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workspace.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/workspace.py tests/test_workspace.py
git commit -m "feat: add learner state workspace persistence"
```

### Task 2: Implement curriculum and progress logic

**Files:**
- Create: `app/agents/curriculum.py`
- Create: `app/agents/progress.py`
- Create: `tests/test_curriculum_progress.py`

- [ ] **Step 1: Write the failing test**

```python
from app.agents.curriculum import CurriculumArchitectAgent
from app.agents.progress import ProgressMonitorAgent
from app.models import DomainMeta, LearnerProfile, LearnerState


def test_curriculum_has_five_stages_and_progress_advances_on_high_score() -> None:
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    curriculum_agent = CurriculumArchitectAgent()
    progress_agent = ProgressMonitorAgent()

    state.domain_meta = curriculum_agent.analyze_domain(state.domain)
    state.curriculum = curriculum_agent.build_curriculum(state.domain, state.domain_meta)
    state.assessment_score = 92

    updated = progress_agent.update_progress(state)

    assert len(updated.curriculum.stages) == 5
    assert updated.current_stage == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_curriculum_progress.py -v`
Expected: FAIL with missing curriculum or progress modules

- [ ] **Step 3: Write minimal implementation**

Implement domain analysis heuristics, a five-stage curriculum builder, and score-based stage advancement using a simple mastery matrix.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_curriculum_progress.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/curriculum.py app/agents/progress.py tests/test_curriculum_progress.py
git commit -m "feat: add curriculum and progress agents"
```

### Task 3: Implement research, skills, instruction, and practice agents

**Files:**
- Create: `app/agents/research.py`
- Create: `app/agents/skillforge.py`
- Create: `app/agents/instructor.py`
- Create: `app/agents/practice.py`
- Create: `tests/test_agents.py`

- [ ] **Step 1: Write the failing test**

```python
from app.agents.instructor import InstructorAgent
from app.agents.practice import PracticeEvaluatorAgent
from app.agents.research import ResearcherAgent
from app.agents.skillforge import SkillForgeAgent
from app.models import LearnerProfile, LearnerState
from app.workspace import WorkspaceManager


def test_agents_generate_learning_artifacts(tmp_path) -> None:
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    manager = WorkspaceManager(root=tmp_path / ".learn")
    manager.bootstrap_session(state)

    state = ResearcherAgent().run(state, manager)
    state = SkillForgeAgent().run(state, manager)
    state = InstructorAgent().run(state, manager)
    state = PracticeEvaluatorAgent().run(state, manager)

    assert state.knowledge_items
    assert state.active_skills
    assert state.lesson is not None
    assert state.practice is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agents.py -v`
Expected: FAIL with missing agent implementations

- [ ] **Step 3: Write minimal implementation**

Implement deterministic local agents that create notes, skill YAML, lesson content, and practice artifacts.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agents.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/research.py app/agents/skillforge.py app/agents/instructor.py app/agents/practice.py tests/test_agents.py
git commit -m "feat: add learning artifact agents"
```

### Task 4: Build the LangGraph orchestrator

**Files:**
- Create: `app/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
from app.models import LearnerProfile
from app.orchestrator import LearningOrchestrator


def test_orchestrator_runs_one_turn(tmp_path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    state = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )

    updated = orchestrator.run_turn(
        session_id=state.session_id,
        learner_answer="asyncio 用于调度协程",
    )

    assert updated.lesson is not None
    assert updated.practice is not None
    assert updated.logs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL with missing orchestrator

- [ ] **Step 3: Write minimal implementation**

Build a LangGraph state graph that routes through curriculum, skills, teaching, practice, and progress nodes, then persists updated state after each turn.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_orchestrator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add langgraph learning orchestrator"
```

### Task 5: Add API layer and config loading

**Files:**
- Create: `app/config.py`
- Create: `app/api/schemas.py`
- Create: `app/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_api_creates_session_and_runs_turn(tmp_path) -> None:
    app = create_app(workspace_root=tmp_path / ".learn")
    client = TestClient(app)

    response = client.post(
        "/api/sessions",
        json={"domain": "Python 异步编程", "goal": "掌握 async/await"},
    )
    assert response.status_code == 201
    session_id = response.json()["session_id"]

    turn = client.post(
        f"/api/sessions/{session_id}/turns",
        json={"learner_answer": "我会用 asyncio.create_task"},
    )
    assert turn.status_code == 200
    assert "lesson" in turn.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with missing app factory or routes

- [ ] **Step 3: Write minimal implementation**

Load the YAML config, expose API schemas, and register session and turn endpoints backed by the orchestrator.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/config.py app/api/schemas.py app/main.py tests/test_api.py
git commit -m "feat: add api layer and config loading"
```

### Task 6: Finish documentation and verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the failing test**

There is no automated README test. Instead, define the documentation acceptance criteria: setup instructions, run command, test command, and `.learn/` output location must all be present.

- [ ] **Step 2: Run verification to confirm the current README fails the acceptance criteria**

Run: `python -c "from pathlib import Path; text = Path('README.md').read_text(encoding='utf-16'); required = ['uvicorn', 'pytest', '.learn']; missing = [item for item in required if item not in text]; print(missing); raise SystemExit(1 if missing else 0)"`
Expected: FAIL with missing setup and run instructions

- [ ] **Step 3: Write minimal implementation**

Update `README.md` with project overview, setup commands, API routes, and test instructions.

- [ ] **Step 4: Run verification to confirm it passes**

Run: `python -c "from pathlib import Path; text = Path('README.md').read_text(encoding='utf-16'); required = ['uvicorn', 'pytest', '.learn']; missing = [item for item in required if item not in text]; print(missing); raise SystemExit(1 if missing else 0)"`
Expected: PASS with `[]`

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document learn new mvp"
```
