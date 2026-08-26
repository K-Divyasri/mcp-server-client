"""SQLite-backed notes store with FTS5 keyword search.

Every MCP tool that touches "the database" goes through this module. It has
no MCP dependency at all -- you can `import mcp_kb.db` and use it from plain
Python, a notebook, or a pytest file with zero protocol overhead. The MCP
server in server.py is a thin wrapper around these functions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Note:
    id: int
    title: str
    body: str
    tags: list[str]
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "tags": self.tags,
            "created_at": self.created_at,
        }


SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title, body, tags, note_id UNINDEXED
);
"""

# Hand-written seed notes (no Faker) -- deliberately spans a few topics with
# some shared vocabulary ("python" shows up in both a code note and a pet
# note) so search relevance actually has to do work.
SEED_NOTES: list[tuple[str, str, list[str]]] = [
    (
        "Python decorator cheat sheet",
        "A decorator is a function that wraps another function. "
        "functools.wraps preserves the original name and docstring. "
        "Use @staticmethod and @classmethod inside a class body.",
        ["python", "programming"],
    ),
    (
        "SQLite FTS5 notes",
        "FTS5 is SQLite's full text search extension. Use bm25() to rank "
        "matches, MATCH for querying, and a virtual table for the index. "
        "It ships built in, no extra install needed on most Python builds.",
        ["python", "sqlite", "programming"],
    ),
    (
        "Reticulated python at the zoo",
        "Saw a reticulated python at the reptile house. Handler said it "
        "was about 4 meters long and eats once every two weeks.",
        ["travel", "animals"],
    ),
    (
        "Weekend bread recipe",
        "200g starter, 500g bread flour, 350g water, 10g salt. Autolyse "
        "30 minutes, then four sets of stretch and folds, bulk ferment "
        "overnight in the fridge.",
        ["recipe", "baking"],
    ),
    (
        "Tomato sauce base",
        "Saute onion and garlic in olive oil, add crushed tomatoes, a "
        "pinch of sugar, salt, and simmer 40 minutes. Finish with basil.",
        ["recipe", "cooking"],
    ),
    (
        "Kyoto trip itinerary",
        "Day 1: Fushimi Inari at sunrise before the crowds. Day 2: "
        "Arashiyama bamboo grove and the monkey park. Day 3: tea ceremony "
        "in Uji.",
        ["travel", "japan"],
    ),
    (
        "Paris weekend notes",
        "The Musee d'Orsay is far less crowded than the Louvre and has "
        "the best impressionist collection. Book the catacombs in advance.",
        ["travel", "france"],
    ),
    (
        "Book: Project Hail Mary",
        "First-person amnesia hook, likable alien-contact arc, and the "
        "chemistry-problem-solving pacing carries the middle third.",
        ["books", "scifi"],
    ),
    (
        "Book: The Pragmatic Programmer",
        "Core idea: DRY, orthogonality, and tracer bullets over big design "
        "up front. Holds up well even for the AI-tooling era.",
        ["books", "programming"],
    ),
    (
        "1:1 with Sam - roadmap",
        "Agreed to slip the Q3 roadmap by two weeks to fit the security "
        "review. Sam will own the migration doc, I own the rollout plan.",
        ["work", "meetings"],
    ),
    (
        "Standup notes - sprint 14",
        "Blocked on the staging database migration. Unblocked after "
        "restarting the connection pool; root cause was a leaked cursor.",
        ["work", "meetings", "sqlite"],
    ),
    (
        "Houseplant watering schedule",
        "Pothos and snake plant: once every 10 days. Fiddle leaf fig: "
        "once a week, rotate a quarter turn each time for even light.",
        ["home", "plants"],
    ),
    (
        "MCP protocol primitives",
        "Tools are actions a model can call. Resources are readable data "
        "the model (or a human) can fetch by URI. Prompts are reusable "
        "templates a client can surface as a slash command.",
        ["mcp", "programming"],
    ),
    (
        "Why stdio for local MCP servers",
        "stdio transport runs the server as a child process and talks "
        "over stdin/stdout -- no port to open, no auth to configure. "
        "Streamable HTTP is for servers that live on another machine.",
        ["mcp", "programming"],
    ),
    (
        "Marathon training week 6",
        "Long run 18km at an easy pace, felt strong on the last 5km. "
        "Legs still tired from the hill repeats on Tuesday.",
        ["fitness"],
    ),
]


def connect(path: str = ":memory:", *, seed: bool = False) -> sqlite3.Connection:
    """Open (and create if needed) the notes database at `path`.

    `seed=True` inserts SEED_NOTES, but only into a database with zero
    existing notes -- calling it again on an already-populated file is a
    harmless no-op, so it's safe to call on every server startup.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    if seed:
        count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        if count == 0:
            for title, body, tags in SEED_NOTES:
                add_note(conn, title, body, tags)
    return conn


def _row_to_note(row: sqlite3.Row) -> Note:
    tags = [t for t in row["tags"].split(",") if t]
    return Note(id=row["id"], title=row["title"], body=row["body"], tags=tags, created_at=row["created_at"])


def add_note(conn: sqlite3.Connection, title: str, body: str, tags: list[str] | str) -> Note:
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tags_str = ",".join(tags)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO notes (title, body, tags, created_at) VALUES (?, ?, ?, ?)",
        (title, body, tags_str, created_at),
    )
    note_id = cur.lastrowid
    conn.execute(
        "INSERT INTO notes_fts (title, body, tags, note_id) VALUES (?, ?, ?, ?)",
        (title, body, tags_str, note_id),
    )
    conn.commit()
    return Note(id=note_id, title=title, body=body, tags=tags, created_at=created_at)


def get_note(conn: sqlite3.Connection, note_id: int) -> Note | None:
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    return _row_to_note(row) if row else None


def search_notes(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[Note]:
    """Rank matches by FTS5's bm25() score (lower/more-negative = better)."""
    if not query.strip():
        return []
    # FTS5 query syntax treats bare tokens as AND by default; wrap each
    # word so punctuation in a user's question can't break the MATCH parse.
    tokens = [t for t in query.replace('"', " ").split() if t]
    if not tokens:
        return []
    match_expr = " OR ".join(f'"{t}"' for t in tokens)
    rows = conn.execute(
        """
        SELECT notes.*, bm25(notes_fts) AS score
        FROM notes_fts
        JOIN notes ON notes.id = notes_fts.note_id
        WHERE notes_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (match_expr, limit),
    ).fetchall()
    return [_row_to_note(r) for r in rows]


def list_tags(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT tags FROM notes").fetchall()
    tags: set[str] = set()
    for row in rows:
        tags.update(t for t in row["tags"].split(",") if t)
    return sorted(tags)


def stats(conn: sqlite3.Connection) -> dict:
    count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    latest = conn.execute("SELECT title, created_at FROM notes ORDER BY id DESC LIMIT 1").fetchone()
    return {
        "note_count": count,
        "tag_count": len(list_tags(conn)),
        "latest_note": latest["title"] if latest else None,
        "latest_created_at": latest["created_at"] if latest else None,
    }
