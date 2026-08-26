"""The MCP server: exposes PersonalKB (notes + weather) over the Model
Context Protocol.

Run it two ways:
    python -m mcp_kb.server            # stdio transport (Claude Desktop, local clients)
    python -m mcp_kb.server --http     # streamable-http transport (remote clients)

Everything in here is a thin wrapper around mcp_kb.db and mcp_kb.weather --
the MCP layer's only job is translating between the protocol and plain
Python functions. That split is deliberate: it's what makes db.py and
weather.py testable with zero protocol overhead.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from mcp_kb import db, weather

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = str(DATA_DIR / "notes.db")


def _db_path() -> str:
    return os.environ.get("MCP_KB_DB_PATH", DEFAULT_DB_PATH)


def _connect():
    path = _db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return db.connect(path, seed=True)


mcp = FastMCP(
    "PersonalKB",
    host=os.environ.get("MCP_KB_HTTP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_KB_HTTP_PORT", "8765")),
)


@mcp.tool()
def search_notes(query: str, limit: int = 5) -> list[dict]:
    """Search notes by keyword across title, body, and tags. Returns the
    best matches ranked by relevance, most relevant first."""
    conn = _connect()
    try:
        return [n.to_dict() for n in db.search_notes(conn, query, limit=limit)]
    finally:
        conn.close()


@mcp.tool()
def add_note(title: str, body: str, tags: str = "") -> dict:
    """Add a new note. `tags` is a comma-separated string, e.g. 'python,work'."""
    conn = _connect()
    try:
        note = db.add_note(conn, title, body, tags)
        return note.to_dict()
    finally:
        conn.close()


@mcp.tool()
def list_tags() -> list[str]:
    """List every tag currently used across all notes, alphabetically."""
    conn = _connect()
    try:
        return db.list_tags(conn)
    finally:
        conn.close()


@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city. Uses live open-meteo.com data
    when the server was started with MCP_KB_LIVE_WEATHER=1, otherwise
    returns offline demo data for a handful of well-known cities."""
    return weather.get_weather(city)


@mcp.resource("note://{note_id}")
def note_resource(note_id: str) -> str:
    """The full text of one note, addressed by its numeric id."""
    conn = _connect()
    try:
        note = db.get_note(conn, int(note_id))
        if note is None:
            return f"No note with id {note_id}."
        tags = ", ".join(note.tags) if note.tags else "(none)"
        return f"# {note.title}\n\n{note.body}\n\nTags: {tags}\nCreated: {note.created_at}"
    finally:
        conn.close()


@mcp.resource("notebook://summary")
def notebook_summary() -> str:
    """Notebook-wide stats: how many notes, how many tags, the latest note."""
    conn = _connect()
    try:
        s = db.stats(conn)
        return (
            f"{s['note_count']} notes, {s['tag_count']} tags. "
            f"Latest: {s['latest_note']!r} ({s['latest_created_at']})."
        )
    finally:
        conn.close()


@mcp.prompt()
def research_prompt(topic: str) -> str:
    """A reusable prompt template: search notes on a topic and summarize
    what's found, citing which notes were used."""
    return (
        f"Search my notes for everything about '{topic}'. "
        "Then write a 2-3 sentence summary of what you found, "
        "citing the title of each note you used."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PersonalKB MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve over streamable-http instead of stdio",
    )
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
