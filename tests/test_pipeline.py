import unittest

from pydantic import ValidationError

from stock_analysis.crew import StockAnalysisCrew
from stock_analysis.reporting import render_markdown
from stock_analysis.schemas import PortfolioReport, RiskReport


class PortfolioPipelineTest(unittest.TestCase):
    def test_offline_workflow_and_constraints(self):
        cases = [
            ("AAPL", 1.94, "low", 102.60),
            ("NVDA", 4.76, "medium", 100.70),
            ("MSFT", 12.84, "high", 95.95),
        ]
        for symbol, drawdown, level, stressed_close in cases:
            with self.subTest(symbol=symbol):
                report = StockAnalysisCrew(symbol).analyze()
                self.assertEqual(report.risk.market.symbol, symbol)
                self.assertEqual(report.risk.market.max_drawdown_pct, drawdown)
                self.assertEqual(report.risk.risk_level, level)
                self.assertEqual(report.risk.stressed_close_usd, stressed_close)
                self.assertEqual(PortfolioReport.model_validate_json(report.model_dump_json()), report)

                risk = report.risk.model_dump()
                wrong_level = "high" if level != "high" else "low"
                with self.assertRaises(ValidationError):
                    RiskReport.model_validate(risk | {"risk_level": wrong_level})
                with self.assertRaises(ValidationError):
                    RiskReport.model_validate(risk | {"stressed_close_usd": 1.0})

    def test_custom_scenario_and_markdown(self):
        report = StockAnalysisCrew("NVDA", downside_pct=15).analyze()
        self.assertEqual(report.risk.downside_pct, 15)
        self.assertEqual(report.risk.stressed_close_usd, 90.10)
        self.assertEqual(report.risk.risk_level, "medium")
        self.assertIn("| Close after a 15% drop | $90.10 |", render_markdown(report))
        with self.assertRaises(ValidationError):
            RiskReport.model_validate(report.risk.model_dump() | {"downside_pct": 20})
        with self.assertRaises(ValueError):
            StockAnalysisCrew("NVDA", downside_pct=100)
