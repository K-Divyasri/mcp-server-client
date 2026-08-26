from mcp_kb.agent import Agent
from mcp_kb.bridge import MCPToolBridge
from mcp_kb.llm import FakeRouter

from conftest import run


def _ask(question: str, db_path: str):
    async def _inner():
        async with MCPToolBridge(transport="stdio", db_path=db_path) as bridge:
            agent = Agent(bridge, real=False)
            return await agent.run(question)

    return run(_inner())


def test_weather_question_routes_to_weather_tool(temp_db_path):
    result = _ask("what's the weather in Paris?", temp_db_path)
    assert not result.real
    assert result.steps[0].tool == "get_weather"
    assert "Paris" in result.answer


def test_search_question_routes_to_search_tool(temp_db_path):
    result = _ask("find notes about python", temp_db_path)
    assert result.steps[0].tool == "search_notes"
    assert "Python decorator cheat sheet" in result.answer or "python" in result.answer.lower()


def test_tags_question_routes_to_list_tags(temp_db_path):
    result = _ask("what tags do I have", temp_db_path)
    assert result.steps[0].tool == "list_tags"
    assert "python" in result.answer


def test_router_is_deterministic():
    router = FakeRouter()
    names = ["search_notes", "add_note", "list_tags", "get_weather"]
    d1 = router.decide("weather in oslo", names)
    d2 = router.decide("weather in oslo", names)
    assert d1.tool_name == d2.tool_name == "get_weather"
    assert d1.arguments == d2.arguments


def test_router_falls_back_when_no_matching_tool():
    router = FakeRouter()
    decision = router.decide("what's the weather in Oslo", ["search_notes"])
    # no get_weather tool available -- must not hallucinate a call to it
    assert decision.tool_name in ("search_notes", None)
