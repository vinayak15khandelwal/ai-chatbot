from .conftest import chat


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "keys_configured": 2, "cache_enabled": True}


def test_health_degraded_with_one_key(make_client):
    c = make_client(LLM_API_KEYS="only-one")
    r = c.get("/health")
    assert r.status_code == 503 and r.json()["keys_configured"] == 1


def test_valid_chat_contract(client):
    r = chat(client, "s-7f3a")
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "s-7f3a" and body["reply"]
    m = body["metadata"]
    assert m["resolution_source"] == "LIVE_INFERENCE"
    assert m["model"] == "fake/test-model"
    assert isinstance(m["latency_ms"], int) and m["latency_ms"] > 0
    assert m["input_tokens"] > 0 and m["output_tokens"] > 0
    assert m["key_id"] == "key_1" and m["fallback_attempts"] == 0


def test_missing_session_id(client):
    assert client.post("/chat", json={"message": "hi"}).status_code == 422


def test_empty_session_id(client):
    assert chat(client, session="").status_code == 422


def test_session_id_too_long(client):
    assert chat(client, session="x" * 129).status_code == 422


def test_missing_message(client):
    assert client.post("/chat", json={"session_id": "a"}).status_code == 422


def test_empty_and_whitespace_message(client):
    assert chat(client, message="").status_code == 422
    assert chat(client, message="    \n ").status_code == 422


def test_message_too_long(client):
    assert chat(client, message="a" * 4001).status_code == 422
    assert chat(client, message="a" * 4000).status_code == 200


def test_malformed_json_is_json_422(client):
    r = client.post("/chat", content="{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_unknown_route_is_json(client):
    r = client.get("/nope")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}


def test_cors_allows_configured_origin(client):
    r = client.options(
        "/chat",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "content-type,x-simulate-failure"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    bad = client.options("/chat", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers
