from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.models import Curriculum, DomainMeta, KnowledgeChunk, LearnerState


class WorkspaceManager:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def session_root(self, session_id: str) -> Path:
        return self.root / "sessions" / session_id

    def list_session_ids(self) -> list[str]:
        sessions_root = self.root / "sessions"
        if not sessions_root.exists():
            return []
        return sorted(
            [path.name for path in sessions_root.iterdir() if path.is_dir()],
            key=lambda session_id: (sessions_root / session_id).stat().st_mtime,
            reverse=True,
        )

    def bootstrap_session(self, state: LearnerState) -> Path:
        session_dir = self.session_root(state.session_id)
        for relative in [
            "knowledge/raw",
            "knowledge/indexed",
            "skills",
            "user_uploads",
            "labs",
            "checkpoints",
        ]:
            (session_dir / relative).mkdir(parents=True, exist_ok=True)
        self.write_session_config(state)
        self.save_state(state)
        self._write_progress(state)
        return session_dir

    def save_state(self, state: LearnerState) -> None:
        session_dir = self.session_root(state.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "state.json").write_text(
            json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._write_progress(state)
        self.write_session_config(state)
        if state.curriculum is not None:
            self.write_curriculum(state.session_id, state.curriculum)
        if state.domain_meta is not None:
            self.write_domain_meta(state.session_id, state.domain_meta)

    def load_state(self, session_id: str) -> LearnerState:
        path = self.session_root(session_id) / "state.json"
        return LearnerState.model_validate_json(path.read_text(encoding="utf-8"))

    def write_curriculum(self, session_id: str, curriculum: Curriculum) -> None:
        lines = [f"# {curriculum.domain} Curriculum", ""]
        for stage in curriculum.stages:
            lines.extend(
                [
                    f"## Stage {stage.stage}: {stage.title}",
                    f"- Objective: {stage.objective}",
                    f"- Concepts: {', '.join(stage.concepts)}",
                    f"- Practice: {stage.practice_format}",
                    f"- Exit: {stage.exit_criteria}",
                    "",
                ]
            )
        (self.session_root(session_id) / "curriculum.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

    def write_skill_file(self, session_id: str, name: str, content: str) -> Path:
        path = self.session_root(session_id) / "skills" / name
        path.write_text(content, encoding="utf-8")
        return path

    def write_session_config(self, state: LearnerState) -> Path:
        payload = {
            "session_id": state.session_id,
            "domain": state.domain,
            "current_stage": state.current_stage,
            "curriculum_version": state.curriculum_version,
            "learner_profile": state.learner_profile.model_dump(mode="json"),
        }
        path = self.session_root(state.session_id) / "config.yaml"
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def write_domain_meta(self, session_id: str, domain_meta: DomainMeta) -> Path:
        return self.write_json_artifact(
            session_id,
            "domain_meta.json",
            domain_meta.model_dump(mode="json"),
        )

    def write_json_artifact(self, session_id: str, relative_path: str, payload: object) -> Path:
        path = self.session_root(session_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def append_knowledge_chunks(self, session_id: str, chunks: list[KnowledgeChunk]) -> Path:
        path = self.session_root(session_id) / "knowledge" / "indexed" / "chunks.json"
        existing = self.read_knowledge_chunks(session_id)
        payload = [chunk.model_dump(mode="json") for chunk in existing + chunks]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_knowledge_chunks(self, session_id: str) -> list[KnowledgeChunk]:
        path = self.session_root(session_id) / "knowledge" / "indexed" / "chunks.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [KnowledgeChunk.model_validate(item) for item in data]

    def write_checkpoint(self, state: LearnerState) -> None:
        checkpoint_id = f"stage-{state.current_stage}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
        self.write_json_artifact(
            state.session_id,
            f"checkpoints/{checkpoint_id}.json",
            state.model_dump(mode="json"),
        )

    def list_checkpoints(self, session_id: str) -> list[Path]:
        checkpoint_dir = self.session_root(session_id) / "checkpoints"
        if not checkpoint_dir.exists():
            return []
        return sorted(checkpoint_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)

    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> LearnerState:
        path = self.session_root(session_id) / "checkpoints" / f"{checkpoint_id}.json"
        return LearnerState.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_progress(self, state: LearnerState) -> None:
        payload = {
            "current_stage": state.current_stage,
            "assessment_score": state.assessment_score,
            "consecutive_low_scores": state.consecutive_low_scores,
            "needs_intervention": state.needs_intervention,
            "teaching_mode": state.teaching_mode,
            "review_queue": state.review_queue,
            "mastery_matrix": {
                key: value.model_dump(mode="json")
                for key, value in state.mastery_matrix.items()
            },
        }
        (self.session_root(state.session_id) / "progress.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
