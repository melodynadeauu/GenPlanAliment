"""LangGraph orchestration: the node graph described in docs/architecture.md.

agent/tools/collect_proposal (tool-calling loop, where the LLM can
call compute_plan_total to check its own math) -> resolve_recompute (re-derives
totals so no LLM number reaches the user) -> validate_guardrails (target conformity,
disliked foods, unresolved fdc_ids). A calorie-only violation is rescaled for free via
adjust_portions before any retry is spent; anything else (or a rescale that clamping
couldn't fix) loops back to agent up to MAX_ATTEMPTS, then degrade instead of showing
a non-conforming plan.
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
# Sized for Groq (one tool call per turn); Gemini batches many per turn.
MAX_AUTO_TURNS = 15
RETRY_DELAYS_SECONDS = [1, 2]
MAX_RETRIES = 2
# Max guardrail-violation retries (separate from MAX_RETRIES, for transient LLM errors).
MAX_ATTEMPTS = 2
# A plan more than this fraction off target_kcal is a violation. target_kcal=0
# skips the check (used by tests).
TARGET_TOLERANCE_FRACTION = 0.10
# When the calorie target is the only remaining violation, rescale grams instead
# of degrading -- but only up to this fraction off target.
ADJUST_MAX_FRACTION = 0.15
# Rescaled portions are rounded to the nearest multiple of this many grams,
# never below it.
ADJUST_ROUND_GRAMS = 5
# Rescaled portions are clamped to this range so adjust_portions never produces
# an unrealistic serving (e.g. 5g of rice, or 900g of lettuce).
MIN_GRAMS = 20.0
MAX_GRAMS = 400.0


@tool
def submit_plan(foods: list[PlanFood]) -> str:
    """Submit the final, complete meal plan once all foods have been looked up."""
    return "ok"


@tool
def compute_plan_total(foods: list[dict]) -> dict:
    """Compute the true total kcal for a draft list of foods, each a dict with
    fdc_id and grams. Uses the same USDA lookup the final plan is checked
    against, so this catches arithmetic mistakes before submit_plan does. Call
    it as often as needed while drafting; it submits nothing.
    Success: {"total_kcal", "unresolved_fdc_ids"} -- an fdc_id USDA doesn't
    recognize is excluded from the total and listed there instead.
    """
    total_kcal = 0.0
    unresolved_fdc_ids: list[str] = []
    for food in foods:
        kcal_per_100g = _lookup_kcal_per_100g(food["fdc_id"])
        if kcal_per_100g is None:
            unresolved_fdc_ids.append(food["fdc_id"])
            continue
        total_kcal += kcal_per_100g * (food["grams"] / 100)
    return {"total_kcal": round(total_kcal, 1), "unresolved_fdc_ids": unresolved_fdc_ids}


def _lookup_kcal_per_100g(fdc_id: str) -> float | None:
    """kcal/100g for `fdc_id` via get_nutrition_tool, or None if USDA doesn't
    recognize it."""
    nutrition = get_nutrition_tool.invoke({"fdc_id": fdc_id})
    if "error" in nutrition:
        return None
    return nutrition["macros_per_100g"]["kcal"]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    turn: int
    tool_was_called: bool
    plan: PlanPropose | None
    error: str | None
    # --- guardrail state ---
    target_kcal: float
    dislikes: list[str]
    resolved_total_kcal: float | None
    attempt: int
    degraded: bool
    violations: list[str]
    unresolved: list[str]
    adjustable: bool
    adjusted: bool


def build_graph(llm: BaseChatModel, data_tools: list[BaseTool], provider):
    """Compile the agent graph for one generate() call. `provider` supplies
    classify_exception().
    """
    all_tools = [*data_tools, compute_plan_total, submit_plan]
    tools_by_name = {t.name: t for t in [*data_tools, compute_plan_total]}
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

    def collect_proposal_node(state: AgentState) -> dict:
        last = state["messages"][-1]
        call = next((c for c in last.tool_calls if c["name"] == SUBMIT_PLAN_TOOL_NAME), None)
        if call is None:
            return {"error": "invalid_output"}
        try:
            plan = PlanPropose(**call["args"])
        except (ValidationError, TypeError):
            return {"error": "invalid_output"}
        # An empty plan is only valid if a data tool was actually called first.
        if not plan.foods and not state["tool_was_called"]:
            return {"error": "invalid_output"}
        return {"plan": plan}

    def resolve_recompute_node(state: AgentState) -> dict:
        """Re-derives total kcal from get_nutrition_tool instead of trusting the
        LLM's arithmetic. A food whose fdc_id USDA doesn't recognize is excluded
        from the total and collected into `unresolved`.
        """
        plan = state["plan"]
        assert plan is not None
        total_kcal = 0.0
        unresolved: list[str] = []
        for food in plan.foods:
            kcal_per_100g = _lookup_kcal_per_100g(food.fdc_id)
            if kcal_per_100g is None:
                unresolved.append(f"{food.description} (fdc_id {food.fdc_id})")
                continue  # unresolvable food: excluded from the total, flagged below
            total_kcal += kcal_per_100g * (food.grams / 100)
        return {"resolved_total_kcal": total_kcal, "unresolved": unresolved}

    def validate_guardrails_node(state: AgentState) -> dict:
        """Checks target conformity, disliked foods, and unresolved fdc_ids. Never
        mutates the plan; only decides the next route.

        `adjustable` is True only when the calorie target is the sole violation
        and within ADJUST_MAX_FRACTION.
        """
        plan = state["plan"]
        assert plan is not None
        violations: list[str] = []

        total = state["resolved_total_kcal"]
        target = state["target_kcal"]
        assert total is not None
        kcal_violation = bool(target) and abs(total - target) > TARGET_TOLERANCE_FRACTION * target
        if kcal_violation:
            violations.append(
                f"Total is {round(total)} kcal, target is {round(target)} kcal "
                f"(must be within {int(TARGET_TOLERANCE_FRACTION * 100)}%)."
            )

        disliked = find_disliked_foods(plan.foods, state["dislikes"])
        if disliked:
            names = ", ".join(f.description for f in disliked)
            violations.append(f"These foods are on the dislikes list and must be removed: {names}.")

        unresolved = state.get("unresolved") or []
        if unresolved:
            names = "; ".join(unresolved)
            violations.append(
                f"These foods don't exist in USDA -- look them up via search_food_tool "
                f"instead of inventing an fdc_id, or drop them: {names}."
            )

        within_adjust_cap = bool(target) and abs(total - target) <= ADJUST_MAX_FRACTION * target
        adjustable = kcal_violation and not disliked and not unresolved and within_adjust_cap

        return {"violations": violations, "adjustable": adjustable}

    def adjust_portions_node(state: AgentState) -> dict:
        """Scales every food's grams by target/total so the total lands on
        target_kcal, clamped to [MIN_GRAMS, MAX_GRAMS] per food. Runs at most once
        per generate() call; a residual violation after rounding/clamping falls
        through to retry (or degrade once attempts are exhausted).
        """
        plan = state["plan"]
        total = state["resolved_total_kcal"]
        assert plan is not None
        assert total is not None
        factor = state["target_kcal"] / total
        adjusted_foods = [
            food.model_copy(update={"grams": _clamp_grams(_round_grams(food.grams * factor))})
            for food in plan.foods
        ]
        return {"plan": plan.model_copy(update={"foods": adjusted_foods}), "adjusted": True}

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
            # Forced final turn didn't call submit_plan; report invalid_output
            # instead of looping again.
            return "collect_proposal"
        if tool_calls:
            return "tools"
        return "agent"

    def route_after_collect(state: AgentState) -> str:
        return END if state.get("error") else "resolve_recompute"

    def route_after_validate(state: AgentState) -> str:
        if not state["violations"]:
            return "finalize"
        if state["adjustable"] and not state["adjusted"]:
            return "adjust_portions"
        if state["attempt"] >= MAX_ATTEMPTS:
            return "degrade"
        return "retry"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("collect_proposal", collect_proposal_node)
    graph.add_node("resolve_recompute", resolve_recompute_node)
    graph.add_node("validate_guardrails", validate_guardrails_node)
    graph.add_node("retry", apply_retry_node)
    graph.add_node("adjust_portions", adjust_portions_node)
    graph.add_node("degrade", degrade_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent)
    graph.add_edge("tools", "agent")
    graph.add_conditional_edges("collect_proposal", route_after_collect)
    graph.add_edge("resolve_recompute", "validate_guardrails")
    graph.add_conditional_edges(
        "validate_guardrails",
        route_after_validate,
        {"finalize": END, "degrade": "degrade", "retry": "retry", "adjust_portions": "adjust_portions"},
    )
    graph.add_edge("retry", "agent")
    graph.add_edge("adjust_portions", "resolve_recompute")
    graph.add_edge("degrade", END)
    return graph.compile()


def _round_grams(grams: float) -> float:
    """Round to the nearest ADJUST_ROUND_GRAMS, never below it."""
    return max(float(ADJUST_ROUND_GRAMS), round(grams / ADJUST_ROUND_GRAMS) * ADJUST_ROUND_GRAMS)


def _clamp_grams(grams: float) -> float:
    """Keep a rescaled portion within [MIN_GRAMS, MAX_GRAMS]."""
    return min(MAX_GRAMS, max(MIN_GRAMS, grams))


def _invoke_with_retry(bound_llm, messages, provider):
    """One LLM call, retried per RETRY_DELAYS_SECONDS/MAX_RETRIES for retryable
    errors from provider.classify_exception. "invalid_output" raises immediately;
    anything else re-raises as-is.
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
