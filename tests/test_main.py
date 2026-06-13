"""Tests for the main FastAPI application."""

from fastapi.testclient import TestClient

from src.backend.app.main import app

client = TestClient(app)


def test_home():
    """Test the home endpoint returns a welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to NextGen Bank - FastAPI!"}
