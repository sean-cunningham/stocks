import os
from dataclasses import dataclass, field


def _get_allowed_origins() -> tuple[str, ...]:
    v = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").strip()
    parts = [x.strip() for x in v.split(",") if x.strip()]
    return tuple(parts) if parts else ("http://localhost:3000",)


@dataclass(frozen=True)
class Settings:
    db_path: str = "stocks.db"
    allowed_origins: tuple[str, ...] = field(default_factory=_get_allowed_origins)
    recent_decision_hours: int = 48
    paper_portfolio_usd: float = 100_000.0
    paper_max_alloc_pct: float = 0.07
    default_max_alloc_pct: float = 0.05
    min_market_cap: float = 2_000_000_000.0
    min_avg_dollar_vol_20d: float = 20_000_000.0
    hard_veto_keywords: tuple[str, ...] = (
        "fraud",
        "bankruptcy",
        "accounting irregularity",
        "delisting",
        "material weakness",
    )
    enable_scheduler: bool = True
    reserve_job_minutes: int = 60
    broad_job_hours: int = 6
    reserve_max_queries: int = 10
    broad_max_queries: int = 50
    watchlist: tuple[str, ...] = ("AAPL", "MSFT", "NVDA", "TSLA", "AMZN")
    metrics_lookback_days: int = 90


settings = Settings()

METRICS_LOOKBACK_DAYS = settings.metrics_lookback_days

# Scheduler constants
ENABLE_SCHEDULER = settings.enable_scheduler
RESERVE_JOB_MINUTES = settings.reserve_job_minutes
BROAD_JOB_HOURS = settings.broad_job_hours
RESERVE_MAX_QUERIES = settings.reserve_max_queries
BROAD_MAX_QUERIES = settings.broad_max_queries
