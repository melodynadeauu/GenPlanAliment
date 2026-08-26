"""Per-provider adapters, each implementing the same three-function protocol:
start_conversation / call / append_tool_results. core.agent.llm_adapter picks one at
import time based on LLM_PROVIDER and never imports a provider SDK directly.
"""
