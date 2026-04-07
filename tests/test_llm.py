from pathlib import Path

from app.agents.instructor import InstructorAgent
from app.config import load_config
from app.llm import LLMGateway
from app.models import Curriculum, CurriculumStage, LearnerProfile, LearnerState
from app.workspace import WorkspaceManager


def test_load_config_resolves_env_refs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_SILICONFLOW_API_KEY", "secret-key")
    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: 1",
                "llm:",
                "  default_provider: siliconflow",
                "  default_profile: chat",
                "  providers:",
                "    siliconflow:",
                "      enabled: true",
                "      base_url: https://api.siliconflow.cn/v1",
                "      api_key: ${TEST_SILICONFLOW_API_KEY}",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.llm.providers["siliconflow"].api_key == "secret-key"


def test_llm_gateway_reports_unavailable_without_api_key(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: 1",
                "llm:",
                "  default_provider: siliconflow",
                "  default_profile: chat",
                "  providers:",
                "    siliconflow:",
                "      enabled: true",
                "      base_url: https://api.siliconflow.cn/v1",
                "      api_key:",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
            ]
        ),
        encoding="utf-8",
    )
    config = load_config(config_path)
    gateway = LLMGateway(config=config)

    assert gateway.is_available("chat") is False


def test_instructor_prefers_llm_output_when_gateway_available(tmp_path: Path) -> None:
    class FakeGateway:
        def is_available(self, profile: str = "chat") -> bool:
            return True

        def complete_json(self, *, system_prompt: str, user_prompt: str, profile: str = "chat") -> dict:
            return {
                "explanation": "LLM generated explanation",
                "key_takeaways": ["One", "Two", "Three"],
                "micro_quiz": {"question": "What matters?", "expected_points": ["One"]},
                "next_step": "Use the generated exercise.",
            }

    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    state.curriculum = Curriculum(
        domain=state.domain,
        stages=[
            CurriculumStage(
                stage=1,
                title="入门",
                objective="理解事件循环",
                concepts=["event loop"],
                practice_format="quiz",
                exit_criteria="能解释事件循环",
            )
        ],
    )
    manager = WorkspaceManager(root=tmp_path / ".learn")
    manager.bootstrap_session(state)

    updated = InstructorAgent(llm=FakeGateway()).run(state, manager)

    assert updated.lesson is not None
    assert updated.lesson.explanation == "LLM generated explanation"
