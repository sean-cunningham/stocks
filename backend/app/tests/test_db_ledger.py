from app.db import derive_active_positions, get_conn, init_db, insert_trade


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


def test_positions_derived_from_ledger() -> None:
    _reset()
    insert_trade("AAPL", "BUY", 10, 100, 0, "eh", "dh")
    insert_trade("AAPL", "BUY", 5, 120, 0, "eh", "dh")
    insert_trade("AAPL", "SELL", 8, 130, 0, "eh", "dh")
    insert_trade("MSFT", "BUY", 2, 300, 0, "eh", "dh")
    insert_trade("MSFT", "SELL", 2, 305, 0, "eh", "dh")

    positions = sorted(derive_active_positions(), key=lambda x: x["ticker"])
    assert len(positions) == 1
    assert positions[0]["ticker"] == "AAPL"
    assert abs(positions[0]["net_qty"] - 7.0) < 1e-9
    assert positions[0]["avg_cost"] > 0
