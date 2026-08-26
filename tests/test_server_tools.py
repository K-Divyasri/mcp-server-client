"""Exercise the @mcp.tool()-decorated functions directly, no protocol
involved -- these decorators don't change what the function IS, just
register it. server._connect() reads MCP_KB_DB_PATH at call time, so
monkeypatching the env var per test is enough; no need to reimport."""

import pytest

from mcp_kb import server


@pytest.fixture(autouse=True)
def _seeded_db(monkeypatch, temp_db_path):
    monkeypatch.setenv("MCP_KB_DB_PATH", temp_db_path)
    yield


def test_search_notes_tool():
    results = server.search_notes("python", limit=3)
    assert len(results) >= 2
    assert all("id" in r and "title" in r for r in results)


def test_add_note_tool_then_search():
    added = server.add_note("Rust ownership", "borrow checker basics", "rust,programming")
    assert added["title"] == "Rust ownership"
    results = server.search_notes("rust")
    assert any(r["id"] == added["id"] for r in results)


def test_list_tags_tool():
    tags = server.list_tags()
    assert "python" in tags
    assert tags == sorted(tags)


def test_get_weather_tool_offline():
    assert "offline demo data" in server.get_weather("Tokyo")


def test_note_resource_found_and_missing():
    added = server.add_note("Resource test", "body", "")
    text = server.note_resource(str(added["id"]))
    assert "Resource test" in text
    missing = server.note_resource("999999")
    assert "No note with id" in missing


def test_notebook_summary_resource():
    text = server.notebook_summary()
    assert "notes" in text
    assert "tags" in text


def test_research_prompt():
    text = server.research_prompt("baking")
    assert "baking" in text
