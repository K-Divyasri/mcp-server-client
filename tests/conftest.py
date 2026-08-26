import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(coro):
    """Run an async test body without pulling in pytest-asyncio."""
    return asyncio.run(coro)


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "notes.db")


@pytest.fixture
def seeded_conn(temp_db_path):
    from mcp_kb import db

    conn = db.connect(temp_db_path, seed=True)
    yield conn
    conn.close()


@pytest.fixture
def server_env(temp_db_path):
    """Environment dict for spawning the real MCP server subprocess against
    a throwaway, seeded database."""
    env = dict(os.environ)
    env["MCP_KB_DB_PATH"] = temp_db_path
    return env
