from app.db import get_conn, init_db, upsert_hysteresis_state
from app.entry_policy import entry_gate
from app.exits import exit_policy_v2


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


def test_hysteresis_requires_two_unless_shock_override() -> None:
    _reset()
    decision = {
        "rec": "BUY",
        "signal_score": 0.75,
        "prob_outperform_90d": 0.60,
        "key_risks": [],
    }
    first = entry_gate(
        ticker="AAPL",
        decision=decision,
        avg_vol_20d=5_000_000,
        avg_close_20d=10,
        market_cap=3_000_000_000,
        shock_score=0.2,
    )
    second = entry_gate(
        ticker="AAPL",
        decision=decision,
        avg_vol_20d=5_000_000,
        avg_close_20d=10,
        market_cap=3_000_000_000,
        shock_score=0.2,
    )
    override = entry_gate(
        ticker="MSFT",
        decision=decision,
        avg_vol_20d=5_000_000,
        avg_close_20d=10,
        market_cap=3_000_000_000,
        shock_score=0.8,
    )
    assert first.action == "NO_TRADE"
    assert second.action == "BUY"
    assert override.action == "BUY"


def test_strong_buy_gate_is_stricter_and_hard_veto_blocks() -> None:
    _reset()
    strict_fail = entry_gate(
        ticker="NVDA",
        decision={
            "rec": "STRONG_BUY",
            "signal_score": 0.79,
            "prob_outperform_90d": 0.61,
            "key_risks": [],
        },
        avg_vol_20d=5_000_000,
        avg_close_20d=10,
        market_cap=3_000_000_000,
        shock_score=0.1,
    )
    veto = entry_gate(
        ticker="TSLA",
        decision={
            "rec": "BUY",
            "signal_score": 0.90,
            "prob_outperform_90d": 0.90,
            "key_risks": ["Potential fraud investigation"],
        },
        avg_vol_20d=5_000_000,
        avg_close_20d=10,
        market_cap=3_000_000_000,
        shock_score=0.9,
    )
    assert strict_fail.action == "NO_TRADE"
    assert "signal" in strict_fail.reason or "hysteresis" in strict_fail.reason
    assert veto.action == "NO_TRADE"
    assert veto.reason == "hard_veto"


def test_exit_policy_downgrade_streak_and_profit_partial() -> None:
    _reset()
    upsert_hysteresis_state("META", consecutive_ok=2, peak_price=100.0, downgrade_streak=0)
    first = exit_policy_v2("META", current_price=101.5, prev_close=100.0, atr_14d=1.0, signal_score=0.65)
    second = exit_policy_v2("META", current_price=100.0, prev_close=100.0, atr_14d=1.0, signal_score=0.65)
    assert first.action == "SELL_PARTIAL"
    assert second.action == "SELL_ALL"
