"""Deterministic responses for exercising CrewAI without credentials."""

import json
import re

from crewai.llms.base_llm import BaseLLM
from pydantic import BaseModel

from .schemas import Evidence, MarketSnapshot, PortfolioReport, RiskReport, Ticker, risk_level_for, stressed_close


class FixtureLLM(BaseLLM):
    def __init__(self, symbol: Ticker, downside_pct: int):
        super().__init__(model="fixture")
        self.symbol = symbol
        self.downside_pct = downside_pct

    def call(
        self, messages, tools=None, callbacks=None, available_functions=None,
        from_task=None, from_agent=None,
    ):
        task_name = from_task.name
        prompt = messages if isinstance(messages, str) else "\n".join(
            str(message.get("content", "")) for message in messages
        )
        # Fixture tools and upstream tasks serialize their outputs as compact JSON.
        decoder = json.JSONDecoder()
        payloads = [
            decoder.raw_decode(prompt[match.start():])[0]
            for match in re.finditer(r'\{"(?:symbol|market)":', prompt)
        ]
        market = next((item for item in payloads if "last_close_usd" in item), None)
        notes = {item["kind"]: item for item in payloads if "kind" in item}

        if task_name in ("research", "filings_analysis"):
            kind = "research" if task_name == "research" else "filing"
            if kind not in notes:
                return self._action("get_demo_evidence", kind=kind)
            return self._answer(Evidence.model_validate(notes[kind]))

        if task_name == "financial_analysis":
            if market is None:
                return self._action("get_market_snapshot")
            return self._answer(MarketSnapshot.model_validate(market))

        filing = Evidence.model_validate(notes["filing"])
        if task_name == "risk_analysis":
            snapshot = MarketSnapshot.model_validate(market)
            drawdown = snapshot.max_drawdown_pct
            return self._answer(RiskReport(
                market=snapshot,
                risk_level=risk_level_for(drawdown),
                downside_pct=self.downside_pct,
                stressed_close_usd=stressed_close(snapshot.last_close_usd, self.downside_pct),
                risk_factors=[f"Sample drawdown was {drawdown:.2f}%.", filing.note],
                limitation="Uses six synthetic closing prices and a mock filing.",
            ))

        research = Evidence.model_validate(notes["research"])
        risk = RiskReport.model_validate(next(item for item in payloads if "risk_level" in item))
        return self._answer(PortfolioReport(
            research=research,
            filing=filing,
            risk=risk,
            summary=f"The synthetic {self.symbol} case rates {risk.risk_level} by drawdown. {filing.note}",
        ))

    def _action(self, tool_name: str, **kwargs: str) -> str:
        args = json.dumps({"symbol": self.symbol, **kwargs})
        return f"Thought: I need the fixture data.\nAction: {tool_name}\nAction Input: {args}"

    @staticmethod
    def _answer(model: BaseModel) -> str:
        return f"Final Answer: {model.model_dump_json()}"
