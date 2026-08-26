"""The provider-agnostic agent loop: force a structured PlanPropose out of whichever
LLM_PROVIDER is configured, executing data tools along the way, by building and running
the LangGraph graph in core.agent.graph. Never raises -- see GenerationResult.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from core.agent import graph as agent_graph
from core.agent.schemas import PlanPropose

# How many LangGraph steps one generate() call is allowed: worst case is
# agent_graph.MAX_AUTO_TURNS auto turns + 1 forced turn, each auto turn that calls a data
# tool costing one extra "tools" step, plus one "finalize" step (~32 in the worst case).
# 100 is a comfortable ceiling above that, not a tuned value.
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
    """Outcome of generate(): either `plan` on success, or `error` (one of "rate_limited",
    "timeout", "api_error", "invalid_output") on failure -- never both, never an exception.

    target_kcal defaults to None here -- generate() itself doesn't know the calorie target,
    it only drives the tool-calling loop. plan_generator.generate_daily_plan() fills it in
    from the deterministic pipeline it already ran before calling generate().
    """

    plan: PlanPropose | None
    error: str | None
    target_kcal: float | None = None


def generate(system_prompt: str, user_prompt: str, tools: list[BaseTool]) -> GenerationResult:
    """Build the LangGraph graph (core.agent.graph.build_graph) for the configured
    provider's chat model and run it to completion, translating its final state into a
    GenerationResult.
    """
    try:
        # get_llm() and build_graph() are inside this try too: get_llm() can raise
        # (pydantic validation, missing env setup) and build_graph() calls bind_tools(),
        # which can raise ValueError on an unconvertible tool schema. The pre-migration
        # loop guarded model/tool-declaration construction the same way, not just the
        # call loop, so generate()'s "never raises" contract has to cover this too.
        compiled = agent_graph.build_graph(_provider.get_llm(), tools, _provider)
        initial_state = {
            "messages": [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
            "turn": 0,
            "tool_was_called": False,
            "plan": None,
            "error": None,
        }
        final_state = compiled.invoke(initial_state, config={"recursion_limit": _RECURSION_LIMIT})
    except Exception:
        # Every LLM/tool failure core.agent.graph's own nodes can anticipate already
        # lands in final_state["error"] below -- this catches what a node's try/except
        # can't: LangGraph's own runtime raising between node executions (e.g.
        # GraphRecursionError if a provider ever violated tool_choice badly enough to
        # blow the turn budget). Keeps generate()'s "never raises" contract absolute.
        return GenerationResult(None, "api_error")
    if final_state["error"]:
        return GenerationResult(None, final_state["error"])
    return GenerationResult(final_state["plan"], None)
