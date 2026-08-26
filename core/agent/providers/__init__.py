"""Per-provider adapters. Each provider module exposes get_llm() (a configured LangChain
chat model) and classify_exception(exc) -> str | None. core.agent.llm_adapter picks one at
import time based on LLM_PROVIDER and never imports a provider SDK directly.
"""
