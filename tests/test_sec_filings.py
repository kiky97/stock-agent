import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from stock_analysis import sec_filings
from stock_analysis.api import app


class FilingWorkflowTest(unittest.TestCase):
    def test_real_quote_with_overclaim_is_revised(self):
        report = sec_filings.analyze_filing("AAPL", 2024)
        self.assertEqual(report.status, "verified")
        self.assertEqual([attempt.stage for attempt in report.attempts], ["review", "accepted"])
        self.assertIn("not a confirmed event", report.attempts[0].feedback[0])
        source = sec_filings.CORPUS["AAPL", 2024]
        self.assertEqual(report.source_url, source.source_url)
        for finding in report.findings:
            self.assertIn(finding.quote, source.excerpts[finding.category])
        supply = next(finding for finding in report.findings if finding.category == "supply_chain")
        self.assertIn("dependency", supply.claim)

    def test_fabricated_quote_exhausts_retry_without_publication(self):
        original = sec_filings._run_task
        draft_instructions = []

        def run_task(llm, fixture, role, instruction, output):
            if output is sec_filings.RiskDraft:
                draft_instructions.append(instruction)
                fixture.findings[0].quote = "This invented sentence does not appear in the source excerpt."
            self.assertIsNot(output, sec_filings.SemanticReview)
            return original(llm, fixture, role, instruction, output)

        with patch.object(sec_filings, "_run_task", side_effect=run_task):
            report = sec_filings.analyze_filing("MSFT", 2024)

        self.assertEqual(report.status, "insufficient_evidence")
        self.assertEqual(report.findings, [])
        self.assertEqual([attempt.stage for attempt in report.attempts], ["citation", "citation"])
        self.assertEqual(len(draft_instructions), 2)
        self.assertIn("quote is absent", draft_instructions[1])

    def test_reviewer_rejections_stay_unpublished_after_retry(self):
        original = sec_filings._run_task

        def run_task(llm, fixture, role, instruction, output):
            if output is sec_filings.SemanticReview:
                return sec_filings.SemanticReview(issues=[
                    sec_filings.ReviewIssue(category="competition", reason="Unsupported certainty."),
                ])
            return original(llm, fixture, role, instruction, output)

        with patch.object(sec_filings, "_run_task", side_effect=run_task):
            report = sec_filings.analyze_filing("MSFT", 2024)
        self.assertEqual(report.status, "insufficient_evidence")
        self.assertEqual(report.findings, [])
        self.assertEqual([attempt.stage for attempt in report.attempts], ["review", "review"])

    def test_compare_filing_excerpts_through_api(self):
        with patch.dict(os.environ, {"SEC_ANALYSIS_OPENAI_MODEL": ""}), TestClient(app) as client:
            invalid = client.post("/filings/analyze", json={"symbol": "AAPL", "fiscal_year": 2022})
            response = client.post("/filings/analyze", json={"symbol": "AAPL"})
            comparison = client.post("/filings/compare", json={"symbol": "MSFT"})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(sec_filings.FilingReport.model_validate_json(response.content).fiscal_year, 2024)
        self.assertEqual(comparison.status_code, 200, comparison.text)
        data = sec_filings.FilingComparison.model_validate_json(comparison.content)
        self.assertEqual(data.status, "compared")
        self.assertEqual((data.earlier.fiscal_year, data.later.fiscal_year), (2023, 2024))
        self.assertNotEqual(data.earlier.source_url, data.later.source_url)
        changes = {change.category: change for change in data.changes}
        self.assertEqual(changes["ai"].status, "only_in_later_review")
        self.assertIsNone(changes["ai"].earlier)
        self.assertEqual(changes["competition"].status, "wording_changed")
        self.assertEqual(changes["cybersecurity"].status, "unchanged")
