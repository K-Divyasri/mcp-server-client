"""Real MCP protocol round-trips over stdio -- a live subprocess, real
JSON-RPC framing, no mocking of the protocol layer at all. The only thing
ever faked in this project is the LLM decision; MCP itself is cheap enough
to just run for real, every time."""

from mcp_kb.bridge import MCPToolBridge

from conftest import run


def test_list_tools_matches_anthropic_shape(temp_db_path):
    async def _inner():
        async with MCPToolBridge(transport="stdio", db_path=temp_db_path) as bridge:
            return await bridge.list_tools_for_llm()

    tools = run(_inner())
    names = {t["name"] for t in tools}
    assert names == {"search_notes", "add_note", "list_tags", "get_weather"}
    for t in tools:
        assert "input_schema" in t
        assert t["input_schema"]["type"] == "object"


def test_call_tool_search(temp_db_path):
    async def _inner():
        async with MCPToolBridge(transport="stdio", db_path=temp_db_path) as bridge:
            return await bridge.call_tool("search_notes", {"query": "python", "limit": 5})

    output = run(_inner())
    assert not output.is_error
    assert len(output.parts) >= 1
    assert "python" in output.text.lower()


def test_call_tool_error_surfaces(temp_db_path):
    async def _inner():
        async with MCPToolBridge(transport="stdio", db_path=temp_db_path) as bridge:
            # get_note is not exposed as a tool; note_resource requires an int-able id
            return await bridge.call_tool("get_weather", {})  # missing required 'city'

    output = run(_inner())
    assert output.is_error


def test_resources_and_prompts(temp_db_path):
    async def _inner():
        async with MCPToolBridge(transport="stdio", db_path=temp_db_path) as bridge:
            resources = await bridge.list_resources()
            summary = await bridge.read_resource("notebook://summary")
            prompts = await bridge.list_prompts()
            prompt_text = await bridge.get_prompt("research_prompt", {"topic": "baking"})
            return resources, summary, prompts, prompt_text

    resources, summary, prompts, prompt_text = run(_inner())
    assert any(r["uri"] == "notebook://summary" for r in resources)
    assert "notes" in summary
    assert prompts[0]["name"] == "research_prompt"
    assert "baking" in prompt_text


def test_bridge_rejects_bad_transport():
    import pytest

    with pytest.raises(ValueError):
        MCPToolBridge(transport="carrier-pigeon")


def test_bridge_requires_http_url_for_http():
    import pytest

    with pytest.raises(ValueError):
        MCPToolBridge(transport="http")
