from __future__ import annotations

from app.knowledge import KnowledgeService
from app.llm import LLMGateway
from app.models import KnowledgeItem, LearnerState
from app.workspace import WorkspaceManager


class ResearcherAgent:
    def __init__(self, llm: LLMGateway | None = None) -> None:
        self.llm = llm

    def run(self, state: LearnerState, manager: WorkspaceManager) -> LearnerState:
        if state.knowledge_items:
            return state

        knowledge = [
            KnowledgeItem(
                title=f"{state.domain} overview",
                summary=f"{state.domain} 关注核心概念、实践路径和常见误区。",
                source="local://domain-overview",
                confidence=0.75,
            ),
            KnowledgeItem(
                title=f"{state.domain} learning path",
                summary="从基础概念、执行机制、模式应用到综合项目逐步推进。",
                source="local://learning-path",
                confidence=0.8,
            ),
        ]
        service = KnowledgeService(manager)
        uploaded_chunks = service.list_chunks(state.session_id)
        for chunk in uploaded_chunks[:3]:
            knowledge.append(
                KnowledgeItem(
                    title=chunk.title,
                    summary=chunk.content[:180],
                    source=chunk.source,
                    confidence=0.9,
                )
            )
        if self.llm and self.llm.is_available("chat"):
            try:
                payload = self.llm.complete_json(
                    system_prompt=(
                        "你是研究助理。请输出 JSON，包含 items 数组，"
                        "每个元素有 title, summary, source, confidence。"
                    ),
                    user_prompt=f"请为领域 `{state.domain}` 生成 2 条高层知识摘要，面向学习规划。",
                    profile="chat",
                )
                items = payload.get("items", [])
                parsed = [KnowledgeItem.model_validate(item) for item in items]
                if parsed:
                    knowledge = parsed[:3] + knowledge[2:]
                    state.add_log("llm_used", "Researcher generated knowledge with configured LLM provider.")
            except Exception as exc:
                state.add_log("llm_fallback", f"Researcher fell back to local generator: {exc}")
        state.knowledge_items = knowledge
        manager.write_json_artifact(
            state.session_id,
            "knowledge/indexed/knowledge.json",
            [item.model_dump(mode="json") for item in knowledge],
        )
        state.add_log("knowledge_indexed", f"Indexed {len(knowledge)} local knowledge items.")
        return state
