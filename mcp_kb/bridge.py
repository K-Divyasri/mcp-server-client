"""MCPToolBridge: the one place that speaks the Model Context Protocol.

Everything above this module (the agent, the CLI) only ever sees plain
Python: dicts, strings, lists. This is deliberate -- it's the same "backend
behind an interface" shape as every other project on this track, except
here the interface itself IS the point of the project.

Two transports are supported, matching the roadmap spec's "stdio + HTTP"
requirement:
  - stdio: spawns `python -m mcp_kb.server` as a child process and talks
    over its stdin/stdout. This is what Claude Desktop uses for local tools.
  - http: connects to an already-running `python -m mcp_kb.server --http`
    over Streamable HTTP. This is what you'd use for a server that lives on
    another machine.
"""

from __future__ import annotations

import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


@dataclass
class CallToolOutput:
    parts: list[str] = field(default_factory=list)
    is_error: bool = False

    @property
    def text(self) -> str:
        """Every part joined -- good enough when you just want to show a
        human (or feed an LLM) the raw tool output."""
        return "\n".join(self.parts)


class MCPToolBridge:
    """Async context manager wrapping one MCP client session."""

    def __init__(
        self,
        transport: str = "stdio",
        *,
        http_url: str | None = None,
        db_path: str | None = None,
        live_weather: bool = False,
    ) -> None:
        if transport not in ("stdio", "http"):
            raise ValueError(f"unknown transport {transport!r}, expected 'stdio' or 'http'")
        if transport == "http" and not http_url:
            raise ValueError("http_url is required when transport='http'")
        self.transport = transport
        self.http_url = http_url
        self.db_path = db_path
        self.live_weather = live_weather
        self._stack: AsyncExitStack | None = None
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "MCPToolBridge":
        self._stack = AsyncExitStack()
        if self.transport == "stdio":
            env = dict(os.environ)
            if self.db_path:
                env["MCP_KB_DB_PATH"] = self.db_path
            if self.live_weather:
                env["MCP_KB_LIVE_WEATHER"] = "1"
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_kb.server"],
                env=env,
            )
            read, write = await self._stack.enter_async_context(stdio_client(params))
        else:
            read, write, _get_session_id = await self._stack.enter_async_context(
                streamablehttp_client(self.http_url)
            )
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc_info) -> None:
        assert self._stack is not None
        await self._stack.aclose()
        self.session = None

    async def list_tools_for_llm(self) -> list[dict]:
        """Discovered tools, already shaped as Anthropic `tools=[...]`
        entries. MCP's `inputSchema` and Anthropic's `input_schema` are both
        plain JSON Schema -- there's no translation to write, just a
        rename."""
        assert self.session is not None
        result = await self.session.list_tools()
        return [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
            for t in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict) -> CallToolOutput:
        assert self.session is not None
        result = await self.session.call_tool(name, arguments)
        parts = [block.text for block in result.content if hasattr(block, "text")]
        return CallToolOutput(parts=parts, is_error=bool(result.isError))

    async def list_resources(self) -> list[dict]:
        assert self.session is not None
        result = await self.session.list_resources()
        return [{"uri": str(r.uri), "name": r.name, "description": r.description} for r in result.resources]

    async def read_resource(self, uri: str) -> str:
        assert self.session is not None
        result = await self.session.read_resource(uri)
        return "\n".join(c.text for c in result.contents if hasattr(c, "text"))

    async def list_prompts(self) -> list[dict]:
        assert self.session is not None
        result = await self.session.list_prompts()
        return [{"name": p.name, "description": p.description} for p in result.prompts]

    async def get_prompt(self, name: str, arguments: dict | None = None) -> str:
        assert self.session is not None
        result = await self.session.get_prompt(name, arguments or {})
        texts = []
        for message in result.messages:
            content = message.content
            if hasattr(content, "text"):
                texts.append(content.text)
        return "\n".join(texts)
