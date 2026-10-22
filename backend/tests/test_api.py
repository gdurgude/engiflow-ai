from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r=client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'

def test_unauthenticated_projects_blocked():
    assert client.get('/projects').status_code == 401

def test_homepage_available():
    assert client.get('/').status_code == 200
