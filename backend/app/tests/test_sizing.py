from app.sizing import compute_alloc_pct


def test_compute_alloc_bounds_default() -> None:
    low = compute_alloc_pct(prob_outperform_90d=0.5, vol_20d=0.0, velocity=0.0, corr_penalty=0.0)
    high = compute_alloc_pct(prob_outperform_90d=1.0, vol_20d=0.0, velocity=0.0, corr_penalty=0.0)
    assert 0.01 <= low <= 0.05
    assert abs(high - 0.05) < 1e-9


def test_compute_alloc_respects_moderate_max_and_penalties() -> None:
    moderate = compute_alloc_pct(
        prob_outperform_90d=1.0, vol_20d=0.0, velocity=0.0, corr_penalty=0.0, risk_mode="moderate"
    )
    penalized = compute_alloc_pct(
        prob_outperform_90d=1.0, vol_20d=0.2, velocity=0.3, corr_penalty=0.4, risk_mode="moderate"
    )
    assert moderate <= 0.07
    assert penalized < moderate
    assert penalized >= 0.01
