import unittest
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from stock_analysis.api import app
from stock_analysis.schemas import PortfolioReport


class AnalysisApiTest(unittest.TestCase):
    def setUp(self):
        self.client = self.enterContext(TestClient(app))

    def test_health_and_openapi(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/docs").status_code, 200)
        schema = self.client.get("/openapi.json").json()
        self.assertIn("/analyze", schema["paths"])

    def test_analysis_keeps_requests_independent(self):
        requests = [
            ({"symbol": "AAPL"}, ("AAPL", 5, 102.60)),
            ({"symbol": "NVDA", "downside_pct": 15}, ("NVDA", 15, 90.10)),
            ({"symbol": "AAPL"}, ("AAPL", 5, 102.60)),
        ]

        def analyze(case):
            body, expected = case
            response = self.client.post("/analyze", json=body)
            self.assertEqual(response.status_code, 200, response.text)
            risk = PortfolioReport.model_validate(response.json()).risk
            self.assertEqual((risk.market.symbol, risk.downside_pct, risk.stressed_close_usd), expected)

        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(analyze, requests))

    def test_invalid_inputs_return_422(self):
        for body in (
            {"symbol": "UNKNOWN"},
            {"symbol": "AAPL", "downside_pct": 100},
            {"symbol": "AAPL", "downside_pct": "5"},
            {"symbol": "AAPL", "unexpected": True},
        ):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/analyze", json=body).status_code, 422)
