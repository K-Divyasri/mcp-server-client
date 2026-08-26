"""Real end-to-end Streamable HTTP: spawn `python -m mcp_kb.server --http`
as a subprocess, wait for it to come up, talk to it over real HTTP, then
tear it down. Same "actually run it" discipline as the stdio tests -- no
mocked transport."""

import contextlib
import socket
import subprocess
import sys
import time

import pytest

from mcp_kb.bridge import MCPToolBridge

from conftest import run


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with contextlib.suppress(OSError):
            with socket.create_connection((host, port), timeout=0.5):
                return
        time.sleep(0.2)
    raise TimeoutError(f"server on {host}:{port} did not start in time")


@pytest.fixture
def http_server(server_env):
    port = _free_port()
    server_env = dict(server_env)
    server_env["MCP_KB_HTTP_PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_kb.server", "--http"],
        env=server_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_until_up("127.0.0.1", port)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_http_transport_list_and_call(http_server):
    async def _inner():
        async with MCPToolBridge(transport="http", http_url=http_server) as bridge:
            tools = await bridge.list_tools_for_llm()
            output = await bridge.call_tool("get_weather", {"city": "Sydney"})
            return tools, output

    tools, output = run(_inner())
    names = {t["name"] for t in tools}
    assert "get_weather" in names
    assert "Sydney" in output.text
