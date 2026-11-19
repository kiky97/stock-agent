import argparse
import os
from pathlib import Path

from .crew import StockAnalysisCrew
from .data_tools import CLOSES
from .reporting import render_markdown
from .schemas import DEFAULT_DOWNSIDE_PCT


def run() -> None:
    parser = argparse.ArgumentParser(description="Run the CrewAI stock risk portfolio demo.")
    parser.add_argument("--symbol", type=str.upper, choices=CLOSES, default="AAPL")
    parser.add_argument("--openai-model", help="Use an OpenAI model with the same synthetic inputs.")
    parser.add_argument("--downside-pct", type=int, default=DEFAULT_DOWNSIDE_PCT,
                        help="Whole percentage decrease from 1 to 99 (default: 5).")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="Write the validated report to a file.")
    parser.add_argument("--verbose", action="store_true", help="Show agent and tool activity.")
    args = parser.parse_args()
    if args.openai_model and not os.environ.get("OPENAI_API_KEY"):
        parser.error("--openai-model requires OPENAI_API_KEY")

    if not 1 <= args.downside_pct <= 99:
        parser.error("--downside-pct must be between 1 and 99")

    report = StockAnalysisCrew(
        args.symbol, args.openai_model, args.verbose, downside_pct=args.downside_pct,
    ).analyze()
    payload = render_markdown(report) if args.format == "markdown" else report.model_dump_json(indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    run()
