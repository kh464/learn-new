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
