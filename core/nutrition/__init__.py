"""Deterministic nutrition core: no I/O, no LLM, no UI."""
from core.nutrition.energy import compute_bmr

__all__ = ["compute_bmr"]
