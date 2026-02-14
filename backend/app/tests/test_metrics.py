from datetime import date, timedelta

from app.config import settings
from app.db import get_conn, init_db, insert_trade
from app.metrics import (
    METRICS_LOOKBACK_DAYS,
    PriceProvider,
    compute_metrics,
    _compute_win_rate_fifo,
    _replay_trades_through_date,
    _parse_ts_date,
)


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


def _stub_provider(constant: float = 100.0) -> PriceProvider:
    def provider(ticker: str, start_iso: str, end_iso: str) -> dict[str, float]:
        out = {}
        start = date.fromisoformat(start_iso)
        end = date.fromisoformat(end_iso)
        d = start
        while d <= end:
            out[d.isoformat()] = constant
            d += timedelta(days=1)
        return out

    return provider


def test_equity_curve_length_and_sharpe_dd_no_crash() -> None:
    _reset()
    insert_trade("AAPL", "BUY", 10, 100, 0, "eh", "dh")
    result = compute_metrics(price_provider=_stub_provider(100.0))
    assert len(result["equity_curve"]) > 1
    assert "sharpe" in result
    assert "max_drawdown" in result
    assert "win_rate" in result
    sharpe = result["sharpe"]
    max_dd = result["max_drawdown"]
    assert isinstance(sharpe, (int, float))
    assert isinstance(max_dd, (int, float))
    assert result["equity_curve"][0]["date"] <= result["equity_curve"][-1]["date"]


def test_metrics_no_trades_returns_single_point() -> None:
    _reset()
    result = compute_metrics(price_provider=_stub_provider())
    assert len(result["equity_curve"]) == 1
    assert result["equity_curve"][0]["value"] == settings.paper_portfolio_usd
    assert result["sharpe"] == 0.0
    assert result["max_drawdown"] == 0.0
    assert result["win_rate"] == 0.0


def test_replay_trades_through_date() -> None:
    trades = [
        {"ticker": "AAPL", "side": "BUY", "qty": 10, "price": 100, "fees": 0, "ts_utc": "2025-01-01T12:00:00Z"},
        {"ticker": "AAPL", "side": "SELL", "qty": 5, "price": 110, "fees": 0, "ts_utc": "2025-01-02T12:00:00Z"},
    ]
    cash, pos = _replay_trades_through_date(trades, "2025-01-01", 100_000.0)
    assert cash == 100_000.0 - 10 * 100 - 0
    assert pos.get("AAPL") == 10
    cash2, pos2 = _replay_trades_through_date(trades, "2025-01-02", 100_000.0)
    assert pos2.get("AAPL") == 5
    assert cash2 == 100_000.0 - 1000 + 5 * 110


def test_parse_ts_date() -> None:
    assert _parse_ts_date("2025-02-01T14:30:00Z") == "2025-02-01"
    assert _parse_ts_date("2025-02-01") == "2025-02-01"


def test_win_rate_fifo() -> None:
    trades_win = [
        {"ticker": "A", "side": "BUY", "qty": 10, "price": 100, "fees": 0},
        {"ticker": "A", "side": "SELL", "qty": 10, "price": 110, "fees": 0},
    ]
    for t in trades_win:
        t["ts_utc"] = "2025-01-01T00:00:00Z"
    wr = _compute_win_rate_fifo(trades_win)
    assert wr == 1.0
    trades_lose = [
        {"ticker": "B", "side": "BUY", "qty": 10, "price": 100, "fees": 0},
        {"ticker": "B", "side": "SELL", "qty": 10, "price": 90, "fees": 0},
    ]
    for t in trades_lose:
        t["ts_utc"] = "2025-01-01T00:00:00Z"
    wr2 = _compute_win_rate_fifo(trades_lose)
    assert wr2 == 0.0
    combined = trades_win + trades_lose
    wr3 = _compute_win_rate_fifo(combined)
    assert wr3 == 0.5


def test_metrics_lookback_config() -> None:
    assert METRICS_LOOKBACK_DAYS == 90
