"""Runs the LangGraph graph in core.agent.graph for the configured LLM_PROVIDER,
producing a PlanPropose. Never raises -- see GenerationResult.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from core.agent import graph as agent_graph
from core.agent.schemas import PlanPropose

# Max LangGraph steps per generate() call; ~32 in the worst case, 100 is a safe ceiling.
_RECURSION_LIMIT = 100


def _require_provider(value: str | None) -> str:
    if value not in ("gemini", "groq"):
        raise RuntimeError(
            f"LLM_PROVIDER must be 'gemini' or 'groq', got {value!r}. Define it in a .env "
            "file at the root of the project (see .env.example)."
        )
    return value


load_dotenv()
LLM_PROVIDER = _require_provider(os.getenv("LLM_PROVIDER"))

if LLM_PROVIDER == "gemini":
    from core.agent.providers import gemini as _provider
else:
    from core.agent.providers import groq as _provider


@dataclass(frozen=True)
class GenerationResult:
    """Outcome of generate(): `plan` on success or `error` on failure, never both,
    never an exception.

    target_kcal is filled in later by plan_generator.generate_daily_plan(), not here.
    degraded: guardrail retries were exhausted and the last plan was returned anyway.
    adjusted: retries were exhausted but grams were rescaled to hit target_kcal
    instead. Mutually exclusive with degraded (see core.agent.graph.route_after_validate).
    """

    plan: PlanPropose | None
    error: str | None
    target_kcal: float | None = None
    degraded: bool = False
    adjusted: bool = False


def generate(
    system_prompt: str,
    user_prompt: str,
    tools: list[BaseTool],
    target_kcal: float,
    dislikes: list[str],
) -> GenerationResult:
    """Builds and runs the graph for the configured provider, translating its
    final state into a GenerationResult.
    """
    try:
        # get_llm()/build_graph() can also raise before the graph runs.
        compiled = agent_graph.build_graph(_provider.get_llm(), tools, _provider)
        initial_state: agent_graph.AgentState = {
            "messages": [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            "turn": 0,
            "tool_was_called": False,
            "plan": None,
            "error": None,
            "target_kcal": target_kcal,
            "dislikes": dislikes,
            "resolved_total_kcal": None,
            "attempt": 1,
            "degraded": False,
            "violations": [],
            "unresolved": [],
            "adjustable": False,
            "adjusted": False,
        }
        final_state = compiled.invoke(initial_state, config={"recursion_limit": _RECURSION_LIMIT})
    except Exception:
        # Catches LangGraph runtime errors between nodes (e.g. GraphRecursionError).
        return GenerationResult(None, "api_error")
    if final_state["error"]:
        return GenerationResult(None, final_state["error"])
    return GenerationResult(
        final_state["plan"], None, degraded=final_state["degraded"], adjusted=final_state["adjusted"]
    )
