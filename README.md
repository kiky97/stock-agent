# Stock Risk Analyst

A portfolio extension of the official [CrewAI Stock Analysis example](https://github.com/crewAIInc/crewAI-examples/tree/da94a91e691e1cf5b3151416bb15b5b62729bea8/crews/stock_analysis). It preserves the upstream `CrewBase` layout, YAML configuration, and research-to-report workflow, and adds a Risk Analyst, validated reports, and a FastAPI interface.

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

## Run the FastAPI service

After installing dependencies and setting the demo environment variables above, start Uvicorn.

```bash
uv run --locked uvicorn stock_analysis.api:app --host 127.0.0.1 --port 8000
```

Open Swagger UI at `http://127.0.0.1:8000/docs` to try the API. The health endpoint is `GET /health`, and the OpenAPI spec is at `/openapi.json`.

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"NVDA","downside_pct":15}'
```

The API runs the same offline CrewAI pipeline as the CLI and returns a validated `PortfolioReport`. Supported symbols are AAPL, MSFT, and NVDA. The integer `downside_pct` defaults to 5 and accepts values from 1 to 99. Invalid requests return HTTP 422.

## Review real SEC disclosures

The service includes selected Item 1A excerpts from Apple and Microsoft's FY2023 and FY2024 SEC 10-K filings. Each report includes the EDGAR document URL, fiscal year, risk claims, verbatim quotes, and the review history.

~~~bash
curl -X POST http://127.0.0.1:8000/filings/analyze \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"AAPL","fiscal_year":2024}'

curl -X POST http://127.0.0.1:8000/filings/compare \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"MSFT"}'
~~~

1. The Research Analyst selects relevant categories from the local filing excerpts.
2. The Risk Analyst drafts one claim and a verbatim quote per selected category. Python checks each quote against its source, allowing whitespace normalization.
3. A separate Reviewer agent assesses whether the quote supports the claim. Citation failures and reviewer feedback go back to the Risk Analyst for one revision. After a second failure, the API returns an `insufficient_evidence` report with no published findings.

The annual comparison runs both reviews, pairs results by risk category, and labels excerpt wording changes or categories reviewed in only one year. The comparison covers the selected excerpts. It cannot establish that a risk appeared or disappeared across the full filings.

The default `offline_demo` mode uses scripted agent responses with real source excerpts. Apple's sample deliberately starts with an overstatement to demonstrate the review and revision path. To use a language model for selection, drafting, and semantic review, set `OPENAI_API_KEY` and `SEC_ANALYSIS_OPENAI_MODEL=gpt-4.1-mini` before starting Uvicorn. The reports identify the execution mode.

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

> Extended CrewAI’s official Stock Analysis example with a Risk Analyst agent that grades drawdown risk and models configurable downside scenarios. Enforced Pydantic output contracts and evidence consistency across a four-agent pipeline, and exposed the workflow through FastAPI. Added SEC 10-K risk extraction with verbatim citation checks, a Reviewer agent with bounded revision, and cross-year comparisons.
