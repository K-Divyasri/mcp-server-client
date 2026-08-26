"""Live Claude test -- skipped automatically when ANTHROPIC_API_KEY is unset
so the rest of the suite (and CI) never needs a key."""

import pytest

from mcp_kb.agent import Agent
from mcp_kb.bridge import MCPToolBridge
from mcp_kb.llm import has_api_key

from conftest import run

pytestmark = pytest.mark.skipif(not has_api_key(), reason="requires ANTHROPIC_API_KEY")


def test_real_agent_answers_weather_question(temp_db_path):
    async def _inner():
        async with MCPToolBridge(transport="stdio", db_path=temp_db_path) as bridge:
            agent = Agent(bridge, real=True)
            return await agent.run("What's the weather like in Paris right now?")

    result = run(_inner())
    assert result.real
    assert any(s.tool == "get_weather" for s in result.steps)
    assert "Paris" in result.answer or "paris" in result.answer.lower()
