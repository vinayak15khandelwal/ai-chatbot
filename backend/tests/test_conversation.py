import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app

from .conftest import chat, make_settings


def test_multi_turn_sends_full_history_to_llm(client, provider):
    chat(client, "s1", "my name is Ada")
    r = chat(client, "s1", "what is my name?")
    assert r.status_code == 200
    sent = provider.calls[-1]["messages"]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]
    assert sent[1]["content"] == "my name is Ada" and sent[3]["content"] == "what is my name?"
    assert "my name is Ada" in r.json()["reply"]


def test_input_tokens_cover_system_history_and_message(client):
    first = chat(client, "a", "hello there").json()["metadata"]["input_tokens"]
    second = chat(client, "a", "hello again").json()["metadata"]["input_tokens"]
    assert second > first  # per-request prompt grows with history, but is not a running total of both


def test_session_isolation(client, provider):
    chat(client, "A", "secret apple")
    chat(client, "B", "banana")
    sent = provider.calls[-1]["messages"]
    assert all("apple" not in m["content"] for m in sent)
    a = client.get("/sessions/A/messages").json()["messages"]
    b = client.get("/sessions/B/messages").json()["messages"]
    assert [m["content"] for m in a if m["role"] == "user"] == ["secret apple"]
    assert [m["content"] for m in b if m["role"] == "user"] == ["banana"]


def test_history_endpoint_shape_and_order(client):
    chat(client, "h", "one")
    chat(client, "h", "two")
    body = client.get("/sessions/h/messages").json()
    assert body["session_id"] == "h"
    msgs = body["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert [m["content"] for m in msgs if m["role"] == "user"] == ["one", "two"]
    assert "metadata" not in msgs[0]
    meta = msgs[1]["metadata"]
    assert meta["resolution_source"] == "LIVE_INFERENCE" and meta["input_tokens"] > 0 and meta["output_tokens"] > 0
    assert not any(m["role"] == "system" for m in msgs)


def test_system_prompt_is_used_but_not_returned(client, provider):
    chat(client, "sp", "hi", system_prompt="You are a pirate.")
    chat(client, "sp", "again")  # no prompt: session keeps the one it was given
    assert provider.calls[-1]["messages"][0] == {"role": "system", "content": "You are a pirate."}
    assert all("pirate" not in m["content"] for m in client.get("/sessions/sp/messages").json()["messages"])


def test_unknown_session_404(client):
    r = client.get("/sessions/does-not-exist/messages")
    assert r.status_code == 404 and r.json() == {"detail": "session not found"}


def test_sqlite_persistence_across_restart(tmp_path, provider):
    c1 = TestClient(create_app(make_settings(tmp_path)))
    with c1:
        chat(c1, "persist", "remember me")
    c2 = TestClient(create_app(make_settings(tmp_path)))  # "restarted" app, same database file
    with c2:
        msgs = c2.get("/sessions/persist/messages").json()["messages"]
    assert [m["content"] for m in msgs][0] == "remember me" and len(msgs) == 2
    row = sqlite3.connect(tmp_path / "app.db").execute(
        "SELECT role, created_at, metadata FROM messages ORDER BY id").fetchall()
    assert row[0][0] == "user" and row[0][2] is None
    assert row[1][0] == "assistant" and '"input_tokens"' in row[1][2]
    assert "T" in row[0][1]  # ISO-8601
