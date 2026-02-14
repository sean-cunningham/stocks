from datetime import datetime, timedelta, timezone
from typing import Any

import yfinance as yf
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import ENABLE_SCHEDULER, settings
from app.db import (
    derive_active_positions,
    get_hysteresis_state,
    init_db,
    insert_audit_log,
    insert_trade,
    most_recent_decision_hashes,
    most_recent_decision_payload,
)
from app.entry_policy import entry_gate
from app.evidence import build_evidence_packet
from app.exits import exit_policy_v2
from app.hashing import canonical_json_hash
from app.jobs import create_scheduler
from app.llm_router import llm_decide_from_evidence
from app.metrics import compute_metrics
from app.news_providers import gdelt_news, gnews_news, guardian_news, newsdata_news
from app.provider_router import ProviderRouter
from app.sizing import compute_alloc_pct, derive_qty

app = FastAPI(title="Stock Analysis Portfolio Bot v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BuyRequest(BaseModel):
    ticker: str
    qty_optional: float | None = None
    notional_usd_optional: float | None = None
    risk_mode: str | None = None
    fees: float = 0.0


class SellRequest(BaseModel):
    ticker: str
    qty_optional: float | None = None
    fees: float = 0.0


def _safe_current_price(ticker: str) -> float:
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=False)
        if data is not None and not data.empty:
            return float(data["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return 100.0


def analyze(ticker: str, router: ProviderRouter | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence_packet = build_evidence_packet(ticker.upper(), news_router=router)
    llm_decision = llm_decide_from_evidence(evidence_packet)
    return evidence_packet, llm_decision


@app.on_event("startup")
def _startup() -> None:
    init_db()
    app.state.news_router = ProviderRouter(
        providers={
            "gdelt": gdelt_news,
            "newsdata": newsdata_news,
            "gnews": gnews_news,
            "guardian": guardian_news,
        },
        quotas={"gdelt": 100, "newsdata": 100, "gnews": 100, "guardian": 100},
        ttl_seconds=300,
    )
    if ENABLE_SCHEDULER:
        scheduler = create_scheduler(app)
        scheduler.start()
        app.state.scheduler = scheduler


@app.on_event("shutdown")
def _shutdown() -> None:
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/analyze/{ticker}")
def analyze_endpoint(request: Request, ticker: str) -> dict[str, Any]:
    router = getattr(request.app.state, "news_router", None)
    evidence_packet, llm_decision = analyze(ticker, router=router)
    return {"evidence_packet": evidence_packet, "llm_decision": llm_decision}


@app.get("/api/portfolio/active")
def active_positions(request: Request) -> list[dict[str, Any]]:
    positions = derive_active_positions()
    since_iso = (datetime.now(timezone.utc) - timedelta(hours=settings.recent_decision_hours)).isoformat()
    router = getattr(request.app.state, "news_router", None)
    result: list[dict[str, Any]] = []
    for p in positions:
        ticker = p["ticker"]
        current_price = _safe_current_price(ticker)
        avg_cost = p["avg_cost"]
        unrealized = (current_price / avg_cost - 1.0) if avg_cost > 0 else 0.0
        recent_decision = most_recent_decision_payload(ticker, since_iso)
        evidence: dict[str, Any] | None = None

        if recent_decision is None:
            try:
                evidence_packet, llm_decision = analyze(ticker, router=router)
                evidence = evidence_packet
                evidence_hash = canonical_json_hash(evidence_packet)
                decision_hash = canonical_json_hash(llm_decision)
                insert_audit_log(
                    event_type="DECISION",
                    ticker=ticker,
                    evidence_hash=evidence_hash,
                    decision_hash=decision_hash,
                    payload={"evidence_packet": evidence_packet, "llm_decision": llm_decision},
                )
                recent_decision = {"evidence_packet": evidence_packet, "llm_decision": llm_decision}
            except Exception as exc:
                insert_audit_log(
                    event_type="ERROR",
                    ticker=ticker,
                    payload={"error": str(exc), "context": "active_positions_no_recent_decision"},
                )
                result.append(
                    {
                        "ticker": ticker,
                        "net_qty": p["net_qty"],
                        "avg_cost": avg_cost,
                        "current_price": current_price,
                        "unrealized_pnl_pct": unrealized,
                        "last_decision": None,
                        "sell_trigger": False,
                        "sell_reason": "no_recent_decision",
                    }
                )
                continue

        llm_decision = recent_decision.get("llm_decision") or {}
        signal_score_raw = llm_decision.get("signal_score")
        if signal_score_raw is None:
            result.append(
                {
                    "ticker": ticker,
                    "net_qty": p["net_qty"],
                    "avg_cost": avg_cost,
                    "current_price": current_price,
                    "unrealized_pnl_pct": unrealized,
                    "last_decision": llm_decision if llm_decision else None,
                    "sell_trigger": False,
                    "sell_reason": "no_recent_decision",
                }
            )
            continue

        if evidence is None:
            evidence = build_evidence_packet(ticker, news_router=router)
        signal_score = float(signal_score_raw)
        exit_decision = exit_policy_v2(
            ticker=ticker,
            current_price=current_price,
            prev_close=evidence["prev_close"],
            atr_14d=evidence["atr_14d"],
            signal_score=signal_score,
        )
        result.append(
            {
                "ticker": ticker,
                "net_qty": p["net_qty"],
                "avg_cost": avg_cost,
                "current_price": current_price,
                "unrealized_pnl_pct": unrealized,
                "last_decision": llm_decision,
                "sell_trigger": exit_decision.action != "HOLD",
                "sell_reason": exit_decision.reason,
            }
        )
    return result


@app.post("/api/portfolio/buy")
def buy_position(request: Request, req: BuyRequest) -> dict[str, Any]:
    ticker = req.ticker.upper()
    router = getattr(request.app.state, "news_router", None)
    evidence_packet, llm_decision = analyze(ticker, router=router)

    evidence_hash = canonical_json_hash(evidence_packet)
    decision_hash = canonical_json_hash(llm_decision)
    insert_audit_log(
        event_type="DECISION",
        ticker=ticker,
        evidence_hash=evidence_hash,
        decision_hash=decision_hash,
        payload={"evidence_packet": evidence_packet, "llm_decision": llm_decision},
    )

    entry = entry_gate(
        ticker=ticker,
        decision=llm_decision,
        avg_vol_20d=float(evidence_packet["avg_vol_20d"]),
        avg_close_20d=float(evidence_packet["avg_close_20d"]),
        market_cap=evidence_packet.get("market_cap"),
        shock_score=float(evidence_packet["shock_score"]),
    )
    if entry.action != "BUY":
        return {"status": "no_trade", "reason": entry.reason, "ticker": ticker}

    alloc_pct = compute_alloc_pct(
        prob_outperform_90d=float(llm_decision["prob_outperform_90d"]),
        vol_20d=float(evidence_packet["vol_20d"]),
        velocity=float(evidence_packet["velocity"]),
        corr_penalty=float(evidence_packet["corr_penalty"]),
        risk_mode=req.risk_mode,
    )
    current_price = float(evidence_packet["current_price"])
    qty = derive_qty(current_price, alloc_pct, req.qty_optional, req.notional_usd_optional)
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    insert_trade(
        ticker=ticker,
        side="BUY",
        qty=qty,
        price=current_price,
        fees=req.fees,
        evidence_hash=evidence_hash,
        decision_hash=decision_hash,
        strategy_id="v2",
        model_version="stub-llm-v2",
        note=entry.reason,
    )
    insert_audit_log(
        event_type="BUY",
        ticker=ticker,
        evidence_hash=evidence_hash,
        decision_hash=decision_hash,
        payload={"qty": qty, "price": current_price, "fees": req.fees, "reason": entry.reason},
    )
    return {"status": "ok", "ticker": ticker, "qty": qty, "price": current_price, "alloc_pct": alloc_pct}


@app.post("/api/portfolio/sell")
def sell_position(req: SellRequest) -> dict[str, Any]:
    ticker = req.ticker.upper()
    evidence_hash, decision_hash = most_recent_decision_hashes(ticker)
    if evidence_hash is None or decision_hash is None:
        fallback_hash = canonical_json_hash({})
        evidence_hash = fallback_hash
        decision_hash = fallback_hash
        insert_audit_log(
            event_type="ERROR",
            ticker=ticker,
            evidence_hash=evidence_hash,
            decision_hash=decision_hash,
            payload={"error": "Missing prior DECISION hashes for SELL"},
        )

    positions = {p["ticker"]: p for p in derive_active_positions()}
    if ticker not in positions:
        raise HTTPException(status_code=400, detail="No active position to sell")
    current_pos = positions[ticker]
    qty = req.qty_optional if req.qty_optional is not None else current_pos["net_qty"]
    if qty <= 0 or qty > current_pos["net_qty"]:
        raise HTTPException(status_code=400, detail="Invalid sell quantity")

    current_price = _safe_current_price(ticker)
    insert_trade(
        ticker=ticker,
        side="SELL",
        qty=qty,
        price=current_price,
        fees=req.fees,
        evidence_hash=evidence_hash,
        decision_hash=decision_hash,
        strategy_id="v2",
        model_version="stub-llm-v2",
        note="manual_sell",
    )
    state = get_hysteresis_state(ticker)
    if qty >= current_pos["net_qty"]:
        from app.db import upsert_hysteresis_state

        upsert_hysteresis_state(ticker, consecutive_ok=0, peak_price=state.get("peak_price"), downgrade_streak=0)
    insert_audit_log(
        event_type="SELL",
        ticker=ticker,
        evidence_hash=evidence_hash,
        decision_hash=decision_hash,
        payload={"qty": qty, "price": current_price, "fees": req.fees},
    )
    return {"status": "ok", "ticker": ticker, "qty": qty, "price": current_price}


@app.get("/api/metrics")
def metrics_endpoint() -> dict[str, Any]:
    return compute_metrics()
