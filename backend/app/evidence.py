from datetime import datetime, timedelta, timezone
from statistics import stdev
from typing import Any

import yfinance as yf

from app.news_providers import gdelt_news, gnews_news, guardian_news, newsdata_news
from app.provider_router import ProviderRouter
from app.shock import compute_shock_score


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _history_or_stub(ticker: str) -> list[dict[str, float]]:
    # yfinance is used strictly as raw input, never as direct trading decision engine.
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=60)
    hist = yf.download(ticker, start=start.date(), end=end.date(), progress=False, auto_adjust=False)
    if hist is None or hist.empty:
        # TODO: Implement real market data provider fallback.
        closes = [100.0 + i * 0.2 for i in range(30)]
        vols = [1_000_000.0 + i * 1_000.0 for i in range(30)]
        return [{"Close": c, "Volume": v} for c, v in zip(closes, vols)]
    rows: list[dict[str, float]] = []
    for _, row in hist.tail(30).iterrows():
        rows.append({"Close": _safe_float(row.get("Close")), "Volume": _safe_float(row.get("Volume"))})
    return rows


def _compute_returns(closes: list[float]) -> list[float]:
    returns: list[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if prev <= 0:
            continue
        returns.append(cur / prev - 1.0)
    return returns


def build_evidence_packet(
    ticker: str,
    news_router: ProviderRouter | None = None,
    news_ttl_seconds: int = 300,
) -> dict[str, Any]:
    rows = _history_or_stub(ticker.upper())
    closes = [r["Close"] for r in rows if r["Close"] > 0]
    vols = [r["Volume"] for r in rows if r["Volume"] >= 0]
    current_price = closes[-1] if closes else 0.0
    prev_close = closes[-2] if len(closes) > 1 else current_price

    returns = _compute_returns(closes[-21:]) if len(closes) >= 21 else _compute_returns(closes)
    vol_20d = stdev(returns[-20:]) if len(returns) >= 2 else 0.0
    avg_vol_20d = sum(vols[-20:]) / max(1, len(vols[-20:])) if vols else 0.0
    avg_close_20d = sum(closes[-20:]) / max(1, len(closes[-20:])) if closes else 0.0
    momentum_20d = (closes[-1] / closes[-20] - 1.0) if len(closes) >= 20 and closes[-20] > 0 else 0.0
    atr_14d = max(0.01, current_price * 0.02)

    info = {}
    try:
        info = yf.Ticker(ticker.upper()).info or {}
    except Exception:
        info = {}
    market_cap = _safe_float(info.get("marketCap"), 5_000_000_000.0)
    sector = str(info.get("sector", "Unknown"))
    industry = str(info.get("industry", "Unknown"))

    router = news_router or ProviderRouter(
        providers={
            "gdelt": gdelt_news,
            "newsdata": newsdata_news,
            "gnews": gnews_news,
            "guardian": guardian_news,
        },
        quotas={"gdelt": 100, "newsdata": 100, "gnews": 100, "guardian": 100},
        ttl_seconds=news_ttl_seconds,
    )
    news_items = router.call(cache_key=f"news:{ticker.upper()}", ticker=ticker.upper(), limit=5)[:5]
    filings = [
        {"type": "10-Q", "summary": f"{ticker.upper()} quarterly filing summary."},
        {"type": "8-K", "summary": f"{ticker.upper()} material event filing summary."},
        {"type": "10-K", "summary": f"{ticker.upper()} annual filing summary."},
    ][:3]
    news_sentiment = 0.2
    shock_score = compute_shock_score(today_hits=len(news_items), baseline_7d=3.0, macro_relevance=0.4)

    return {
        "ticker": ticker.upper(),
        "asof_utc": datetime.now(timezone.utc).isoformat(),
        "current_price": current_price,
        "prev_close": prev_close,
        "avg_vol_20d": avg_vol_20d,
        "avg_close_20d": avg_close_20d,
        "vol_20d": vol_20d,
        "price_momentum_20d": momentum_20d,
        "atr_14d": atr_14d,
        "market_cap": market_cap,
        "sector": sector,
        "industry": industry,
        "news_top5": news_items,
        "filings_top3": filings,
        "news_sentiment": news_sentiment,
        "today_hits": len(news_items),
        "baseline_7d": 3.0,
        "macro_relevance": 0.4,
        "shock_score": shock_score,
        "corr_penalty": 0.0,
        "velocity": abs(momentum_20d),
    }
