from __future__ import annotations

from app.knowledge import KnowledgeService
from app.models import Curriculum, CurriculumStage, DomainMeta, LearnerState
from app.workspace import WorkspaceManager


class CurriculumArchitectAgent:
    def analyze_domain(self, domain: str) -> DomainMeta:
        lowered = domain.lower()
        if any(keyword in lowered for keyword in ["python", "rust", "前端", "javascript", "async"]):
            return DomainMeta(
                type="technical",
                pedagogy="project_driven",
                core_primitives=["fundamentals", "execution_model", "patterns", "debugging"],
                assessment_style="code_execution + reflective_review",
                difficulty_curve="exponential_then_plateau",
            )
        return DomainMeta(
            type="knowledge",
            pedagogy="case_based",
            core_primitives=["concepts", "frameworks", "analysis", "application"],
            assessment_style="structured_response",
            difficulty_curve="gradual",
        )

    def build_curriculum(self, domain: str, meta: DomainMeta, focus_keywords: list[str] | None = None) -> Curriculum:
        focus_keywords = focus_keywords or []
        stage_one_concepts = [meta.core_primitives[0], "mental model", "key terms"]
        stage_two_concepts = [meta.core_primitives[1], "workflow", "trade-offs"]
        stage_three_concepts = [meta.core_primitives[2], "applied patterns", "decision making"]
        if focus_keywords:
            if focus_keywords[0] not in stage_one_concepts:
                stage_one_concepts.insert(0, focus_keywords[0])
            for keyword in focus_keywords[1:3]:
                if keyword not in stage_two_concepts:
                    stage_two_concepts.insert(0, keyword)
            for keyword in focus_keywords[3:4]:
                if keyword not in stage_three_concepts:
                    stage_three_concepts.insert(0, keyword)

        stages = [
            CurriculumStage(
                stage=1,
                title="入门地图",
                objective=f"建立 {domain} 的整体认知和关键术语地图。",
                concepts=stage_one_concepts,
                practice_format="micro_quiz",
                exit_criteria="能用自己的话解释领域目标和关键组成部分",
            ),
            CurriculumStage(
                stage=2,
                title="核心机制",
                objective=f"掌握 {domain} 的核心机制和基本流程。",
                concepts=stage_two_concepts,
                practice_format="guided_exercise",
                exit_criteria="能解释关键机制如何运作并识别常见误区",
            ),
            CurriculumStage(
                stage=3,
                title="模式应用",
                objective=f"把 {domain} 的概念用于中等复杂度任务。",
                concepts=stage_three_concepts,
                practice_format="scenario_lab",
                exit_criteria="能在给定场景中选出合适的方法并说明原因",
            ),
            CurriculumStage(
                stage=4,
                title="诊断优化",
                objective=f"识别 {domain} 中的常见失败模式并做出优化。",
                concepts=[meta.core_primitives[3], "debugging", "performance"],
                practice_format="diagnostic_lab",
                exit_criteria="能定位问题并提出改进方案",
            ),
            CurriculumStage(
                stage=5,
                title="综合实战",
                objective=f"完成一个关于 {domain} 的综合项目或案例复盘。",
                concepts=["capstone", "architecture", "communication"],
                practice_format="capstone",
                exit_criteria="能独立完成综合任务并给出结构化复盘",
            ),
        ]
        return Curriculum(domain=domain, stages=stages)

    def run(self, state: LearnerState, manager: WorkspaceManager) -> LearnerState:
        if state.domain_meta is None:
            state.domain_meta = self.analyze_domain(state.domain)
            manager.write_domain_meta(state.session_id, state.domain_meta)
        if state.curriculum is None:
            focus_keywords = KnowledgeService(manager).extract_focus_keywords(state.session_id)
            state.curriculum = self.build_curriculum(state.domain, state.domain_meta, focus_keywords=focus_keywords)
            manager.write_curriculum(state.session_id, state.curriculum)
            state.add_log("curriculum_built", f"Curriculum built for {state.domain}.")
        return state
