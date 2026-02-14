def compute_shock_score(today_hits: int, baseline_7d: float, macro_relevance: float) -> float:
    volume_mult = min(5.0, today_hits / max(1.0, baseline_7d))
    score = min(1.0, (volume_mult - 1.0) * 0.5 + macro_relevance * 0.5)
    return max(0.0, score)
