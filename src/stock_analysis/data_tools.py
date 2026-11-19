from typing import Literal

from crewai.tools import BaseTool
from pydantic import BaseModel

from .schemas import Evidence, MarketSnapshot, Ticker

# Six synthetic daily closing prices in USD, ordered oldest to newest.
CLOSES = {
    "AAPL": (100, 103, 101, 105, 104, 108),
    "MSFT": (100, 109, 107, 98, 95, 101),
    "NVDA": (100, 105, 100, 103, 104, 106),
}

class QuoteInput(BaseModel):
    symbol: Ticker


class MarketDataTool(BaseTool):
    name: str = "get_market_snapshot"
    description: str = "Calculate metrics from six synthetic USD closing prices."
    args_schema: type[BaseModel] = QuoteInput

    def _run(self, symbol: Ticker) -> str:
        return market_snapshot(symbol).model_dump_json()


def market_snapshot(symbol: Ticker) -> MarketSnapshot:
    closes = CLOSES[symbol]
    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        max_drawdown = max(max_drawdown, 100 * (peak - close) / peak)

    return MarketSnapshot(
        symbol=symbol,
        source="synthetic",
        last_close_usd=float(closes[-1]),
        period_return_pct=round(100 * (closes[-1] / closes[0] - 1), 2),
        max_drawdown_pct=round(max_drawdown, 2),
    )


NOTES = {
    "AAPL": ("The mock product launch drove interest.", "The mock 10-K discloses supplier concentration."),
    "MSFT": ("The mock cloud segment faces pricing pressure.", "The mock 10-Q discloses rising capital expenditure."),
    "NVDA": ("The mock update shows stronger accelerator demand.", "The mock 10-K discloses customer concentration."),
}


def evidence(symbol: Ticker, kind: Literal["research", "filing"]) -> Evidence:
    research, filing = NOTES[symbol]
    return Evidence(
        symbol=symbol, kind=kind, source="synthetic",
        note=research if kind == "research" else filing,
    )


class EvidenceInput(BaseModel):
    symbol: Ticker
    kind: Literal["research", "filing"]


class EvidenceTool(BaseTool):
    name: str = "get_demo_evidence"
    description: str = "Read a synthetic research note or a mock filing excerpt for a supported ticker."
    args_schema: type[BaseModel] = EvidenceInput

    def _run(self, symbol: Ticker, kind: Literal["research", "filing"]) -> str:
        return evidence(symbol, kind).model_dump_json()
