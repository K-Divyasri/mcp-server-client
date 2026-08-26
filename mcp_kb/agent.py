"""The agent loop: reason (pick a tool) -> act (call it over real MCP) ->
observe (feed the result back) -> repeat until there's an answer.

Offline mode (`real=False`, the default) uses FakeRouter and stops after
one tool call. Real mode (`real=True`) hands the MCP-discovered tool list
straight to Claude and loops until the model stops asking for tools --
the manual agentic loop pattern from shared/tool-use-concepts.md, just with
`execute_tool` replaced by an MCP `call_tool`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from mcp_kb.bridge import MCPToolBridge
from mcp_kb.llm import DEFAULT_MODEL, FakeRouter, call_claude, has_api_key


@dataclass
class Step:
    tool: str
    arguments: dict
    result: str


@dataclass
class AgentResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    real: bool = False
    stopped_early: bool = False


def _compose_offline_answer(tool_name: str, output_parts: list[str]) -> str:
    if tool_name == "search_notes":
        if not output_parts:
            return "No matching notes found."
        titles = []
        for part in output_parts:
            try:
                titles.append(json.loads(part)["title"])
            except (json.JSONDecodeError, KeyError):
                titles.append(part[:40])
        return "Found these notes: " + "; ".join(titles)
    if tool_name == "get_weather":
        return output_parts[0] if output_parts else "No weather data."
    if tool_name == "list_tags":
        return "Your tags: " + ", ".join(output_parts) if output_parts else "No tags yet."
    if tool_name == "add_note":
        return "Saved a new note." if output_parts else "Could not save the note."
    return "\n".join(output_parts)


class Agent:
    def __init__(self, bridge: MCPToolBridge, *, real: bool = False, model: str | None = None, max_steps: int = 4):
        self.bridge = bridge
        self.real = real
        self.model = model or DEFAULT_MODEL
        self.max_steps = max_steps
        self.router = FakeRouter()

    async def run(self, question: str) -> AgentResult:
        tools = await self.bridge.list_tools_for_llm()
        if self.real and has_api_key():
            return await self._run_real(question, tools)
        return await self._run_offline(question, tools)

    async def _run_offline(self, question: str, tools: list[dict]) -> AgentResult:
        tool_names = [t["name"] for t in tools]
        decision = self.router.decide(question, tool_names)
        if decision.tool_name is None:
            return AgentResult(answer=decision.final_answer or "(no answer)", real=False)
        output = await self.bridge.call_tool(decision.tool_name, decision.arguments)
        step = Step(decision.tool_name, decision.arguments, output.text)
        answer = _compose_offline_answer(decision.tool_name, output.parts)
        return AgentResult(answer=answer, steps=[step], real=False)

    async def _run_real(self, question: str, tools: list[dict]) -> AgentResult:
        messages: list[dict] = [{"role": "user", "content": question}]
        steps: list[Step] = []
        for _ in range(self.max_steps):
            response = call_claude(self.model, messages, tools)
            messages.append({"role": "assistant", "content": response.content})

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                text = next((b.text for b in response.content if b.type == "text"), "")
                return AgentResult(answer=text, steps=steps, real=True)

            tool_results = []
            for tu in tool_uses:
                output = await self.bridge.call_tool(tu.name, tu.input)
                steps.append(Step(tu.name, dict(tu.input), output.text))
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": output.text or "(empty result)",
                        "is_error": output.is_error,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        return AgentResult(answer="(stopped: too many tool-call rounds)", steps=steps, real=True, stopped_early=True)
