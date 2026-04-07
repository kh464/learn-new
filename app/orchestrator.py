from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import AppConfig
from app.agents.curriculum import CurriculumArchitectAgent
from app.agents.instructor import InstructorAgent
from app.agents.practice import PracticeEvaluatorAgent
from app.agents.progress import ProgressMonitorAgent
from app.agents.research import ResearcherAgent
from app.agents.skillforge import SkillForgeAgent
from app.llm import LLMGateway
from app.models import LearnerProfile, LearnerState
from app.session_store import SQLiteSessionStore
from app.sandbox import build_sandbox
from app.workspace import WorkspaceManager


class GraphState(TypedDict):
    state: LearnerState
    learner_answer: str


class LearningOrchestrator:
    def __init__(self, workspace_root: Path, config: AppConfig | None = None) -> None:
        self.workspace = WorkspaceManager(root=Path(workspace_root))
        self.session_store = self._build_session_store(workspace_root=Path(workspace_root), config=config)
        self.llm = LLMGateway(config=config) if config is not None else None
        self.researcher = ResearcherAgent(llm=self.llm)
        self.curriculum = CurriculumArchitectAgent()
        self.skillforge = SkillForgeAgent()
        self.instructor = InstructorAgent(llm=self.llm)
        self.practice = PracticeEvaluatorAgent(llm=self.llm, sandbox=build_sandbox(config))
        self.progress = ProgressMonitorAgent()
        self.graph = self._build_graph()

    def create_session(self, domain: str, profile: LearnerProfile) -> LearnerState:
        state = LearnerState.new(domain=domain, profile=profile)
        self.workspace.bootstrap_session(state)
        if self.session_store is not None:
            self.session_store.save_state(state)
        return state

    def get_state(self, session_id: str) -> LearnerState:
        return self._load_state(session_id)

    def get_due_reviews(self, session_id: str) -> list[str]:
        state = self._load_state(session_id)
        return self.progress.collect_due_concepts(state)

    def get_session_timeline(self, session_id: str, limit: int = 20) -> dict:
        state = self._load_state(session_id)
        items = [
            {
                "timestamp": event.timestamp.isoformat(),
                "kind": event.kind,
                "message": event.message,
            }
            for event in state.logs[-limit:]
        ]
        return {"items": items}

    def get_session_summary(self, session_id: str) -> dict:
        state = self._load_state(session_id)
        due_reviews = self.progress.collect_due_concepts(state)
        mastery_items = list(state.mastery_matrix.items())
        average_score = (
            round(sum(record.score for _, record in mastery_items) / len(mastery_items), 2)
            if mastery_items
            else 0.0
        )
        strongest_concept = None
        weakest_concept = None
        if mastery_items:
            strongest_concept = max(mastery_items, key=lambda item: item[1].score)[0]
            weakest_concept = min(mastery_items, key=lambda item: item[1].score)[0]

        return {
            "session_id": state.session_id,
            "domain": state.domain,
            "current_stage": state.current_stage,
            "teaching_mode": state.teaching_mode,
            "assessment_score": state.assessment_score,
            "log_count": len(state.logs),
            "due_review_count": len(due_reviews),
            "active_skills": state.active_skills,
            "mastery_overview": {
                "tracked_concepts": len(mastery_items),
                "average_score": average_score,
                "due_review_count": len(due_reviews),
                "strongest_concept": strongest_concept,
                "weakest_concept": weakest_concept,
            },
        }

    def list_checkpoints(self, session_id: str) -> dict:
        if self.session_store is not None:
            return {"items": self.session_store.list_checkpoints(session_id)}
        items = []
        for path in self.workspace.list_checkpoints(session_id):
            state = LearnerState.model_validate_json(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "checkpoint_id": path.stem,
                    "created_at": path.stat().st_mtime_ns,
                    "current_stage": state.current_stage,
                    "teaching_mode": state.teaching_mode,
                    "assessment_score": state.assessment_score,
                }
            )
        items.sort(key=lambda item: item["created_at"])
        for item in items:
            # convert after sorting to keep numeric ordering simple
            item["created_at"] = __import__("datetime").datetime.fromtimestamp(
                item["created_at"] / 1_000_000_000,
                tz=__import__("datetime").timezone.utc,
            ).isoformat()
        return {"items": items}

    def restore_checkpoint(self, session_id: str, checkpoint_id: str) -> LearnerState:
        state = self._load_checkpoint(session_id, checkpoint_id)
        state.add_log("checkpoint_restored", f"Restored checkpoint {checkpoint_id}.")
        self._persist_state(state)
        self._write_checkpoint(state)
        return state

    def export_session(self, session_id: str) -> dict:
        state = self._load_state(session_id)
        session_root = self.workspace.session_root(session_id)

        def read_text_if_exists(path: Path) -> str | None:
            return path.read_text(encoding="utf-8") if path.exists() else None

        def read_json_if_exists(path: Path):
            if not path.exists():
                return None
            import json

            return json.loads(path.read_text(encoding="utf-8"))

        skill_dir = session_root / "skills"
        skills = {}
        if skill_dir.exists():
            for path in sorted(skill_dir.glob("*.yaml")):
                skills[path.name] = path.read_text(encoding="utf-8")

        return {
            "session": {
                "session_id": state.session_id,
                "domain": state.domain,
                "current_stage": state.current_stage,
                "teaching_mode": state.teaching_mode,
            },
            "summary": self.get_session_summary(session_id),
            "timeline": self.get_session_timeline(session_id, limit=200),
            "checkpoints": self.list_checkpoints(session_id),
            "artifacts": {
                "state": state.model_dump(mode="json"),
                "curriculum_markdown": read_text_if_exists(session_root / "curriculum.md"),
                "lesson": read_json_if_exists(session_root / "lesson.json"),
                "progress": read_json_if_exists(session_root / "progress.json"),
                "domain_meta": read_json_if_exists(session_root / "domain_meta.json"),
                "knowledge_items": read_json_if_exists(session_root / "knowledge" / "indexed" / "knowledge.json"),
                "knowledge_chunks": read_json_if_exists(session_root / "knowledge" / "indexed" / "chunks.json"),
                "latest_practice": read_json_if_exists(session_root / "labs" / "latest_practice.json"),
                "skills": skills,
            },
        }

    def list_sessions(self) -> dict:
        items = []
        for session_id in self._list_session_ids():
            state = self._load_state(session_id)
            summary = self.get_session_summary(session_id)
            items.append(
                {
                    "session_id": state.session_id,
                    "domain": state.domain,
                    "current_stage": state.current_stage,
                    "teaching_mode": state.teaching_mode,
                    "assessment_score": state.assessment_score,
                    "summary": summary,
                }
            )
        return {"total": len(items), "items": items}

    def start_review(self, session_id: str, concepts: list[str] | None = None) -> LearnerState:
        state = self._load_state(session_id)
        state = self.curriculum.run(state, self.workspace)
        due_concepts = concepts or self.progress.collect_due_concepts(state)
        if not due_concepts:
            state.add_log("review_skipped", "No due review concepts were found.")
            self._persist_state(state)
            return state

        state.teaching_mode = "review"
        state.review_queue = due_concepts
        state.needs_intervention = False
        state = self.skillforge.run(state, self.workspace)
        state = self.instructor.run(state, self.workspace)
        state = self.practice.run(state, self.workspace)
        state.add_log("review_started", f"Started review for concepts: {', '.join(due_concepts)}.")
        self._persist_state(state)
        self._write_checkpoint(state)
        return state

    def run_turn(self, session_id: str, learner_answer: str) -> LearnerState:
        state = self._load_state(session_id)
        result = self.graph.invoke({"state": state, "learner_answer": learner_answer})
        updated = result["state"]
        self._persist_state(updated)
        self._write_checkpoint(updated)
        return updated

    def _build_session_store(self, workspace_root: Path, config: AppConfig | None) -> SQLiteSessionStore | None:
        if config is None or config.storage.backend != "sqlite":
            return None
        sqlite_path = Path(config.storage.sqlite_path) if config.storage.sqlite_path else workspace_root / "sessions.db"
        return SQLiteSessionStore(sqlite_path)

    def _load_state(self, session_id: str) -> LearnerState:
        if self.session_store is not None:
            return self.session_store.load_state(session_id)
        return self.workspace.load_state(session_id)

    def _persist_state(self, state: LearnerState) -> None:
        self.workspace.save_state(state)
        if self.session_store is not None:
            self.session_store.save_state(state)

    def _write_checkpoint(self, state: LearnerState) -> None:
        self.workspace.write_checkpoint(state)
        if self.session_store is not None:
            self.session_store.write_checkpoint(state)

    def _list_session_ids(self) -> list[str]:
        if self.session_store is not None:
            return self.session_store.list_session_ids()
        return self.workspace.list_session_ids()

    def _load_checkpoint(self, session_id: str, checkpoint_id: str) -> LearnerState:
        if self.session_store is not None:
            return self.session_store.load_checkpoint(session_id, checkpoint_id)
        return self.workspace.load_checkpoint(session_id, checkpoint_id)

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("research", self._research)
        graph.add_node("curriculum", self._curriculum)
        graph.add_node("skillforge", self._skillforge)
        graph.add_node("teach", self._teach)
        graph.add_node("practice", self._practice)
        graph.add_node("assess", self._assess)
        graph.add_node("progress", self._progress)
        graph.add_edge(START, "research")
        graph.add_edge("research", "curriculum")
        graph.add_edge("curriculum", "skillforge")
        graph.add_edge("skillforge", "teach")
        graph.add_edge("teach", "practice")
        graph.add_edge("practice", "assess")
        graph.add_edge("assess", "progress")
        graph.add_edge("progress", END)
        return graph.compile()

    def _research(self, payload: GraphState) -> GraphState:
        payload["state"] = self.researcher.run(payload["state"], self.workspace)
        return payload

    def _curriculum(self, payload: GraphState) -> GraphState:
        payload["state"] = self.curriculum.run(payload["state"], self.workspace)
        return payload

    def _skillforge(self, payload: GraphState) -> GraphState:
        payload["state"] = self.skillforge.run(payload["state"], self.workspace)
        return payload

    def _teach(self, payload: GraphState) -> GraphState:
        payload["state"] = self.instructor.run(payload["state"], self.workspace)
        return payload

    def _practice(self, payload: GraphState) -> GraphState:
        payload["state"] = self.practice.run(payload["state"], self.workspace)
        return payload

    def _assess(self, payload: GraphState) -> GraphState:
        payload["state"] = self.practice.evaluate(payload["state"], payload["learner_answer"])
        return payload

    def _progress(self, payload: GraphState) -> GraphState:
        payload["state"] = self.progress.update_progress(payload["state"])
        return payload
