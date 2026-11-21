from .conftest import KEY_1, KEY_2, chat, rate_limit, server_error, settle


def count_rows(client, session):
    r = client.get(f"/sessions/{session}/messages")
    return len(r.json()["messages"]) if r.status_code == 200 else 0


def test_real_429_on_first_key_falls_over(client, provider):
    provider.failures[KEY_1] = rate_limit()
    r = chat(client, "r1")
    assert r.status_code == 200
    m = r.json()["metadata"]
    assert m["key_id"] == "key_2" and m["fallback_attempts"] == 1
    assert [c["api_key"] for c in provider.calls] == [KEY_1, KEY_2]  # a real second provider attempt


def test_real_500_on_first_key_falls_over(client, provider):
    provider.failures[KEY_1] = server_error()
    m = chat(client, "r2").json()["metadata"]
    assert m["key_id"] == "key_2" and m["fallback_attempts"] == 1


def test_all_real_keys_failing_returns_clean_503_and_stores_nothing(client, provider):
    provider.failures[KEY_1] = rate_limit()
    provider.failures[KEY_2] = server_error()
    r = chat(client, "r3")
    assert r.status_code == 503 and r.json() == {"detail": "all providers unavailable"}
    assert client.get("/sessions/r3/messages").status_code == 404


def test_failed_request_not_added_to_existing_history(client, provider):
    chat(client, "keep", "good one")
    provider.failures[KEY_1] = rate_limit(); provider.failures[KEY_2] = rate_limit()
    assert chat(client, "keep", "bad one").status_code == 503
    assert count_rows(client, "keep") == 2
    provider.failures.clear()
    assert chat(client, "keep", "good two").status_code == 200
    assert count_rows(client, "keep") == 4


def test_simulate_key1_429(client, provider):
    r = chat(client, "s1", headers={"X-Simulate-Failure": "key_1=429"})
    assert r.status_code == 200
    m = r.json()["metadata"]
    assert m["key_id"] == "key_2" and m["fallback_attempts"] == 1 and m["resolution_source"] == "LIVE_INFERENCE"
    assert r.json()["reply"] and "simulated" not in r.json()["reply"]
    assert [c["api_key"] for c in provider.calls] == [KEY_2]  # key_1 never reached the provider; key_2 really answered


def test_simulate_key1_500(client):
    m = chat(client, "s2", headers={"X-Simulate-Failure": "key_1=500"}).json()["metadata"]
    assert m["key_id"] == "key_2" and m["fallback_attempts"] == 1


def test_simulate_502_and_503(client):
    for status in (502, 503):
        m = chat(client, f"s-{status}", headers={"X-Simulate-Failure": f"key_1={status}"}).json()["metadata"]
        assert m["key_id"] == "key_2"


def test_simulate_wildcard_503_and_not_stored(client):
    r = chat(client, "w1", headers={"X-Simulate-Failure": "*=429"})
    assert r.status_code == 503 and r.json() == {"detail": "all providers unavailable"}
    assert client.get("/sessions/w1/messages").status_code == 404


def test_simulate_both_keys_listed(client):
    r = chat(client, "w2", headers={"X-Simulate-Failure": "key_1=429,key_2=500"})
    assert r.status_code == 503


def test_simulate_only_key2_means_key1_answers(client):
    m = chat(client, "w3", headers={"X-Simulate-Failure": "key_2=429"}).json()["metadata"]
    assert m["key_id"] == "key_1" and m["fallback_attempts"] == 0


def test_simulation_affects_only_current_request(client):
    chat(client, "o1", headers={"X-Simulate-Failure": "*=429"})
    m = chat(client, "o1").json()["metadata"]
    assert m["key_id"] == "key_1" and m["fallback_attempts"] == 0


def test_simulation_bypasses_cache(client, provider):
    chat(client, "b1", "warm the cache")
    settle()
    r = chat(client, "b2", "warm the cache", headers={"X-Simulate-Failure": "key_1=429"}).json()
    assert r["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert r["metadata"]["key_id"] == "key_2" and r["metadata"]["fallback_attempts"] == 1
    wild = chat(client, "b3", "warm the cache", headers={"X-Simulate-Failure": "*=429"})
    assert wild.status_code == 503  # a cached answer must NOT mask the simulated outage


def test_simulation_disabled_by_env(make_client, provider):
    c = make_client(ENABLE_FAILURE_SIMULATION="false")
    r = chat(c, "d1", headers={"X-Simulate-Failure": "*=429"})
    assert r.status_code == 200 and r.json()["metadata"]["key_id"] == "key_1"


def test_three_keys_chain(make_client, provider):
    c = make_client(LLM_API_KEYS=f"{KEY_1},{KEY_2},test-key-three")
    m = chat(c, "t1", headers={"X-Simulate-Failure": "key_1=429,key_2=503"}).json()["metadata"]
    assert m["key_id"] == "key_3" and m["fallback_attempts"] == 2


def test_malformed_failure_header_is_ignored(client):
    r = chat(client, "m1", headers={"X-Simulate-Failure": "garbage,key_1=404,=500"})
    assert r.status_code == 200 and r.json()["metadata"]["key_id"] == "key_1"


def test_provider_errors_are_logged_without_keys(client, provider, caplog):
    import logging
    provider.failures[KEY_1] = rate_limit(); provider.failures[KEY_2] = server_error()
    with caplog.at_level(logging.WARNING):
        assert chat(client, "lg").status_code == 503
    text = caplog.text
    assert "all providers failed" in text and "RateLimitError" in text or "InternalServerError" in text
    assert KEY_1 not in text and KEY_2 not in text


def test_check_keys_tool_reports_without_leaking(tmp_path, provider, monkeypatch, capsys):
    import asyncio
    from app import check_keys
    monkeypatch.setenv("LLM_API_KEYS", "test-key-one-xxxxxxxxxxxx,test-key-two-xxxxxxxxxxxx")
    monkeypatch.setenv("LLM_MODEL", "fake/test-model")
    provider.failures["test-key-one-xxxxxxxxxxxx"] = rate_limit()
    code = asyncio.run(check_keys.main())
    out = capsys.readouterr().out
    assert code == 1 and "key_1: FAILED" in out and "key_2: OK" in out
    assert "xxxxxxxxxxxx" not in out
