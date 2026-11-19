import os
from functools import cache
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .crew import StockAnalysisCrew
from .schemas import DEFAULT_DOWNSIDE_PCT, PortfolioReport, Ticker
from .sec_filings import (
    DEFAULT_FISCAL_YEAR,
    FilingComparison,
    FilingReport,
    FilingTicker,
    FiscalYear,
    analyze_filing,
    compare_filings,
)

app = FastAPI(
    title="Stock Risk Analyst",
    description="Analyze synthetic price risk and review cited risk disclosures from SEC filings.",
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


class FilingComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    symbol: FilingTicker


class FilingAnalysisRequest(FilingComparisonRequest):
    fiscal_year: FiscalYear = DEFAULT_FISCAL_YEAR


def _filing_model() -> str | None:
    model = os.environ.get("SEC_ANALYSIS_OPENAI_MODEL")
    if model and not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="The filing model is not configured.")
    return model


@app.post("/filings/analyze", response_model=FilingReport)
def analyze_sec_filing(request: FilingAnalysisRequest) -> FilingReport:
    model = _filing_model()
    with _analysis_lock:
        return analyze_filing(request.symbol, request.fiscal_year, model=model)


@app.post("/filings/compare", response_model=FilingComparison)
def compare_sec_filings(request: FilingComparisonRequest) -> FilingComparison:
    model = _filing_model()
    with _analysis_lock:
        return compare_filings(request.symbol, model=model)
