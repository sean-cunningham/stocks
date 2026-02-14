from app.db import get_hysteresis_state, upsert_hysteresis_state
from app.models import ExitDecision


def exit_policy_v2(
    ticker: str,
    current_price: float,
    prev_close: float,
    atr_14d: float,
    signal_score: float,
) -> ExitDecision:
    state = get_hysteresis_state(ticker)
    peak_price = state["peak_price"] if state["peak_price"] is not None else current_price
    peak_price = max(peak_price, current_price)

    trail_stop = peak_price - 3.0 * atr_14d
    trail_stop_hit = current_price < trail_stop
    pnl_today = (current_price / prev_close - 1.0) if prev_close > 0 else 0.0

    downgrade_streak = state["downgrade_streak"] + 1 if signal_score < 0.70 else 0
    upsert_hysteresis_state(ticker, peak_price=peak_price, downgrade_streak=downgrade_streak)

    if trail_stop_hit:
        return ExitDecision(action="SELL_ALL", frac=1.0, reason="atr_trailing_stop_hit")
    if pnl_today >= 0.01:
        return ExitDecision(action="SELL_PARTIAL", frac=0.4, reason="take_profit_plus_1pct_day")
    if downgrade_streak >= 2 and signal_score < 0.70:
        return ExitDecision(action="SELL_ALL", frac=1.0, reason="downgrade_streak_trigger")
    return ExitDecision(action="HOLD", frac=0.0, reason="hold_conditions")
