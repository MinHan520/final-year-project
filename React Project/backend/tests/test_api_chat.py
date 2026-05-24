import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_empty_message():
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 200
    assert res.json() == {"reply": "Please provide a message.", "used_scan_id": None}

def test_chat_no_project_id(monkeypatch):
    monkeypatch.setattr("app.config.Settings.gcp_project_id", "")
    res = client.post("/api/chat", json={"message": "Hello"})
    assert res.status_code == 200
    reply = res.json()["reply"]
    assert "Thanks for the message" in reply or "Hi! I'm TruthLens" in reply

def test_chat_invalid_scan_id():
    res = client.post("/api/chat", json={"scan_id": "missing_id", "message": "Hello"})
    assert res.status_code == 200
    assert res.json()["used_scan_id"] == "missing_id"
