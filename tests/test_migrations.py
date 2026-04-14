from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_core_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'alembic.sqlite3'}"
    repo_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(repo_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(repo_root / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert {
        "user_profiles",
        "paper_profiles",
        "progress_events",
        "signal_snapshots",
        "subscription_policies",
        "pulse_jobs",
        "pulse_cards",
        "delivery_jobs",
    }.issubset(table_names)
    pulse_card_columns = {column["name"] for column in inspector.get_columns("pulse_cards")}
    assert {
        "source_paper_id",
        "score_total",
        "score_breakdown",
        "candidate_metadata",
    }.issubset(pulse_card_columns)
