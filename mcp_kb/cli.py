"""Command-line entry point: `python -m mcp_kb <command>`."""

from __future__ import annotations

import argparse
import asyncio
import sys

from mcp_kb.agent import Agent
from mcp_kb.bridge import MCPToolBridge


def _build_bridge(args: argparse.Namespace) -> MCPToolBridge:
    return MCPToolBridge(
        transport=args.transport,
        http_url=getattr(args, "http_url", None),
        live_weather=getattr(args, "live_weather", False),
    )


async def _cmd_tools(args: argparse.Namespace) -> int:
    async with _build_bridge(args) as bridge:
        tools = await bridge.list_tools_for_llm()
        resources = await bridge.list_resources()
        prompts = await bridge.list_prompts()
    print(f"Tools ({len(tools)}):")
    for t in tools:
        print(f"  - {t['name']}: {t['description']}")
    print(f"Resources ({len(resources)}):")
    for r in resources:
        print(f"  - {r['uri']}: {r['description']}")
    print(f"Prompts ({len(prompts)}):")
    for p in prompts:
        print(f"  - {p['name']}: {p['description']}")
    return 0


async def _cmd_ask(args: argparse.Namespace) -> int:
    async with _build_bridge(args) as bridge:
        agent = Agent(bridge, real=args.real, model=args.model, max_steps=args.max_steps)
        result = await agent.run(args.question)
    print(f"answer ({'real' if result.real else 'offline'}):")
    print(result.answer)
    if args.verbose:
        print("\ntrace:")
        for i, step in enumerate(result.steps, start=1):
            print(f"  [{i}] {step.tool}({step.arguments}) -> {step.result[:200]}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from mcp_kb import server

    sys.argv = ["mcp_kb.server"] + (["--http"] if args.http else [])
    server.main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp_kb", description="PersonalKB MCP server + client")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    common.add_argument("--http-url", default="http://127.0.0.1:8765/mcp")
    common.add_argument("--live-weather", action="store_true", help="Use real open-meteo.com data")

    p_tools = sub.add_parser("tools", parents=[common], help="List tools/resources/prompts the server exposes")
    p_tools.set_defaults(func=_cmd_tools, is_async=True)

    p_ask = sub.add_parser("ask", parents=[common], help="Ask a question; the agent picks a tool via MCP")
    p_ask.add_argument("question")
    p_ask.add_argument("--real", action="store_true", help="Use the real Claude API instead of the offline router")
    p_ask.add_argument("--model", default=None)
    p_ask.add_argument("--max-steps", type=int, default=4)
    p_ask.add_argument("--verbose", action="store_true")
    p_ask.set_defaults(func=_cmd_ask, is_async=True)

    p_serve = sub.add_parser("serve", help="Run the MCP server directly (blocks)")
    p_serve.add_argument("--http", action="store_true")
    p_serve.set_defaults(func=_cmd_serve, is_async=False)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.is_async:
        return asyncio.run(args.func(args))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
