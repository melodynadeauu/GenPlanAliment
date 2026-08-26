"""Agent-facing structures and the LLM adapter: what the LLM must produce, validated at
the boundary, and the loop that drives it there.
"""
from core.agent.llm_adapter import GenerationResult, generate
from core.agent.schemas import PlanFood, PlanPropose

__all__ = [
    "GenerationResult",
    "PlanFood",
    "PlanPropose",
    "generate",
]
