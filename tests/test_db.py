from mcp_kb import db


def test_seed_count(seeded_conn):
    s = db.stats(seeded_conn)
    assert s["note_count"] == len(db.SEED_NOTES)
    assert s["tag_count"] > 0


def test_seed_is_idempotent(temp_db_path):
    conn = db.connect(temp_db_path, seed=True)
    conn2 = db.connect(temp_db_path, seed=True)
    assert db.stats(conn2)["note_count"] == len(db.SEED_NOTES)
    conn.close()
    conn2.close()


def test_search_finds_python_notes(seeded_conn):
    results = db.search_notes(seeded_conn, "python", limit=10)
    titles = {n.title for n in results}
    assert "Python decorator cheat sheet" in titles
    assert "Reticulated python at the zoo" in titles


def test_search_respects_limit(seeded_conn):
    results = db.search_notes(seeded_conn, "python programming sqlite work", limit=2)
    assert len(results) <= 2


def test_search_empty_query_returns_nothing(seeded_conn):
    assert db.search_notes(seeded_conn, "") == []


def test_search_no_match(seeded_conn):
    assert db.search_notes(seeded_conn, "xyznonexistentword") == []


def test_add_note_then_find_it(seeded_conn):
    note = db.add_note(seeded_conn, "Kubernetes notes", "pods and services", ["k8s", "devops"])
    assert note.id is not None
    results = db.search_notes(seeded_conn, "kubernetes")
    assert any(n.id == note.id for n in results)


def test_add_note_accepts_comma_string_tags(seeded_conn):
    note = db.add_note(seeded_conn, "t", "b", "a, b ,c")
    assert note.tags == ["a", "b", "c"]


def test_list_tags_sorted_and_deduped(seeded_conn):
    tags = db.list_tags(seeded_conn)
    assert tags == sorted(set(tags))
    assert "python" in tags


def test_get_note_missing_returns_none(seeded_conn):
    assert db.get_note(seeded_conn, 999999) is None


def test_get_note_round_trip(seeded_conn):
    note = db.add_note(seeded_conn, "Round trip", "body text", ["x"])
    fetched = db.get_note(seeded_conn, note.id)
    assert fetched.title == "Round trip"
    assert fetched.tags == ["x"]
