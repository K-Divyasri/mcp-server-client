"""Create data/notes.db with the seeded PersonalKB notes. Safe to re-run --
add_note is only called when the database is empty."""

from pathlib import Path

from mcp_kb import db

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "notes.db"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect(str(DB_PATH), seed=True)
    s = db.stats(conn)
    conn.close()
    print(f"{DB_PATH}: {s['note_count']} notes, {s['tag_count']} tags")


if __name__ == "__main__":
    main()
