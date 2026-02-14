from app.config import settings
from app.db import get_hysteresis_state, upsert_hysteresis_state
from app.models import EntryDecision


def liquidity_guard(avg_vol_20d: float, avg_close_20d: float, market_cap: float | None) -> bool:
    avg_dollar_vol_20d = avg_vol_20d * avg_close_20d
    market_cap_ok = market_cap is not None and market_cap >= settings.min_market_cap
    return avg_dollar_vol_20d >= settings.min_avg_dollar_vol_20d and market_cap_ok


def _has_hard_veto(key_risks: list[str]) -> bool:
    lower = " ".join(key_risks).lower()
    return any(keyword.lower() in lower for keyword in settings.hard_veto_keywords)


def entry_gate(
    ticker: str,
    decision: dict,
    avg_vol_20d: float,
    avg_close_20d: float,
    market_cap: float | None,
    shock_score: float,
    sector_cap_ok: bool = True,
    corr_penalty_ok: bool = True,
    walk_forward_ok: bool = True,
) -> EntryDecision:
    liq_ok = liquidity_guard(avg_vol_20d=avg_vol_20d, avg_close_20d=avg_close_20d, market_cap=market_cap)
    if not liq_ok:
        upsert_hysteresis_state(ticker, consecutive_ok=0)
        return EntryDecision(action="NO_TRADE", reason="liquidity_guard_failed")
    if not sector_cap_ok:
        upsert_hysteresis_state(ticker, consecutive_ok=0)
        return EntryDecision(action="NO_TRADE", reason="sector_cap_failed")
    if not corr_penalty_ok:
        upsert_hysteresis_state(ticker, consecutive_ok=0)
        return EntryDecision(action="NO_TRADE", reason="corr_penalty_failed")

    key_risks = decision.get("key_risks", [])
    if _has_hard_veto(key_risks):
        upsert_hysteresis_state(ticker, consecutive_ok=0)
        return EntryDecision(action="NO_TRADE", reason="hard_veto")

    score = float(decision.get("signal_score", 0.0))
    prob = float(decision.get("prob_outperform_90d", 0.0))
    rec = decision.get("rec")

    strong_buy_ok = (
        rec == "STRONG_BUY" and score >= 0.80 and prob >= 0.60 and bool(walk_forward_ok)
    )
    buy_ok = score >= 0.70 and prob >= 0.55
    pass_gate = strong_buy_ok or buy_ok

    state = get_hysteresis_state(ticker)
    consecutive_ok = state["consecutive_ok"] + 1 if pass_gate else 0
    upsert_hysteresis_state(ticker, consecutive_ok=consecutive_ok)

    if not pass_gate:
        return EntryDecision(action="NO_TRADE", reason="signal_threshold_failed")

    if shock_score > 0.7:
        return EntryDecision(action="BUY", reason="shock_override")

    if consecutive_ok >= 2:
        return EntryDecision(action="BUY", reason="hysteresis_pass")
    return EntryDecision(action="NO_TRADE", reason="hysteresis_wait")
