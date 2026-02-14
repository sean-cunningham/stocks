import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    db_file = Path(settings.db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trades(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts_utc TEXT NOT NULL,
              ticker TEXT NOT NULL,
              side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
              qty REAL NOT NULL,
              price REAL NOT NULL,
              fees REAL NOT NULL DEFAULT 0.0,
              strategy_id TEXT,
              model_version TEXT,
              note TEXT,
              evidence_hash TEXT NOT NULL,
              decision_hash TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts_utc TEXT NOT NULL,
              event_type TEXT NOT NULL,
              ticker TEXT,
              evidence_hash TEXT,
              decision_hash TEXT,
              payload_json TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS hysteresis_state(
              ticker TEXT PRIMARY KEY,
              consecutive_ok INTEGER NOT NULL DEFAULT 0,
              last_ts_utc TEXT NOT NULL,
              peak_price REAL DEFAULT NULL,
              downgrade_streak INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_ticker_ts ON trades(ticker, ts_utc)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_ticker_event_ts ON audit_log(ticker, event_type, ts_utc)")
        conn.commit()
    finally:
        conn.close()


def insert_audit_log(
    event_type: str,
    payload: dict[str, Any],
    ticker: str | None = None,
    evidence_hash: str | None = None,
    decision_hash: str | None = None,
) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO audit_log(ts_utc, event_type, ticker, evidence_hash, decision_hash, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (_utc_now_iso(), event_type, ticker, evidence_hash, decision_hash, json.dumps(payload)),
        )
        conn.commit()
    finally:
        conn.close()


def insert_trade(
    ticker: str,
    side: str,
    qty: float,
    price: float,
    fees: float,
    evidence_hash: str,
    decision_hash: str,
    strategy_id: str | None = None,
    model_version: str | None = None,
    note: str | None = None,
) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO trades(
              ts_utc, ticker, side, qty, price, fees, strategy_id, model_version, note, evidence_hash, decision_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now_iso(),
                ticker.upper(),
                side,
                qty,
                price,
                fees,
                strategy_id,
                model_version,
                note,
                evidence_hash,
                decision_hash,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_hysteresis_state(ticker: str) -> dict[str, Any]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT ticker, consecutive_ok, last_ts_utc, peak_price, downgrade_streak FROM hysteresis_state WHERE ticker=?",
            (ticker.upper(),),
        ).fetchone()
        if row:
            return dict(row)
        return {
            "ticker": ticker.upper(),
            "consecutive_ok": 0,
            "last_ts_utc": _utc_now_iso(),
            "peak_price": None,
            "downgrade_streak": 0,
        }
    finally:
        conn.close()


def upsert_hysteresis_state(
    ticker: str,
    consecutive_ok: int | None = None,
    peak_price: float | None = None,
    downgrade_streak: int | None = None,
) -> None:
    current = get_hysteresis_state(ticker)
    new_consecutive = current["consecutive_ok"] if consecutive_ok is None else consecutive_ok
    new_peak = current["peak_price"] if peak_price is None else peak_price
    new_downgrade = current["downgrade_streak"] if downgrade_streak is None else downgrade_streak
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO hysteresis_state(ticker, consecutive_ok, last_ts_utc, peak_price, downgrade_streak)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
              consecutive_ok=excluded.consecutive_ok,
              last_ts_utc=excluded.last_ts_utc,
              peak_price=excluded.peak_price,
              downgrade_streak=excluded.downgrade_streak
            """,
            (ticker.upper(), new_consecutive, _utc_now_iso(), new_peak, new_downgrade),
        )
        conn.commit()
    finally:
        conn.close()


def derive_active_positions() -> list[dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT ticker,
                   SUM(CASE WHEN side='BUY' THEN qty ELSE -qty END) AS net_qty,
                   SUM(CASE WHEN side='BUY' THEN qty*price+fees ELSE 0 END) AS gross_buy_cost,
                   SUM(CASE WHEN side='BUY' THEN qty ELSE 0 END) AS gross_buy_qty
            FROM trades
            GROUP BY ticker
            HAVING net_qty > 0
            """
        ).fetchall()
        positions: list[dict[str, Any]] = []
        for row in rows:
            avg_cost = (row["gross_buy_cost"] / row["gross_buy_qty"]) if row["gross_buy_qty"] else 0.0
            positions.append(
                {
                    "ticker": row["ticker"],
                    "net_qty": float(row["net_qty"]),
                    "avg_cost": float(avg_cost),
                }
            )
        return positions
    finally:
        conn.close()


def most_recent_decision_hashes(ticker: str) -> tuple[str | None, str | None]:
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT evidence_hash, decision_hash
            FROM audit_log
            WHERE ticker=? AND event_type='DECISION'
            ORDER BY id DESC
            LIMIT 1
            """,
            (ticker.upper(),),
        ).fetchone()
        if not row:
            return None, None
        return row["evidence_hash"], row["decision_hash"]
    finally:
        conn.close()


def most_recent_decision_payload(ticker: str, since_iso: str) -> dict[str, Any] | None:
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT payload_json
            FROM audit_log
            WHERE ticker=? AND event_type='DECISION' AND ts_utc >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (ticker.upper(), since_iso),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])
    finally:
        conn.close()


def list_trades() -> list[dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM trades ORDER BY ts_utc ASC, id ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
