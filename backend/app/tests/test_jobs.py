from app.db import get_conn, init_db, insert_trade
from app.jobs import create_scheduler, run_broad_job, run_reserve_job


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


def _stub_analyzer(ticker: str, _router, _ttl: int):
    evidence = {
        "avg_vol_20d": 5_000_000.0,
        "avg_close_20d": 10.0,
        "market_cap": 5_000_000_000.0,
        "shock_score": 0.75 if ticker == "AAPL" else 0.2,
        "today_hits": 4,
        "baseline_7d": 3.0,
        "macro_relevance": 0.5,
    }
    decision = {
        "rec": "BUY",
        "signal_score": 0.8,
        "prob_outperform_90d": 0.7,
        "key_risks": [],
    }
    return evidence, decision


def test_scheduler_jobs_write_audit_rows() -> None:
    _reset()
    insert_trade("AAPL", "BUY", 1, 100, 0, "eh", "dh")

    scheduler = create_scheduler()
    assert len(scheduler.get_jobs()) == 2

    run_reserve_job(router=None, analyzer=_stub_analyzer)
    run_broad_job(router=None, analyzer=_stub_analyzer)

    conn = get_conn()
    try:
        rows = conn.execute("SELECT event_type, payload_json FROM audit_log ORDER BY id ASC").fetchall()
    finally:
        conn.close()

    assert len(rows) >= 2
    job_rows = [r for r in rows if r["event_type"] == "JOB"]
    assert len(job_rows) >= 2
