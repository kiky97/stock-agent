from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .data_tools import EvidenceTool, MarketDataTool, evidence, market_snapshot
from .offline import FixtureLLM
from .schemas import DEFAULT_DOWNSIDE_PCT, Evidence, MarketSnapshot, PortfolioReport, RiskReport, Ticker


@CrewBase
class StockAnalysisCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(
        self, symbol: Ticker, model: str | None = None, verbose: bool = False,
        *, downside_pct: int = DEFAULT_DOWNSIDE_PCT,
    ):
        if type(downside_pct) is not int or not 1 <= downside_pct <= 99:
            raise ValueError("Downside must be a whole percentage from 1 to 99.")
        self.downside_pct = downside_pct
        self.symbol = symbol
        self.model = LLM(model=f"openai/{model}", temperature=0) if model else FixtureLLM(symbol, downside_pct)
        self.verbose = verbose

    @agent
    def research_analyst_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["research_analyst"],
            tools=[EvidenceTool()],
            llm=self.model,
        )

    @agent
    def financial_analyst_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["financial_analyst"],
            tools=[MarketDataTool(), EvidenceTool()],
            llm=self.model,
        )

    @agent
    def risk_analyst_agent(self) -> Agent:
        return Agent(config=self.agents_config["risk_analyst"], llm=self.model)

    @agent
    def investment_advisor_agent(self) -> Agent:
        return Agent(config=self.agents_config["investment_advisor"], llm=self.model)

    @task
    def research(self) -> Task:
        return Task(
            config=self.tasks_config["research"],
            agent=self.research_analyst_agent(),
            output_pydantic=Evidence,
        )

    @task
    def financial_analysis(self) -> Task:
        return Task(
            config=self.tasks_config["financial_analysis"],
            agent=self.financial_analyst_agent(),
            output_pydantic=MarketSnapshot,
        )

    @task
    def filings_analysis(self) -> Task:
        return Task(
            config=self.tasks_config["filings_analysis"],
            agent=self.financial_analyst_agent(),
            output_pydantic=Evidence,
        )

    @task
    def risk_analysis(self) -> Task:
        return Task(
            config=self.tasks_config["risk_analysis"],
            agent=self.risk_analyst_agent(),
            context=[self.financial_analysis(), self.filings_analysis()],
            output_pydantic=RiskReport,
        )

    @task
    def recommend(self) -> Task:
        return Task(
            config=self.tasks_config["recommend"],
            agent=self.investment_advisor_agent(),
            context=[self.research(), self.filings_analysis(), self.risk_analysis()],
            output_pydantic=PortfolioReport,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=self.verbose)

    def analyze(self) -> PortfolioReport:
        result = self.crew().kickoff(inputs={"company_stock": self.symbol, "downside_pct": self.downside_pct})
        research, market, filing, risk, final = (task.pydantic for task in result.tasks_output)
        if not isinstance(final, PortfolioReport) or not isinstance(risk, RiskReport):
            raise RuntimeError("The crew did not return validated risk and portfolio reports.")
        if (
            market != market_snapshot(self.symbol)
            or research != evidence(self.symbol, "research")
            or filing != evidence(self.symbol, "filing")
            or risk.market != market
            or risk.downside_pct != self.downside_pct
            or (final.research, final.filing, final.risk) != (research, filing, risk)
        ):
            raise RuntimeError("The final portfolio report does not match the upstream evidence.")
        return final
