import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_project():
    response = client.post("/create_project", params={"name": "مشروع اختبار", "location": "القاهرة"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "مشروع اختبار"

def test_get_projects():
    response = client.get("/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)