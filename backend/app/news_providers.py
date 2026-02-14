from datetime import datetime, timedelta, timezone
from typing import Any


def _mock_news(prefix: str, ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    base = datetime.now(timezone.utc)
    items: list[dict[str, Any]] = []
    for i in range(limit):
        ts = base - timedelta(hours=i * 5)
        items.append(
            {
                "source": prefix,
                "headline": f"{ticker.upper()} update {i + 1} from {prefix}",
                "summary": f"Short summary {i + 1} for {ticker.upper()} from {prefix}.",
                "published_utc": ts.isoformat(),
            }
        )
    return items


def gdelt_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    # TODO: Implement real GDELT call.
    return _mock_news("gdelt", ticker, limit)


def newsdata_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    # TODO: Implement real NewsData call.
    return _mock_news("newsdata", ticker, limit)


def gnews_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    # TODO: Implement real GNews call.
    return _mock_news("gnews", ticker, limit)


def guardian_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    # TODO: Implement real Guardian call.
    return _mock_news("guardian", ticker, limit)
