# MCP Server + Client

PersonalKB: a real Model Context Protocol (MCP) server, notes search plus a live
weather lookup, and a client/agent that talks to it. The MCP protocol layer is
never mocked: every test spawns a real server subprocess and does real JSON-RPC
over it, either over stdio or over real HTTP. The only thing ever faked offline
is the LLM's own tool-choice decision; no API key is needed to run anything here
except the final `--real` flag.

**Problem:** Wiring a model up to tools with a hand-rolled JSON blob works until
you need a second client, a remote server, or someone else's tools. MCP is
Anthropic's open standard for how a model discovers and calls tools, reads
resources, and uses prompt templates over a real wire protocol instead. This
project builds a real server against that protocol, from the decorators up
through a working client bridge and agent loop.

**Skills demonstrated:** building an MCP server (tools, resources, prompts) with
FastMCP, both stdio and streamable-HTTP transports, a client bridge that
discovers tools live over the protocol, an offline deterministic tool router and
a real agentic loop against the Claude API, SQLite full-text search (FTS5), and
pytest against real protocol traffic (no mocking).

**Tech stack:** Python 3.10+, the `mcp` SDK (FastMCP), SQLite (standard
library), the Anthropic SDK for the real agent path, `requests` for live
weather (Open-Meteo), pytest.

## What it exposes

Running `mcp_kb.server` starts an MCP server, **PersonalKB**, over notes stored
in SQLite with full-text search:

- **Tools**: `search_notes(query, limit)`, `add_note(title, body, tags)`,
  `list_tags()`, `get_weather(city)`.
- **Resources**: `note://{note_id}` (fetch one note), `notebook://summary` (a
  summary of the whole notebook).
- **Prompt**: `research_prompt(topic)`, a reusable prompt template.

## Run it

```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python generate_data.py           # seeds data/notes.db with 15 hand-written notes

python -m mcp_kb tools                                  # list tools/resources/prompts
python -m mcp_kb ask "find notes about python"
python -m mcp_kb ask "what's the weather in Paris"
python -m mcp_kb serve                                  # run the server directly (stdio)
python -m mcp_kb serve --http                            # or over streamable-HTTP

pytest -q                          # the full suite, all real protocol traffic, no key needed
```

`ask` spawns the real server, discovers its tools live over MCP, and answers
your question with an offline deterministic router by default, or the real
Claude API with `--real` (needs `ANTHROPIC_API_KEY` in `.env`).

## How it fits together

```
mcp_kb/
├── db.py         SQLite + FTS5 notes store: search, add, tags
├── weather.py     an offline table, or real keyless Open-Meteo data with --live-weather
├── server.py      the actual MCP server (FastMCP-based): tools, resources, a prompt
├── bridge.py       the MCP client wrapper: discovers tools/resources/prompts live
├── llm.py         the offline deterministic tool-choice router
├── agent.py        the agentic loop: offline router, or a real Claude tool-use loop
└── cli.py           python -m mcp_kb tools|ask|serve
tests/                41 tests, all real protocol traffic (stdio and HTTP), no mocking
```

The design choice that matters: `server.py` is a thin wrapper around `db.py` and
`weather.py`; the MCP layer's only job is translating between the protocol and
plain Python functions. That split is what makes the underlying logic testable
with zero protocol overhead, while the protocol layer itself is still exercised
for real in every test.

## Connecting a real MCP client

The same server also runs as-is inside the real Claude Desktop app: point its
MCP config at `python -m mcp_kb serve`, and it can search your notes or check
the weather in a normal chat, calling the exact tools defined in `server.py`.
See `hosting/HOSTING_GUIDE.md` for the connection steps and for deploying the
HTTP transport somewhere a remote client could reach it.

## What I learned

- MCP separates *what a tool does* from *how a client finds and calls it*: the
  server declares tools, resources, and prompts once, and any compliant client
  (a hand-rolled bridge, or Claude Desktop) can discover and use them without
  custom glue.
- Keeping the protocol layer thin and pushing logic into plain, testable Python
  functions is what let the test suite run real client/server traffic without
  it being slow or brittle.
- stdio and streamable-HTTP are just two transports under the same protocol;
  the tools, resources, and prompts a server exposes don't change based on how
  a client reaches it.
