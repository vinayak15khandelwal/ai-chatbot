from .conftest import chat, settle


def test_miss_then_hit_identical_reply_and_tokens(client, provider):
    first = chat(client, "c1", "What is the capital of France?").json()
    settle()
    second = chat(client, "c2", "What is the capital of France?").json()  # NEW session, same message
    assert first["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    m = second["metadata"]
    assert m["resolution_source"] == "LLM_CACHE"
    assert second["reply"] == first["reply"]
    assert m["input_tokens"] == first["metadata"]["input_tokens"]
    assert m["output_tokens"] == first["metadata"]["output_tokens"]
    assert m["key_id"] is None and m["fallback_attempts"] == 0
    assert len(provider.calls) == 1  # provider really was not called again


def test_cache_hit_is_faster_than_live(client):
    live = chat(client, "f1", "latency probe").json()["metadata"]["latency_ms"]
    settle()
    hit = chat(client, "f2", "latency probe").json()["metadata"]["latency_ms"]
    assert hit < live


def test_different_message_never_hits_cache(client, provider):
    a = chat(client, "d1", "alpha question").json()
    settle()
    b = chat(client, "d2", "beta question").json()
    assert b["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert b["reply"] != a["reply"]


def test_history_is_part_of_cache_identity(client):
    chat(client, "x1", "first A")
    chat(client, "x2", "first B")
    settle()
    # Same second message but different history -> different message list -> must not be a cache hit.
    r1 = chat(client, "x1", "follow up").json()
    r2 = chat(client, "x2", "follow up").json()
    assert r1["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert r2["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert r1["reply"] != r2["reply"]


def test_system_prompt_is_part_of_cache_identity(client):
    chat(client, "p1", "same text", system_prompt="Be brief.")
    settle()
    r = chat(client, "p2", "same text", system_prompt="Be verbose.").json()
    assert r["metadata"]["resolution_source"] == "LIVE_INFERENCE"


def test_cache_hit_stored_in_history_with_cache_metadata(client):
    chat(client, "h1", "cache me")
    settle()
    chat(client, "h2", "cache me")
    meta = client.get("/sessions/h2/messages").json()["messages"][1]["metadata"]
    assert meta["resolution_source"] == "LLM_CACHE"


def test_cache_can_be_disabled(make_client, provider):
    c = make_client(CACHE_ENABLED="false")
    assert c.get("/health").json()["cache_enabled"] is False
    chat(c, "n1", "no cache"); settle(); chat(c, "n2", "no cache")
    assert len(provider.calls) == 2
