import time
from typing import Any, Callable


class ProviderRouter:
    def __init__(self, providers: dict[str, Callable[..., Any]], quotas: dict[str, int], ttl_seconds: int = 300) -> None:
        self.ordering = ["gdelt", "newsdata", "gnews", "guardian"]
        self.providers = providers
        self.quotas = quotas.copy()
        self.ttl_seconds = ttl_seconds
        self.cache: dict[str, tuple[float, Any]] = {}

    def call(self, cache_key: str, **kwargs: Any) -> Any:
        now = time.time()
        if cache_key in self.cache:
            ts, value = self.cache[cache_key]
            if now - ts <= self.ttl_seconds:
                return value

        for provider_name in self.ordering:
            if self.quotas.get(provider_name, 0) <= 0:
                continue
            provider = self.providers.get(provider_name)
            if provider is None:
                continue
            result = provider(**kwargs)
            self.quotas[provider_name] -= 1
            self.cache[cache_key] = (now, result)
            return result
        raise RuntimeError("No provider available with remaining quota")
