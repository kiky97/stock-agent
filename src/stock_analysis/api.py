from functools import cache
from threading import Lock
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from .crew import StockAnalysisCrew
from .schemas import DEFAULT_DOWNSIDE_PCT, PortfolioReport, Ticker

app = FastAPI(
    title="Stock Risk Analyst",
    description="Run a four-agent stock risk analysis using synthetic market data.",
    version="0.1.0",
)
_analysis_lock = Lock()


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    symbol: Ticker
    downside_pct: int = Field(default=DEFAULT_DOWNSIDE_PCT, ge=1, le=99)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


@cache
def _crew_for(symbol: Ticker, downside_pct: int) -> StockAnalysisCrew:
    # Reuse CrewBase instances across requests. Inputs allow 3 × 99 combinations.
    return StockAnalysisCrew(symbol, downside_pct=downside_pct)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/analyze", response_model=PortfolioReport)
def analyze(request: AnalysisRequest) -> PortfolioReport:
    # CrewAI's task-output store is shared within the process.
    with _analysis_lock:
        return _crew_for(request.symbol, request.downside_pct).analyze()
