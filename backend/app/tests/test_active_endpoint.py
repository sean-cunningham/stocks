from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db import get_conn, init_db, insert_trade
from app.main import app


def _reset() -> None:
    init_db()
    conn = get_conn()
    try:
        conn.execute("DELETE FROM trades")
        conn.execute("DELETE FROM audit_log")
        conn.execute("DELETE FROM hysteresis_state")
        conn.commit()
    finally:
        conn.close()


def test_active_without_recent_decision_populates_decision_and_no_false_sell_trigger() -> None:
    with TestClient(app) as client:
        _reset()
        insert_trade("AAPL", "BUY", 1, 100, 0, "eh", "dh")
        r = client.get("/api/portfolio/active")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    pos = data[0]
    assert pos["ticker"] == "AAPL"
    assert pos["last_decision"] is not None
    assert "rec" in pos["last_decision"]
    assert "signal_score" in pos["last_decision"]
    assert "prob_outperform_90d" in pos["last_decision"]
    assert pos["sell_reason"] != "downgrade_streak_trigger"
    assert pos["sell_trigger"] is False


def test_active_analyze_failure_returns_no_recent_decision() -> None:
    with TestClient(app) as client:
        _reset()
        insert_trade("AAPL", "BUY", 1, 100, 0, "eh", "dh")
        with patch("app.main.analyze", side_effect=Exception("mock analyze failure")):
            r = client.get("/api/portfolio/active")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    pos = data[0]
    assert pos["ticker"] == "AAPL"
    assert pos["last_decision"] is None
    assert pos["sell_trigger"] is False
    assert pos["sell_reason"] == "no_recent_decision"
