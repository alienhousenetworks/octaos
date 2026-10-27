"""Release gate: Alembic graph must have a single resolvable head."""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_graph_has_one_resolvable_head():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    # Forces Alembic to resolve every revision and catches missing parents / duplicate IDs.
    assert scripts.get_heads()
    assert len(scripts.get_heads()) == 1
