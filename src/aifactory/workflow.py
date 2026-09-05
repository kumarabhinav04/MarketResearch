from __future__ import annotations

import importlib.util
import logging
from typing import Any

from .agents import (
    EligibilityAgent,
    EvidenceAgent,
    ExposureAgent,
    GrowthForecastAgent,
    MarginAgent,
    MoatAgent,
    NarrativeAgent,
    RiskAgent,
    SkepticAgent,
)
from .agents.roles import WorkflowState
from .database import Database
from .llm import ModelGateway, PromptRegistry
from .models import CompanyAssessment
from .telemetry import company_id_context, run_id_context


LOGGER = logging.getLogger(__name__)


class CompanyResearchWorkflow:
    """Typed company workflow with a LangGraph runtime and a dependency-free fallback."""

    def __init__(
        self,
        database: Database,
        policy: dict[str, Any],
        model_gateway: ModelGateway,
        prompt_registry: PromptRegistry,
        prefer_langgraph: bool = True,
    ):
        self.database = database
        self.policy = policy
        self.agents = [
            EligibilityAgent(),
            EvidenceAgent(),
            ExposureAgent(),
            MoatAgent(),
            MarginAgent(),
            GrowthForecastAgent(),
            RiskAgent(),
            SkepticAgent(),
            NarrativeAgent(model_gateway, prompt_registry),
        ]
        self.prefer_langgraph = prefer_langgraph
        self._compiled_graph = None

    @property
    def runtime_name(self) -> str:
        return "langgraph" if self._langgraph_available() and self.prefer_langgraph else "local_graph"

    def run(self, company_id: str, run_id: str, as_of_date: str) -> CompanyAssessment:
        run_token = run_id_context.set(run_id)
        company_token = company_id_context.set(company_id)
        try:
            company = self.database.get_company(company_id)
            if not company:
                raise KeyError(f"Unknown company: {company_id}")
            state: WorkflowState = {
                "run_id": run_id,
                "as_of_date": as_of_date,
                "company": company,
                "claims": self.database.list_claims(company_id, as_of_date),
                "policy": self.policy,
                "assessment": CompanyAssessment(company_id=company_id, run_id=run_id),
            }
            if self.prefer_langgraph and self._langgraph_available():
                result = self._graph().invoke(state)
                return result["assessment"]
            for agent in self.agents:
                state.update(agent(state))
            return state["assessment"]
        finally:
            company_id_context.reset(company_token)
            run_id_context.reset(run_token)

    def _langgraph_available(self) -> bool:
        return importlib.util.find_spec("langgraph") is not None

    def _graph(self):
        if self._compiled_graph is not None:
            return self._compiled_graph
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(WorkflowState)
        previous = START
        for agent in self.agents:
            graph.add_node(agent.name, agent)
            graph.add_edge(previous, agent.name)
            previous = agent.name
        graph.add_edge(previous, END)
        self._compiled_graph = graph.compile()
        return self._compiled_graph

