from pathlib import Path


def test_alembic_assets_exist_for_session_store_schema() -> None:
    alembic_ini = Path("alembic.ini")
    env_py = Path("alembic/env.py")
    versions_dir = Path("alembic/versions")

    assert alembic_ini.exists()
    assert env_py.exists()
    assert versions_dir.exists()

    env_text = env_py.read_text(encoding="utf-8")
    assert "LEARN_NEW_POSTGRES_DSN" in env_text
    assert "target_metadata" in env_text

    migration_files = sorted(versions_dir.glob("*.py"))
    assert migration_files
    migration_text = migration_files[0].read_text(encoding="utf-8")
    assert "sessions" in migration_text
    assert "checkpoints" in migration_text
    assert "owner_id" in migration_text
    assert "updated_at" in migration_text
    combined_migrations = "\n".join(path.read_text(encoding="utf-8") for path in migration_files)
    assert "task_queue" in combined_migrations
    assert "attempt_count" in combined_migrations
    assert "lease_owner" in combined_migrations
    assert "lease_expires_at" in combined_migrations


def test_migrate_script_invokes_alembic_upgrade_head() -> None:
    migrate_script = Path("scripts/migrate.ps1").read_text(encoding="utf-8")

    assert "alembic upgrade head" in migrate_script
    assert "LEARN_NEW_POSTGRES_DSN" in migrate_script
