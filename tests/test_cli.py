import pytest

from mcp_kb.cli import main


def test_tools_command(temp_db_path, monkeypatch, capsys):
    monkeypatch.setenv("MCP_KB_DB_PATH", temp_db_path)
    rc = main(["tools"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "search_notes" in out
    assert "notebook://summary" in out


def test_ask_command_offline(temp_db_path, monkeypatch, capsys):
    monkeypatch.setenv("MCP_KB_DB_PATH", temp_db_path)
    rc = main(["ask", "what's the weather in Tokyo", "--verbose"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "offline" in out
    assert "Tokyo" in out
    assert "get_weather" in out


def test_ask_command_rejects_bad_transport(temp_db_path, monkeypatch):
    monkeypatch.setenv("MCP_KB_DB_PATH", temp_db_path)
    with pytest.raises(SystemExit):
        main(["ask", "hi", "--transport", "carrier-pigeon"])
