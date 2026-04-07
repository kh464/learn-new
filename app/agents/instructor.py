from __future__ import annotations

from app.knowledge import KnowledgeService
from app.llm import LLMGateway
from app.models import LearnerState, LessonArtifact
from app.workspace import WorkspaceManager


class InstructorAgent:
    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm

    def run(self, state: LearnerState, manager: WorkspaceManager) -> LearnerState:
        concepts: list[str] = []
        objective = f"理解 {state.domain} 的关键概念。"
        if state.curriculum is not None:
            stage = state.curriculum.stages[state.current_stage - 1]
            concepts = stage.concepts
            objective = stage.objective

        focus = state.review_queue[0] if state.review_queue else (concepts[0] if concepts else state.domain)
        retrieval = KnowledgeService(manager).retrieve(state.session_id, focus, limit=2)
        lesson = self._fallback_lesson(state, objective, focus, retrieval)
        if self.llm and self.llm.is_available("chat"):
            try:
                payload = self.llm.complete_json(
                    system_prompt=(
                        "你是一位严谨的教学导师。请输出 JSON，字段必须是 "
                        "explanation, key_takeaways, micro_quiz, next_step。"
                    ),
                    user_prompt=(
                        f"领域：{state.domain}\n"
                        f"阶段目标：{objective}\n"
                        f"教学模式：{state.teaching_mode}\n"
                        f"当前聚焦概念：{focus}\n"
                        f"复习队列：{state.review_queue}\n"
                        f"可用知识片段：{[item.content for item in retrieval]}\n"
                        "请生成一段面向中文学习者的简洁讲解、3 条要点、1 个微测验和下一步建议。"
                    ),
                    profile="chat",
                )
                lesson = LessonArtifact.model_validate(payload)
                state.add_log("llm_used", "Instructor generated lesson with configured LLM provider.")
            except Exception as exc:
                state.add_log("llm_fallback", f"Instructor fell back to local generator: {exc}")
        state.lesson = lesson
        manager.write_json_artifact(
            state.session_id,
            "lesson.json",
            lesson.model_dump(mode="json"),
        )
        state.add_log("lesson_generated", f"Prepared lesson for stage {state.current_stage}.")
        return state

    def _fallback_lesson(self, state: LearnerState, objective: str, focus: str, retrieval: list) -> LessonArtifact:
        retrieval_hint = (
            f" 结合资料片段：{retrieval[0].content}"
            if retrieval
            else ""
        )
        remedial_prefix = (
            f"当前处于补救模式，需要先复习 `{focus}` 并用更简单的例子重新建立理解。"
            if state.teaching_mode == "remedial"
            else ""
        )
        review_prefix = (
            f"当前处于复习模式，本轮回顾 `{focus}`，重点是重新唤起记忆并确认你还能解释它。"
            if state.teaching_mode == "review"
            else ""
        )
        next_step = "完成微测验后进入实践题。"
        if state.teaching_mode == "remedial":
            next_step = "先完成补救练习，再重新尝试当前阶段实践题。"
        if state.teaching_mode == "review":
            next_step = "先完成复习题，确认掌握后再回到正常学习节奏。"
        return LessonArtifact(
            explanation=(
                f"{review_prefix}{remedial_prefix} 当前阶段目标是：{objective} "
                f"本轮聚焦 `{focus}`。把它理解为解决问题时最先要建立的心智模型。"
                f"{retrieval_hint}"
            ),
            key_takeaways=[
                f"{focus} 决定了 {state.domain} 的基础理解方式。",
                "先建立模型，再进入工具和优化细节。",
                "能解释概念边界，比背定义更重要。",
            ],
            micro_quiz={
                "question": f"请用一句话解释 {focus} 在 {state.domain} 里的作用。",
                "expected_points": [focus, "作用", "场景"],
            },
            next_step=next_step,
        )
