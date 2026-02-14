from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_db_path_default_stable() -> None:
    assert settings.db_path == "stocks.db"
    assert "backend/" not in settings.db_path


def test_news_router_reused_across_requests() -> None:
    with TestClient(app) as client:
        client.get("/api/analyze/AAPL")
        router_first = client.app.state.news_router
        client.get("/api/analyze/AAPL")
        router_second = client.app.state.news_router
        assert router_first is router_second
