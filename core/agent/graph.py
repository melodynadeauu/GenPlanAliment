"""LangGraph orchestration: the 5/6-node machine the Dossier de défense's architecture
diagram describes (section 04). load_context is a pass-through documenting the input
boundary (Profile/ActivityEntry already validate on construction); agent/tools/
collect_proposal is the tool-calling loop that gets an LLM to call submit_plan;
resolve_recompute re-derives totals from get_nutrition_tool so no LLM number reaches
the user (G3); validate_guardrails enforces G1 (target conformity) and G2 (disliked
foods) in Python, looping back to `agent` with the violation reason appended to the
conversation, capped at MAX_ATTEMPTS -- exhausting it goes to `degrade` instead of
ever showing a silently-non-conforming plan (G7).
"""
import json
import time
from typing import Annotated, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from core.agent.errors import LLMInvalidOutputError, LLMRateLimitedError, LLMTimeoutError
from core.agent.guardrails import find_disliked_foods
from core.agent.schemas import PlanFood, PlanPropose
from core.tools.usda_tool import get_nutrition_tool

SUBMIT_PLAN_TOOL_NAME = "submit_plan"
# Sized for Groq's openai/gpt-oss-120b, which calls exactly one tool per turn (search then
# lookup, one food at a time) -- unlike Gemini, which batches many tool calls into a single
# turn and typically finishes in 1. A lower budget starves the one-tool-per-turn pattern
# before it's done gathering data, so the forced final turn errors instead of ever reaching
# submit_plan (verified live against Groq on 2026-08-25).
MAX_AUTO_TURNS = 15
RETRY_DELAYS_SECONDS = [1, 2]
MAX_RETRIES = 2
# G7: max 2 *guardrail-violation* retries (distinct from MAX_RETRIES above, which caps
# transient LLM-call retries within one attempt). In dur, not LLM-configurable. Shares
# the "turn" budget across attempts rather than resetting it per attempt -- MAX_AUTO_TURNS
# is generous enough (15) that this is a non-issue for a plan-sized number of foods.
MAX_ATTEMPTS = 2
# G1: a plan more than this fraction away from target_kcal is a guardrail violation, not
# merely imprecise -- the prompt already asks the LLM for +-10%, this is the deterministic
# check that actually enforces it. A target_kcal of 0 (falsy) skips this check entirely --
# used by tests that don't care about calorie conformity.
TARGET_TOLERANCE_FRACTION = 0.10


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
    # --- fields added for the 5/6-node graph (G1/G2/G3/G7) ---
    target_kcal: float
    dislikes: list[str]
    resolved_total_kcal: float | None
    attempt: int
    degraded: bool
    violations: list[str]


def build_graph(llm: BaseChatModel, data_tools: list[BaseTool], provider):
    """Compile the agent graph for one generate() call. `provider` is the active
    core.agent.providers.{gemini,groq} module -- used only for its classify_exception(),
    so this stays provider-agnostic the same way llm_adapter._provider already is.
    """
    all_tools = [*data_tools, submit_plan]
    tools_by_name = {t.name: t for t in data_tools}
    bound_auto = llm.bind_tools(all_tools)
    bound_forced = llm.bind_tools(all_tools, tool_choice=SUBMIT_PLAN_TOOL_NAME)

    def load_context_node(state: AgentState) -> dict:
        """Pass-through: Profile/ActivityEntry already validate their inputs at
        construction (core/models.py), so there's nothing left to reject here. Exists
        as its own node so the graph's shape matches the architecture diagram -- the
        input boundary is explicit even though today it never rejects anything.
        """
        return {}

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

    def collect_proposal_node(state: AgentState) -> dict:
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

    def resolve_recompute_node(state: AgentState) -> dict:
        """G3: never trust the LLM's own arithmetic. Re-derive the total kcal from
        get_nutrition_tool (already cache-warm from generation, see data.usda.cache) so
        validate_guardrails checks a number Python computed, not one the model claimed.
        """
        plan = state["plan"]
        assert plan is not None
        total_kcal = 0.0
        for food in plan.foods:
            nutrition = get_nutrition_tool.invoke({"fdc_id": food.fdc_id})
            if "error" in nutrition:
                continue  # unresolvable food: excluded from the total, not a crash
            macros = nutrition["macros_per_100g"]
            total_kcal += macros["kcal"] * (food.grams / 100)
        return {"resolved_total_kcal": total_kcal}

    def validate_guardrails_node(state: AgentState) -> dict:
        """G1 (target conformity) + G2 (disliked foods), both deterministic. Never
        mutates the plan -- only decides, via route_after_validate, whether to loop
        back to `agent`, finalize, or degrade.
        """
        plan = state["plan"]
        assert plan is not None
        violations: list[str] = []

        total = state["resolved_total_kcal"]
        target = state["target_kcal"]
        assert total is not None
        if target and abs(total - target) > TARGET_TOLERANCE_FRACTION * target:
            violations.append(
                f"Total is {round(total)} kcal, target is {round(target)} kcal "
                f"(must be within {int(TARGET_TOLERANCE_FRACTION * 100)}%)."
            )

        disliked = find_disliked_foods(plan.foods, state["dislikes"])
        if disliked:
            names = ", ".join(f.description for f in disliked)
            violations.append(f"These foods are on the dislikes list and must be removed: {names}.")

        return {"violations": violations}

    def degrade_node(state: AgentState) -> dict:
        return {"degraded": True}

    def apply_retry_node(state: AgentState) -> dict:
        reason = " ".join(state["violations"])
        return {
            "attempt": state["attempt"] + 1,
            "messages": [HumanMessage(content=f"The previous plan was rejected: {reason} Submit a corrected plan.")],
        }

    def route_after_agent(state: AgentState) -> str:
        if state.get("error"):
            return END
        tool_calls = state["messages"][-1].tool_calls
        if any(call["name"] == SUBMIT_PLAN_TOOL_NAME for call in tool_calls):
            return "collect_proposal"
        if state["turn"] > MAX_AUTO_TURNS:
            # The forced final turn didn't call submit_plan (no tool call, or the wrong
            # tool) -- collect_proposal_node reports invalid_output rather than looping
            # again. Checked before the tool_calls check below so a provider that doesn't
            # honor tool_choice on the forced turn can't loop past the intended single
            # forced call.
            return "collect_proposal"
        if tool_calls:
            return "tools"
        return "agent"

    def route_after_collect(state: AgentState) -> str:
        return END if state.get("error") else "resolve_recompute"

    def route_after_validate(state: AgentState) -> str:
        if not state["violations"]:
            return "finalize"
        if state["attempt"] >= MAX_ATTEMPTS:
            return "degrade"
        return "retry"

    graph = StateGraph(AgentState)
    graph.add_node("load_context", load_context_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("collect_proposal", collect_proposal_node)
    graph.add_node("resolve_recompute", resolve_recompute_node)
    graph.add_node("validate_guardrails", validate_guardrails_node)
    graph.add_node("retry", apply_retry_node)
    graph.add_node("degrade", degrade_node)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "agent")
    graph.add_conditional_edges("agent", route_after_agent)
    graph.add_edge("tools", "agent")
    graph.add_conditional_edges("collect_proposal", route_after_collect)
    graph.add_edge("resolve_recompute", "validate_guardrails")
    graph.add_conditional_edges(
        "validate_guardrails", route_after_validate, {"finalize": END, "degrade": "degrade", "retry": "retry"}
    )
    graph.add_edge("retry", "agent")
    graph.add_edge("degrade", END)
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
