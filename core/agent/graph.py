"""LangGraph orchestration of the tool-calling loop: forces a structured PlanPropose out
of the bound chat model, executing data tools along the way. This is the loop that used
to live directly inside core.agent.llm_adapter -- the nodes below are that same loop, one
LangGraph node per turn-phase, so the graph *is* the control flow, not documentation of
it (Dossier de défense D2: "le dessin que je montre au client est littéralement le code
qui tourne").
"""
import json
import time
from typing import Annotated, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from core.agent.errors import LLMInvalidOutputError, LLMRateLimitedError, LLMTimeoutError
from core.agent.schemas import PlanFood, PlanPropose

SUBMIT_PLAN_TOOL_NAME = "submit_plan"
# Sized for Groq's openai/gpt-oss-120b, which calls exactly one tool per turn (search then
# lookup, one food at a time) -- unlike Gemini, which batches many tool calls into a single
# turn and typically finishes in 1. A lower budget starves the one-tool-per-turn pattern
# before it's done gathering data, so the forced final turn errors instead of ever reaching
# submit_plan (verified live against Groq on 2026-08-25).
MAX_AUTO_TURNS = 15
RETRY_DELAYS_SECONDS = [1, 2]
MAX_RETRIES = 2


@tool
def submit_plan(foods: list[PlanFood]) -> str:
    """Submit the final, complete meal plan once all foods have been looked up."""
    return "ok"


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    turn: int
    tool_was_called: bool
    plan: PlanPropose | None
    error: str | None


def build_graph(llm: BaseChatModel, data_tools: list[BaseTool], provider):
    """Compile the agent graph for one generate() call. `provider` is the active
    core.agent.providers.{gemini,groq} module -- used only for its classify_exception(),
    so this stays provider-agnostic the same way llm_adapter._provider already is.
    """
    all_tools = [*data_tools, submit_plan]
    tools_by_name = {t.name: t for t in data_tools}
    bound_auto = llm.bind_tools(all_tools)
    bound_forced = llm.bind_tools(all_tools, tool_choice=SUBMIT_PLAN_TOOL_NAME)

    def agent_node(state: AgentState) -> dict:
        bound = bound_forced if state["turn"] >= MAX_AUTO_TURNS else bound_auto
        try:
            response = _invoke_with_retry(bound, state["messages"], provider)
        except LLMRateLimitedError:
            return {"error": "rate_limited"}
        except LLMTimeoutError:
            return {"error": "timeout"}
        except LLMInvalidOutputError:
            return {"error": "invalid_output"}
        except Exception:
            return {"error": "api_error"}
        return {"messages": [response], "turn": state["turn"] + 1}

    def tools_node(state: AgentState) -> dict:
        last = state["messages"][-1]
        results = []
        for call in last.tool_calls:
            fn = tools_by_name.get(call["name"])
            if fn is None:
                content = {"error": "unknown_tool"}
            else:
                try:
                    content = fn.invoke(call["args"])
                except Exception:
                    content = {"error": "tool_execution_error"}
            results.append(ToolMessage(content=json.dumps(content), tool_call_id=call["id"], name=call["name"]))
        return {"messages": results, "tool_was_called": True}

    def finalize_node(state: AgentState) -> dict:
        last = state["messages"][-1]
        call = next((c for c in last.tool_calls if c["name"] == SUBMIT_PLAN_TOOL_NAME), None)
        if call is None:
            return {"error": "invalid_output"}
        try:
            plan = PlanPropose(**call["args"])
        except (ValidationError, TypeError):
            return {"error": "invalid_output"}
        # PlanPropose itself allows an empty foods list, but an empty plan is only
        # genuinely valid if the LLM actually tried and found nothing to add -- not if
        # it skipped straight to submit_plan without ever calling a data tool.
        if not plan.foods and not state["tool_was_called"]:
            return {"error": "invalid_output"}
        return {"plan": plan}

    def route_after_agent(state: AgentState) -> str:
        if state.get("error"):
            return END
        tool_calls = state["messages"][-1].tool_calls
        if any(call["name"] == SUBMIT_PLAN_TOOL_NAME for call in tool_calls):
            return "finalize"
        if state["turn"] > MAX_AUTO_TURNS:
            # The forced final turn didn't call submit_plan (no tool call, or the wrong
            # tool) -- finalize_node reports invalid_output rather than looping again.
            # Checked before the tool_calls check below so a provider that doesn't honor
            # tool_choice on the forced turn (and returns some other tool call instead of
            # submit_plan) can't loop past the intended single forced call.
            return "finalize"
        if tool_calls:
            return "tools"
        return "agent"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent)
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)
    return graph.compile()


def _invoke_with_retry(bound_llm, messages, provider):
    """One LLM call, retried per RETRY_DELAYS_SECONDS/MAX_RETRIES against whatever
    `provider.classify_exception` recognizes as retryable ("rate_limited"/"timeout"),
    raising the matching canonical error once retries are exhausted. A classification of
    "invalid_output" raises immediately, unretried; None re-raises the original exception
    as-is, translated by agent_node's bare `except Exception` into "api_error".
    """
    attempt = 0
    while True:
        try:
            return bound_llm.invoke(messages)
        except Exception as exc:
            outcome = provider.classify_exception(exc)
            if outcome == "invalid_output":
                raise LLMInvalidOutputError() from exc
            if outcome not in ("rate_limited", "timeout"):
                raise
            if attempt >= MAX_RETRIES:
                raise (LLMRateLimitedError if outcome == "rate_limited" else LLMTimeoutError)() from exc
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
            attempt += 1
