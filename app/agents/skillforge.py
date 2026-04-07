from __future__ import annotations

import yaml

from app.models import LearnerState
from app.workspace import WorkspaceManager


class SkillForgeAgent:
    def run(self, state: LearnerState, manager: WorkspaceManager) -> LearnerState:
        stage = state.current_stage
        current_concepts = []
        if state.curriculum is not None:
            current_concepts = state.curriculum.stages[stage - 1].concepts

        skill_name = f"instructor_stage_{stage}.yaml"
        payload = {
            "role": (
                f"你是一位精通 {state.domain} 的阶段 {stage} 导师。"
                "每轮只推进一个核心概念，优先用例子解释。"
            ),
            "constraints": {
                "max_concepts_per_turn": 1,
                "must_use_socratic_method": True,
                "forbid_direct_answers_for_quizzes": True,
            },
            "current_concepts": current_concepts,
        }
        manager.write_skill_file(
            state.session_id,
            skill_name,
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        )
        if skill_name not in state.active_skills:
            state.active_skills.append(skill_name)
        state.add_log("skill_forged", f"Generated runtime skill {skill_name}.")
        return state
