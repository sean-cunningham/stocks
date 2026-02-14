from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class EntryDecision:
    action: Literal["BUY", "NO_TRADE"]
    reason: str


@dataclass(frozen=True)
class ExitDecision:
    action: Literal["HOLD", "SELL_PARTIAL", "SELL_ALL"]
    frac: float
    reason: str
