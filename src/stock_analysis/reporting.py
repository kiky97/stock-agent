from .schemas import PortfolioReport


def render_markdown(report: PortfolioReport) -> str:
    risk = report.risk
    market = risk.market
    factors = "\n".join(f"- {factor}" for factor in risk.risk_factors)
    return f"""# {market.symbol} Stock Risk Report

{report.summary}

| Metric | Result |
| --- | ---: |
| Last close | ${market.last_close_usd:.2f} |
| Sample return | {market.period_return_pct:+.2f}% |
| Maximum drawdown | {market.max_drawdown_pct:.2f}% |
| Risk rating | {risk.risk_level} |
| Close after a {risk.downside_pct}% drop | ${risk.stressed_close_usd:.2f} |

## Risk factors

{factors}

## Evidence

- **Research** — {report.research.note}
- **Filing** — {report.filing.note}

## Limitations

{risk.limitation}"""
