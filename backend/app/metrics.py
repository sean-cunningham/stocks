from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

import yfinance as yf

from app.config import METRICS_LOOKBACK_DAYS, settings
from app.db import insert_audit_log, list_trades

# (ticker, start_date_iso, end_date_iso) -> {date_iso: close_price}
PriceProvider = Callable[[str, str, str], dict[str, float]]


def _parse_ts_date(ts_utc: str) -> str:
    return ts_utc[:10] if ts_utc else ""


def _yfinance_closes(
    ticker: str,
    start_iso: str,
    end_iso: str,
    trades: list[dict[str, Any]],
) -> dict[str, float]:
    try:
        start_d = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).date()
        end_d = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).date()
        data = yf.download(
            ticker,
            start=start_d,
            end=end_d + timedelta(days=1),
            progress=False,
            auto_adjust=True,
            group_by=None,
        )
        if data is None or data.empty:
            raise ValueError("empty data")
        out: dict[str, float] = {}
        close_name = "Adj Close" if "Adj Close" in data.columns else "Close"
        if hasattr(data.columns, "levels"):
            close_series = data[close_name].iloc[:, 0]
        else:
            close_series = data[close_name]
        for ts in close_series.index:
            d = ts.date() if hasattr(ts, "date") else ts
            out[d.isoformat()] = float(close_series.loc[ts])
        return out
    except Exception as exc:
        insert_audit_log(
            event_type="ERROR",
            ticker=ticker,
            payload={
                "error": str(exc),
                "context": "metrics_yfinance_closes",
                "start": start_iso,
                "end": end_iso,
            },
        )
        fallback = 0.0
        for t in reversed(trades):
            if t["ticker"] == ticker and _parse_ts_date(t["ts_utc"]) <= end_iso:
                fallback = float(t["price"])
                break
        out = {}
        start_d = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).date()
        end_d = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).date()
        d = start_d
        while d <= end_d:
            out[d.isoformat()] = fallback
            d += timedelta(days=1)
        return out


def _default_price_provider(
    trades: list[dict[str, Any]],
) -> PriceProvider:
    def provider(ticker: str, start_iso: str, end_iso: str) -> dict[str, float]:
        return _yfinance_closes(ticker, start_iso, end_iso, trades)

    return provider


def _replay_trades_through_date(
    trades: list[dict[str, Any]],
    through_date_iso: str,
    initial_cash: float,
) -> tuple[float, dict[str, float]]:
    cash = initial_cash
    position_qty: dict[str, float] = {}
    for t in trades:
        ts_date = _parse_ts_date(t["ts_utc"])
        if ts_date > through_date_iso:
            continue
        ticker = t["ticker"]
        qty = float(t["qty"])
        price = float(t["price"])
        fees = float(t["fees"])
        side = t["side"]
        if side == "BUY":
            cash -= qty * price + fees
            position_qty[ticker] = position_qty.get(ticker, 0.0) + qty
        else:
            cash += qty * price - fees
            position_qty[ticker] = position_qty.get(ticker, 0.0) - qty
    return cash, position_qty


def _forward_fill_closes(dates_sorted: list[str], closes: dict[str, float]) -> dict[str, float]:
    result: dict[str, float] = {}
    last = 0.0
    for d in dates_sorted:
        last = closes.get(d, last)
        result[d] = last
    return result


def _compute_win_rate_fifo(trades: list[dict[str, Any]]) -> float:
    # FIFO per ticker: list of (qty, price, fees) for buys; match sells to them
    buys: dict[str, list[tuple[float, float, float]]] = {}
    wins = 0
    total_closed = 0
    for t in trades:
        ticker = t["ticker"]
        qty = float(t["qty"])
        price = float(t["price"])
        fees = float(t["fees"])
        side = t["side"]
        if side == "BUY":
            buys.setdefault(ticker, []).append((qty, price, fees))
        else:
            remaining = qty
            sell_price = price
            sell_fees = fees
            buy_cost = 0.0
            buy_fees = 0.0
            while remaining > 0 and ticker in buys and buys[ticker]:
                bq, bp, bf = buys[ticker][0]
                take = min(remaining, bq)
                buy_cost += take * bp
                buy_fees += bf * (take / bq) if bq else 0
                remaining -= take
                if bq <= take:
                    buys[ticker].pop(0)
                else:
                    buys[ticker][0] = (bq - take, bp, bf * (1 - take / bq))
            if remaining < qty:
                realized_qty = qty - remaining
                pnl = realized_qty * sell_price - buy_cost - sell_fees - buy_fees
                total_closed += 1
                if pnl > 0:
                    wins += 1
    return (wins / total_closed) if total_closed else 0.0


def compute_metrics(
    price_provider: PriceProvider | None = None,
) -> dict[str, Any]:
    trades = list_trades()
    end_d = datetime.now(timezone.utc).date()
    start_d = end_d - timedelta(days=METRICS_LOOKBACK_DAYS)
    start_iso = start_d.isoformat()
    end_iso = end_d.isoformat()

    dates_sorted: list[str] = []
    d = start_d
    while d <= end_d:
        dates_sorted.append(d.isoformat())
        d += timedelta(days=1)

    if not trades:
        return {
            "equity_curve": [{"date": end_iso, "value": settings.paper_portfolio_usd}],
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
        }

    get_closes = price_provider or _default_price_provider(trades)
    tickers = list({t["ticker"] for t in trades})
    closes_by_ticker: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        raw = get_closes(ticker, start_iso, end_iso)
        closes_by_ticker[ticker] = _forward_fill_closes(dates_sorted, raw)

    equity_curve: list[dict[str, Any]] = []
    for day_iso in dates_sorted:
        cash, position_qty = _replay_trades_through_date(
            trades, day_iso, settings.paper_portfolio_usd
        )
        total = cash
        for ticker, qty in position_qty.items():
            if qty <= 0:
                continue
            close = closes_by_ticker.get(ticker, {}).get(day_iso, 0.0)
            total += qty * close
        equity_curve.append({"date": day_iso, "value": round(total, 2)})

    equity_values = [p["value"] for p in equity_curve]
    if len(equity_values) < 2:
        sharpe = 0.0
    else:
        returns = []
        for i in range(1, len(equity_values)):
            prev = equity_values[i - 1]
            cur = equity_values[i]
            if prev and prev > 0:
                returns.append((cur - prev) / prev)
            else:
                returns.append(0.0)
        if len(returns) < 2:
            sharpe = 0.0
        else:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
            std = variance ** 0.5
            if std == 0:
                sharpe = 0.0
            else:
                sharpe = (mean_ret / std) * (252 ** 0.5)

    peak = equity_values[0] if equity_values else 0
    max_dd = 0.0
    for v in equity_values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

    win_rate = _compute_win_rate_fifo(trades)

    return {
        "equity_curve": equity_curve,
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
    }
