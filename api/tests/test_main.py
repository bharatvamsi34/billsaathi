from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


def test_health(monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc1234")
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["git_sha"] == "abc1234"
    assert set(body) == {"status", "version", "git_sha", "env"}  # nothing else leaks
