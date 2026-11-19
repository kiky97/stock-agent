from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Ticker = Literal["AAPL", "MSFT", "NVDA"]
RiskLevel = Literal["low", "medium", "high"]
DEFAULT_DOWNSIDE_PCT = 5


def risk_level_for(drawdown: float) -> RiskLevel:
    if drawdown >= 10:
        return "high"
    if drawdown >= 3:
        return "medium"
    return "low"


def stressed_close(last_close: float, downside_pct: int) -> float:
    return round(last_close * (100 - downside_pct) / 100, 2)


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    symbol: Ticker
    source: Literal["synthetic"]
    last_close_usd: float = Field(gt=0, allow_inf_nan=False)
    period_return_pct: float = Field(gt=-100, allow_inf_nan=False)
    max_drawdown_pct: float = Field(ge=0, lt=100, allow_inf_nan=False)


class RiskReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    market: MarketSnapshot
    risk_level: RiskLevel
    downside_pct: int = Field(default=DEFAULT_DOWNSIDE_PCT, ge=1, le=99)
    stressed_close_usd: float = Field(gt=0, allow_inf_nan=False)
    risk_factors: list[str] = Field(min_length=2)
    limitation: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_risk_metrics(self):
        expected = risk_level_for(self.market.max_drawdown_pct)
        if self.risk_level != expected:
            raise ValueError(f"Risk level must be {expected} for this drawdown")
        if self.stressed_close_usd != stressed_close(self.market.last_close_usd, self.downside_pct):
            raise ValueError("Stressed close must reflect the specified price drop")
        return self


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    symbol: Ticker
    kind: Literal["research", "filing"]
    source: Literal["synthetic"]
    note: str = Field(min_length=1)


class PortfolioReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    research: Evidence
    filing: Evidence
    risk: RiskReport
    summary: str = Field(min_length=1)
