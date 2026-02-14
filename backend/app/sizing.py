from app.config import settings


def compute_alloc_pct(
    prob_outperform_90d: float,
    vol_20d: float,
    velocity: float,
    corr_penalty: float,
    risk_mode: str | None = None,
) -> float:
    prob = max(0.5, min(1.0, prob_outperform_90d))
    base = 0.01 + (prob - 0.5) * (0.05 - 0.01) / 0.5

    penalty = max(0.0, vol_20d) * 0.20 + max(0.0, velocity) * 0.10 + max(0.0, corr_penalty) * 0.10
    alloc = base - penalty
    alloc = max(0.01, alloc)

    max_alloc = settings.default_max_alloc_pct
    if (risk_mode or "").lower() == "moderate":
        max_alloc = settings.paper_max_alloc_pct
    return min(max_alloc, alloc)


def derive_qty(
    current_price: float,
    alloc_pct: float,
    qty_optional: float | None,
    notional_usd_optional: float | None,
) -> float:
    if qty_optional is not None:
        return max(0.0, qty_optional)
    if notional_usd_optional is not None:
        return max(0.0, notional_usd_optional / current_price)
    return max(0.0, (settings.paper_portfolio_usd * alloc_pct) / current_price)
