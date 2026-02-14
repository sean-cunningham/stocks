from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import (
    BROAD_JOB_HOURS,
    BROAD_MAX_QUERIES,
    RESERVE_JOB_MINUTES,
    RESERVE_MAX_QUERIES,
    settings,
)
from app.db import derive_active_positions, insert_audit_log
from app.entry_policy import entry_gate
from app.evidence import build_evidence_packet
from app.llm_router import llm_decide_from_evidence
from app.news_providers import gdelt_news, gnews_news, guardian_news, newsdata_news
from app.provider_router import ProviderRouter
from app.shock import compute_shock_score


def _make_news_router(ttl_seconds: int, budget: int) -> ProviderRouter:
    return ProviderRouter(
        providers={
            "gdelt": gdelt_news,
            "newsdata": newsdata_news,
            "gnews": gnews_news,
            "guardian": guardian_news,
        },
        quotas={"gdelt": budget, "newsdata": budget, "gnews": budget, "guardian": budget},
        ttl_seconds=ttl_seconds,
    )


def analyze_ticker(ticker: str, router: ProviderRouter | None = None, ttl_seconds: int = 300) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence_packet = build_evidence_packet(ticker.upper(), news_router=router, news_ttl_seconds=ttl_seconds)
    llm_decision = llm_decide_from_evidence(evidence_packet)
    return evidence_packet, llm_decision


def run_reserve_job(
    router: ProviderRouter | None = None,
    analyzer: Callable[[str, ProviderRouter | None, int], tuple[dict[str, Any], dict[str, Any]]] = analyze_ticker,
) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    router = router or _make_news_router(ttl_seconds=30 * 60, budget=RESERVE_MAX_QUERIES)
    holdings = [p["ticker"] for p in derive_active_positions()]
    tickers = holdings[:RESERVE_MAX_QUERIES]
    shock_triggers: list[str] = []
    checked: list[str] = []
    errors: list[dict[str, str]] = []

    try:
        for ticker in tickers:
            try:
                evidence, _ = analyzer(ticker, router, 30 * 60)
                checked.append(ticker)
                shock = compute_shock_score(
                    today_hits=int(evidence.get("today_hits", 0)),
                    baseline_7d=float(evidence.get("baseline_7d", 1.0)),
                    macro_relevance=float(evidence.get("macro_relevance", 0.0)),
                )
                if shock > 0.6:
                    shock_triggers.append(ticker)
            except Exception as exc:
                errors.append({"ticker": ticker, "error": str(exc)})

        payload = {
            "job_name": "reserve_hourly",
            "ran_at_utc": now_iso,
            "max_queries": RESERVE_MAX_QUERIES,
            "tickers_checked": checked,
            "shock_triggers": shock_triggers,
            "errors": errors,
        }
        insert_audit_log(event_type="JOB", ticker=None, payload=payload)
        if errors:
            insert_audit_log(event_type="ERROR", ticker=None, payload={"job_name": "reserve_hourly", "errors": errors})
        return payload
    except Exception as exc:
        insert_audit_log(
            event_type="ERROR",
            ticker=None,
            payload={"job_name": "reserve_hourly", "ran_at_utc": now_iso, "error": str(exc)},
        )
        raise


def run_broad_job(
    router: ProviderRouter | None = None,
    analyzer: Callable[[str, ProviderRouter | None, int], tuple[dict[str, Any], dict[str, Any]]] = analyze_ticker,
) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    ticker_router = router or _make_news_router(ttl_seconds=60 * 60, budget=BROAD_MAX_QUERIES)
    non_ticker_router = router or _make_news_router(ttl_seconds=4 * 60 * 60, budget=5)
    holdings = [p["ticker"] for p in derive_active_positions()]
    universe = list(dict.fromkeys(holdings + list(settings.watchlist)))
    tickers = universe[:BROAD_MAX_QUERIES]
    checked: list[str] = []
    entry_candidates: list[str] = []
    errors: list[dict[str, str]] = []

    try:
        # Non-ticker macro snapshot uses a longer cache TTL.
        macro_news = non_ticker_router.call(cache_key="macro:global", ticker="MACRO", limit=1)
        macro_hits = len(macro_news) if isinstance(macro_news, list) else 0

        for ticker in tickers:
            try:
                evidence, decision = analyzer(ticker, ticker_router, 60 * 60)
                checked.append(ticker)
                gate = entry_gate(
                    ticker=ticker,
                    decision=decision,
                    avg_vol_20d=float(evidence.get("avg_vol_20d", 0.0)),
                    avg_close_20d=float(evidence.get("avg_close_20d", 0.0)),
                    market_cap=evidence.get("market_cap"),
                    shock_score=float(evidence.get("shock_score", 0.0)),
                )
                if gate.action == "BUY":
                    entry_candidates.append(ticker)
            except Exception as exc:
                errors.append({"ticker": ticker, "error": str(exc)})

        payload = {
            "job_name": "broad_6h",
            "ran_at_utc": now_iso,
            "max_queries": BROAD_MAX_QUERIES,
            "macro_hits": macro_hits,
            "tickers_checked": checked,
            "entry_candidates": entry_candidates,
            "errors": errors,
        }
        insert_audit_log(event_type="JOB", ticker=None, payload=payload)
        if errors:
            insert_audit_log(event_type="ERROR", ticker=None, payload={"job_name": "broad_6h", "errors": errors})
        return payload
    except Exception as exc:
        insert_audit_log(
            event_type="ERROR",
            ticker=None,
            payload={"job_name": "broad_6h", "ran_at_utc": now_iso, "error": str(exc)},
        )
        raise


def create_scheduler(app: object | None = None) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    if app is not None and hasattr(app, "state") and hasattr(app.state, "news_router"):
        shared_router = app.state.news_router

        def reserve_wrapper() -> None:
            run_reserve_job(router=shared_router)

        def broad_wrapper() -> None:
            run_broad_job(router=shared_router)

        scheduler.add_job(reserve_wrapper, "interval", minutes=RESERVE_JOB_MINUTES, id="reserve_job", replace_existing=True)
        scheduler.add_job(broad_wrapper, "interval", hours=BROAD_JOB_HOURS, id="broad_job", replace_existing=True)
    else:
        scheduler.add_job(run_reserve_job, "interval", minutes=RESERVE_JOB_MINUTES, id="reserve_job", replace_existing=True)
        scheduler.add_job(run_broad_job, "interval", hours=BROAD_JOB_HOURS, id="broad_job", replace_existing=True)
    return scheduler
