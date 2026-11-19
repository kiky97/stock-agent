# Stock Risk Analyst

A portfolio extension of the official [CrewAI Stock Analysis example](https://github.com/crewAIInc/crewAI-examples/tree/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/stock_analysis). It preserves the upstream `CrewBase` layout, YAML configuration, and research-to-report workflow, and adds a Risk Analyst and validated JSON reports.

## Run the demo

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). From this directory, run:

```bash
uv sync --locked
export XDG_DATA_HOME="$PWD/.venv/data"
export OTEL_SDK_DISABLED=true CREWAI_DISABLE_TRACKING=true LITELLM_LOCAL_MODEL_COST_MAP=True
uv run --locked stock_analysis --symbol MSFT --output report.json
uv run --locked stock_analysis --symbol AAPL --verbose
uv run --locked stock_analysis --symbol NVDA --downside-pct 15 --format markdown --output report.md
uv run --locked python -m unittest discover -s tests -v
```

The default mode runs without credentials after dependencies are installed. A deterministic model drives the CrewAI tasks, which call tools backed by six synthetic closes per ticker, mock research notes, and mock SEC filing excerpts. With `OPENAI_API_KEY` set, pass `--openai-model gpt-4.1-mini` to run the same tasks and tools with an OpenAI model.

## How the crew works

| Agent | Task | Input or tool |
| --- | --- | --- |
| Research Analyst | Gather a company research note | `get_demo_evidence` |
| Financial Analyst | Calculate return and maximum drawdown | `get_market_snapshot` |
| Financial Analyst | Collect a mock filing disclosure | `get_demo_evidence` |
| Risk Analyst | Rate drawdown risk and model a configurable drop from the last close | Market snapshot and filing evidence |
| Investment Advisor | Assemble the research brief | Research, filing, and validated risk report |

An **Agent** owns a role, a **Task** defines the work and expected output, and a **Tool** performs a bounded operation against data. CrewAI passes earlier outputs to the Risk Analyst and Investment Advisor using explicit task context.

Pydantic validates every task output. It enforces the drawdown thresholds and verifies the stressed price against the last close. Before exporting, the CLI also checks that the final report preserves the upstream evidence and risk report.

| Synthetic case | Maximum drawdown | Risk grade | Close after a 5% drop |
| --- | ---: | --- | ---: |
| AAPL | 1.94% | low | $102.60 |
| NVDA | 4.76% | medium | $100.70 |
| MSFT | 12.84% | high | $95.95 |

The demo rates drawdown below 3% as low, 3% to under 10% as medium, and 10% or above as high. The stress scenario defaults to 5%. Pass `--downside-pct` with a whole number from 1 to 99 to change it. The risk grade remains based on observed sample drawdown. JSON is the default output format. Choose `--format markdown` for a human-readable report. All evidence is synthetic and intended for demonstration.

## CV bullet

> Extended CrewAI’s official Stock Analysis example with a Risk Analyst agent that grades drawdown risk and models configurable downside scenarios. Enforced Pydantic output contracts and evidence consistency across a four-agent pipeline, and verified JSON and Markdown reporting with offline cases.
