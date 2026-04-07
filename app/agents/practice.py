from __future__ import annotations

from app.llm import LLMGateway
from app.models import LearnerState, PracticeArtifact
from app.sandbox import PythonSandbox
from app.workspace import WorkspaceManager


class PracticeEvaluatorAgent:
    def __init__(self, llm: LLMGateway | None = None, sandbox: PythonSandbox | None = None) -> None:
        self.llm = llm
        self.sandbox = sandbox or PythonSandbox()

    def run(self, state: LearnerState, manager: WorkspaceManager) -> LearnerState:
        stage_title = f"Stage {state.current_stage}"
        concept = state.review_queue[0] if state.review_queue else state.domain
        is_python_domain = "python" in state.domain.lower()
        if state.curriculum is not None:
            stage = state.curriculum.stages[state.current_stage - 1]
            stage_title = stage.title
            if not state.review_queue:
                concept = stage.concepts[0]

        if state.teaching_mode == "review":
            practice = PracticeArtifact(
                title=f"{stage_title} Review",
                prompt=f"请复习 `{concept}`，用 2 到 3 句话说明它的作用、一个使用场景，以及一个常见误区。",
                expected_answer=f"答案需要覆盖 `{concept}` 的作用、场景和误区。",
                rubric=[
                    "解释核心概念",
                    "给出使用场景",
                    "指出一个常见误区",
                ],
                reference_code="",
                evaluation_mode="freeform",
                test_code="",
            )
            state.practice = practice
            manager.write_json_artifact(
                state.session_id,
                "labs/latest_practice.json",
                practice.model_dump(mode="json"),
            )
            state.add_log("practice_generated", f"Generated review practice for concept {concept}.")
            return state

        practice = PracticeArtifact(
            title=f"{stage_title} Practice",
            prompt=f"围绕 `{concept}` 写出你会如何在 {state.domain} 学习或实践中使用它。",
            expected_answer=f"回答需解释 `{concept}` 的作用，并给出一个具体应用场景。",
            rubric=[
                "解释核心概念",
                "给出具体场景",
                "说明选择原因或权衡",
            ],
            reference_code="",
            evaluation_mode="freeform",
            test_code="",
        )
        if is_python_domain:
            practice = PracticeArtifact(
                title=f"{stage_title} Async Lab",
                prompt=(
                    "实现 `async def build_tasks()`，内部使用 `asyncio.create_task` 调度 3 个协程，"
                    "最后返回 `[0, 2, 4]`。请只提交 Python 代码。"
                ),
                expected_answer="需要定义异步函数并使用 asyncio.create_task + asyncio.gather。",
                rubric=[
                    "定义 async 函数",
                    "使用 asyncio.create_task",
                    "返回预期结果 [0, 2, 4]",
                ],
                reference_code=(
                    "import asyncio\n"
                    "async def build_tasks():\n"
                    "    async def work(x):\n"
                    "        return x * 2\n"
                    "    tasks = [asyncio.create_task(work(i)) for i in range(3)]\n"
                    "    return await asyncio.gather(*tasks)\n"
                ),
                evaluation_mode="python_script",
                test_code=(
                    "import asyncio\n"
                    "result = asyncio.run(build_tasks())\n"
                    "assert result == [0, 2, 4]\n"
                    "print('ok')\n"
                ),
            )
        if self.llm and self.llm.is_available("chat"):
            try:
                payload = self.llm.complete_json(
                    system_prompt=(
                        "你是实践题设计器。请输出 JSON，字段必须是 "
                        "title, prompt, expected_answer, rubric, reference_code。"
                    ),
                    user_prompt=(
                        f"领域：{state.domain}\n"
                        f"当前概念：{concept}\n"
                        "请生成一个中文练习题，适合当前学习阶段。"
                    ),
                    profile="chat",
                )
                practice = PracticeArtifact.model_validate(payload)
                state.add_log("llm_used", "Practice generated with configured LLM provider.")
            except Exception as exc:
                state.add_log("llm_fallback", f"Practice fell back to local generator: {exc}")
        state.practice = practice
        manager.write_json_artifact(
            state.session_id,
            "labs/latest_practice.json",
            practice.model_dump(mode="json"),
        )
        state.add_log("practice_generated", f"Generated practice for stage {state.current_stage}.")
        return state

    def evaluate(self, state: LearnerState, learner_answer: str) -> LearnerState:
        state.latest_answer = learner_answer
        if state.practice is not None and state.practice.evaluation_mode == "python_script":
            user_code = self._extract_code(learner_answer)
            result = self.sandbox.run(user_code=user_code, test_code=state.practice.test_code)
            state.assessment_score = 100 if result.passed else 40
            state.latest_feedback = (
                f"代码通过测试。\n{result.stdout.strip()}".strip()
                if result.passed
                else f"代码未通过测试。\n{result.stderr.strip()}".strip()
            )
            state.add_log("practice_assessed", f"Scored learner answer at {state.assessment_score}.")
            return state

        answer = learner_answer.lower()
        score = 35
        if state.practice is not None:
            prompt = state.practice.prompt.lower()
            if any(token in answer for token in ["例", "example", "场景", "scenario"]):
                score += 20
            if any(token in answer for token in ["因为", "因此", "trade-off", "权衡", "原因"]):
                score += 20
            if any(fragment in answer for fragment in prompt.replace("`", "").split()[:3]):
                score += 20
        if len(learner_answer.strip()) > 20:
            score += 10

        state.assessment_score = min(score, 100)
        state.latest_feedback = (
            "回答已经覆盖部分关键点。"
            if state.assessment_score >= 80
            else "回答还不够具体，建议补充概念作用、场景和权衡。"
        )
        state.add_log("practice_assessed", f"Scored learner answer at {state.assessment_score}.")
        return state

    def _extract_code(self, learner_answer: str) -> str:
        stripped = learner_answer.strip()
        if "```" not in stripped:
            return stripped
        segments = stripped.split("```")
        for segment in segments:
            cleaned = segment.strip()
            if cleaned.startswith("python"):
                return cleaned[len("python") :].strip()
            if cleaned and "\n" in cleaned:
                return cleaned
        return stripped
