# LangChain/LangGraph Agent Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-rolled per-provider tool-calling loop in `core/agent/` with LangChain (`ChatGoogleGenerativeAI` / `ChatGroq`, `@tool`) and LangGraph (`StateGraph`), so the agent's control flow is a compiled graph instead of a `for` loop re-implementing what those libraries already do — matching the architecture argued for in the two reference artifacts (battle plan block F; defense dossier D2 and the node/tool diagram in section 04).

**Architecture:** `core/agent/graph.py` (new) owns the tool-calling loop as a 3-node LangGraph graph (`agent` → `tools`/`finalize`, looping until `submit_plan` is called or the turn budget is exhausted). `core/agent/providers/{gemini,groq}.py` shrink to a `get_llm()` factory plus a `classify_exception()` predicate; `core/agent/llm_adapter.py` shrinks to building the initial state and invoking the graph. `core/tools/usda_tool.py`'s two functions become LangChain `@tool`s. `core/agent/tool_schema.py` is deleted — LangChain's own schema generation (verified below) replaces its hand-rolled JSON-schema normalization.

**Tech Stack:** `langgraph` 1.2 / `langchain-core` 1.6 (already installed), `langchain-google-genai` 4.3 / `langchain-groq` 1.1 (added by this plan). Python 3.11+, pytest, pydantic v2.

**Spec:** User-provided file table (chat message, 2026-08-26) plus the two linked artifacts — "Plan de bataille 48 heures" (block F: LangGraph, and the fallback-to-`run_pipeline()` pivot rule) and "Dossier de défense — Agent Meal Prep" (D2: why LangGraph over LangChain's `AgentExecutor`/CrewAI; section 04's node/tool distinction and the 6-node graph diagram; G1–G7 guardrail table). This plan implements only the tool-calling-loop slice of that architecture (node 3 + the USDA tool from the diagram) — nodes 1/2/4/5/6 already exist as `plan_generator.py`/`core/nutrition.py`/`plan_view.py` and are explicitly out of scope (see Global Constraints).

## Global Constraints

- **Working directory:** every `Run:`/`git` command below assumes `cwd` is `GenPlanAliment/` — that's its own git repository (`case_study_kpmg/`, one level up, is not a git repo). All file paths in this plan (Files sections, code blocks, commands) are relative to `GenPlanAliment/`.
- `plan_generator.py`, `schemas.py`, `prompts.py` do not change (user's own constraint) — `llm_adapter.generate(system_prompt, user_prompt, tools)` must keep its exact signature and its `GenerationResult(plan, error, target_kcal)` contract.
- `GenerationResult.error` stays one of exactly `"rate_limited"`, `"timeout"`, `"api_error"`, `"invalid_output"` — `app.py` and `main.py` branch on these four literal strings (`main.py:14-21`); a fifth value or a renamed one breaks both without any test catching it, since neither file is covered by this plan.
- Every `core.agent.errors` exception (`LLMRateLimitedError`, `LLMTimeoutError`, `LLMInvalidOutputError`) stays defined and actually raised somewhere in the real path — not just kept for `test_agent_errors.py` to import in isolation.
- No test may perform a real network call. Every LLM call in a test is against a fake chat model (`bind_tools`/`invoke` duck-typed) or, for provider-level tests, against real-but-locally-constructed SDK exception objects (`google.genai.errors.ClientError(...)`, `groq.RateLimitError(...)`) — never a live API request.
- `tests/conftest.py`'s placeholder env vars (`LLM_PROVIDER=gemini`, `*_API_KEY=test-placeholder-key`) must remain sufficient to import every `core.agent.*` module and run the full suite with no `.env` file present.

---

## Discovery notes (read before Task 4/5 — corrects the user's own file table)

Verified live in this repo's venv (`venv`) before writing this plan:

- `pip install langchain-google-genai` pulls in **`google-genai`** (the new SDK), not `google-generativeai`/`google-api-core`. `langchain_google_genai.ChatGoogleGenerativeAI` raises `google.genai.errors.ClientError` / `ServerError` — both carry the HTTP status on `.code` — instead of the old `google.api_core.exceptions.ResourceExhausted`/`DeadlineExceeded`/etc. The current `gemini.py`'s exception tuples do not translate 1:1; `classify_exception()` below inspects `.code` instead.
- `langchain_core.tools.tool` + `langchain_core.utils.function_calling.convert_to_openai_tool` already inline nested pydantic models and drop `$ref`/`$defs`/`title` — confirmed against this project's real `PlanFood`/`PlanPropose` (including the `MealType` enum and every `Field(description=...)`). This is exactly what `core/agent/tool_schema.py`'s `_normalize_schema` does by hand — hence it's deletable, not just "check usages".
- A `@tool`-decorated function is **not** callable as a plain function any more (`get_nutrition_tool(x)` raises `TypeError: 'StructuredTool' object is not callable`; the real call is `.invoke({"fdc_id": x})`). `core/agent/plan_view.py:85` calls `get_nutrition_tool(food.fdc_id)` directly — outside the user's file table, but this migration breaks it if left alone. Task 3 below fixes it; it was not optional.
- `StateGraph.add_conditional_edges(node, route_fn)` accepts a route function that returns `END` directly, no `path_map` needed (smoke-tested against installed `langgraph==1.2.11`).
- `bind_tools(tools, tool_choice="submit_plan")` is accepted by both `ChatGoogleGenerativeAI` and `ChatGroq` (smoke-tested — for Groq it lowers to `{"type": "function", "function": {"name": "submit_plan"}}`, matching the current hand-rolled Groq logic exactly).

---

### Task 1: Swap the Gemini SDK dependency, add the two new LangChain packages

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `langchain-google-genai` and `langchain-groq` importable in the venv for every later task.

- [ ] **Step 1: Edit requirements.txt**

Replace the current content:

```
requests
python-dotenv
google-generativeai
groq
langgraph
langchain-core
streamlit
pytest
```

with:

```
requests
python-dotenv
groq
langgraph
langchain-core
langchain-google-genai
langchain-groq
google-genai
streamlit
pytest
```

(`google-generativeai` is dropped — Task 4 removes the last import of it. `google-genai` is added explicitly, even though `langchain-google-genai` already pulls it in transitively — Task 4's `gemini.py` imports `google.genai.errors` directly, so the dependency should be declared, not implicit. This line was added during the final whole-branch review, not in Task 1's original execution — see the "Post-implementation fixes" note before Task 9.)

- [ ] **Step 2: Install into the venv**

Run: `venv/Scripts/python.exe -m pip install -r requirements.txt`

- [ ] **Step 3: Verify the imports resolve**

Run:
```
venv/Scripts/python.exe -c "from langchain_google_genai import ChatGoogleGenerativeAI; from langchain_groq import ChatGroq; from langgraph.graph import StateGraph, END, START; from langchain_core.tools import tool; print('ok')"
```
Expected: prints `ok`, no `ImportError`.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "deps: replace google-generativeai with langchain-google-genai + langchain-groq"
```

---

### Task 2: `core/tools/usda_tool.py` — decorate both functions with `@tool`

**Files:**
- Modify: `core/tools/usda_tool.py`
- Test: `tests/test_usda_tool.py`

**Interfaces:**
- Produces: `search_food_tool` / `get_nutrition_tool` as `langchain_core.tools.StructuredTool` instances — `.name` (`"search_food_tool"` / `"get_nutrition_tool"`), `.description` (from the docstring), and callable only via `.invoke({...})`, not `fn(...)`. Consumed by Task 6 (`graph.py`'s `tools_by_name`/`fn.invoke(call["args"])`) and Task 3 (`plan_view.py`).

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_usda_tool.py` with:

```python
"""Tests for core.tools.usda_tool: LLM-facing @tool wrappers around data.usda.client.

search_food_tool/get_nutrition_tool are StructuredTool instances (langchain_core.tools),
not plain functions -- called via .invoke({...}), not fn(...). data.usda.client.search_food
/ get_nutrition are monkeypatched directly (not requests.get) -- these tests only check the
tool's own wrapping, not the client's retry/caching behaviour, which is covered in
tests/test_usda_client*.
"""
import pytest

from core.tools import usda_tool
from data.usda import client as usda_client

ERROR_CODES = ["not_found", "rate_limited", "timeout", "api_error"]


# --- wiring: these are real LangChain tools, not plain functions ---


def test_search_food_tool_is_a_structured_tool_named_after_the_function():
    assert usda_tool.search_food_tool.name == "search_food_tool"
    assert "Search USDA foods" in usda_tool.search_food_tool.description


def test_get_nutrition_tool_is_a_structured_tool_named_after_the_function():
    assert usda_tool.get_nutrition_tool.name == "get_nutrition_tool"
    assert "Look up nutrition" in usda_tool.get_nutrition_tool.description


def test_a_structured_tool_is_no_longer_directly_callable():
    """Documents the breaking change @tool introduces -- callers must use .invoke({...}).
    core.agent.plan_view was the one caller relying on the old plain-callable form
    (see Task 3)."""
    with pytest.raises(TypeError):
        usda_tool.search_food_tool("apple")


# --- search_food_tool ---


def test_search_food_tool_returns_results_on_success(monkeypatch):
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: usda_client.FoodLookupResult(
            [{"fdc_id": 123, "description": "Apple, raw"}], None
        ),
    )

    result = usda_tool.search_food_tool.invoke({"query": "apple"})

    assert result == {"results": [{"fdc_id": 123, "description": "Apple, raw"}]}


def test_search_food_tool_passes_query_and_module_api_key(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: calls.append((query, api_key)) or usda_client.FoodLookupResult([], None),
    )

    usda_tool.search_food_tool.invoke({"query": "banana"})

    assert calls == [("banana", usda_client.USDA_API_KEY)]


@pytest.mark.parametrize("error_code", ERROR_CODES)
def test_search_food_tool_returns_error_dict_never_raises(monkeypatch, error_code):
    monkeypatch.setattr(
        usda_client,
        "search_food",
        lambda query, api_key: usda_client.FoodLookupResult(None, error_code),
    )

    result = usda_tool.search_food_tool.invoke({"query": "zzz_nonexistent"})

    assert result == {"error": error_code}


# --- get_nutrition_tool ---


CHICKEN_GRAVY_FOOD = {
    "fdc_id": 2620254,
    "description": "CHICKEN GRAVY, CHICKEN",
    "macros_per_100g": {"kcal": 65.0, "protein_g": 1.61, "fat_g": 4.03, "carbs_g": 4.84},
}


def test_get_nutrition_tool_passes_through_the_client_food_dict_unchanged(monkeypatch):
    """client.get_nutrition already extracts/caches only the four macros (see
    data.usda.nutrients) -- get_nutrition_tool is a passthrough, not a transform."""
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: usda_client.FoodLookupResult(CHICKEN_GRAVY_FOOD, None),
    )

    result = usda_tool.get_nutrition_tool.invoke({"fdc_id": "2620254"})

    assert result == CHICKEN_GRAVY_FOOD


def test_get_nutrition_tool_passes_fdc_id_and_module_api_key(monkeypatch):
    calls = []
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: calls.append((fdc_id, api_key))
        or usda_client.FoodLookupResult(CHICKEN_GRAVY_FOOD, None),
    )

    usda_tool.get_nutrition_tool.invoke({"fdc_id": "2620254"})

    assert calls == [("2620254", usda_client.USDA_API_KEY)]


@pytest.mark.parametrize("error_code", ERROR_CODES)
def test_get_nutrition_tool_returns_error_dict_never_raises(monkeypatch, error_code):
    monkeypatch.setattr(
        usda_client,
        "get_nutrition",
        lambda fdc_id, api_key: usda_client.FoodLookupResult(None, error_code),
    )

    result = usda_tool.get_nutrition_tool.invoke({"fdc_id": "1"})

    assert result == {"error": error_code}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_usda_tool.py -v`
Expected: FAIL — `search_food_tool`/`get_nutrition_tool` have no `.name`/`.invoke`, and the "not directly callable" test fails because they're still plain functions.

- [ ] **Step 3: Decorate both functions**

Replace `core/tools/usda_tool.py` with:

```python
"""LLM-facing tools wrapping data.usda.client.

Two distinct @tool-decorated functions rather than one generic dispatch with an
"action" param, so each stays a plain, single-purpose function an LLM can call
directly. Neither ever raises: on failure they return {"error": <code>}, one of
data.usda.client's four error codes (not_found, rate_limited, timeout, api_error).

@tool (langchain_core.tools) turns each function into a StructuredTool: its .name,
.description and argument schema are inferred from the function name, docstring and
type hints -- core.agent.graph binds these straight to the LLM, replacing the manual
JSON-schema building core.agent.tool_schema used to do by hand. Because of that, a
StructuredTool is no longer a plain callable -- call through .invoke({...}), not
tool(...) directly. core.agent.plan_view does this for get_nutrition_tool.
"""
from langchain_core.tools import tool

from data.usda import client as usda_client


@tool
def search_food_tool(query: str) -> dict:
    """Search USDA foods for `query`. Success: {"results": [{"fdc_id", "description"}, ...]}
    (client.py already trims each result to fdc_id + description; passed through as-is).
    Failure: {"error": <code>}.
    """
    result = usda_client.search_food(query, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    return {"results": result.food}


@tool
def get_nutrition_tool(fdc_id: str) -> dict:
    """Look up nutrition for `fdc_id`. Success: {"fdc_id", "description",
    "macros_per_100g"} -- client.py already extracts and caches only these macros
    (see data.usda.nutrients), so this is a passthrough, not a transform.
    Failure: {"error": <code>}.
    """
    result = usda_client.get_nutrition(fdc_id, usda_client.USDA_API_KEY)
    if result.error is not None:
        return {"error": result.error}
    assert isinstance(result.food, dict)
    return result.food
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_usda_tool.py -v`
Expected: PASS (all tests). Note `core/agent/plan_view.py` and `tests/test_plan_view.py` are now broken (Task 3 fixes them) and `tests/test_agent_tool_schema.py` may now fail on a schema-shape assertion tied to the old plain-function introspection (Task 8 removes it) — do not chase those failures here.

- [ ] **Step 5: Commit**

```bash
git add core/tools/usda_tool.py tests/test_usda_tool.py
git commit -m "feat(usda_tool): decorate search_food_tool/get_nutrition_tool with @tool"
```

---

### Task 3: Fix the one caller that used `get_nutrition_tool` as a plain function

**Files:**
- Modify: `core/agent/plan_view.py:85`
- Test: `tests/test_plan_view.py`

**Interfaces:**
- Consumes: `get_nutrition_tool` from Task 2, now a `StructuredTool` — must be called `.invoke({"fdc_id": ...})`.

- [ ] **Step 1: Write the failing test**

In `tests/test_plan_view.py`, add this helper right after the imports (before `PROFILE = ...`) and use it in place of every plain `lambda fdc_id: ...` monkeypatch:

```python
class _FakeNutritionTool:
    """Stands in for the StructuredTool get_nutrition_tool becomes after core.tools.usda_tool
    adds @tool (see tests/test_usda_tool.py) -- plan_view.py now calls
    get_nutrition_tool.invoke({"fdc_id": ...}), not get_nutrition_tool(fdc_id) directly."""

    def __init__(self, fn):
        self._fn = fn

    def invoke(self, args):
        return self._fn(args["fdc_id"])
```

Then replace each of the five occurrences of `monkeypatch.setattr(plan_view, "get_nutrition_tool", lambda fdc_id: X)` with `monkeypatch.setattr(plan_view, "get_nutrition_tool", _FakeNutritionTool(lambda fdc_id: X))`, for these five `X`:
- `APPLE_NUTRITION` (in `test_build_plan_view_places_a_single_food_under_its_meal_with_computed_kcal`)
- `NUTRITION_BY_FDC_ID[fdc_id]` (in `test_build_plan_view_orders_meals_breakfast_to_snack_regardless_of_input_order`)
- `NUTRITION_BY_FDC_ID[fdc_id]` (in `test_build_plan_view_sums_item_kcal_into_meal_and_total_kcal`)
- `{"error": "not_found"}` (in `test_build_plan_view_falls_back_to_estimation_when_nutrition_lookup_fails`)
- `APPLE_NUTRITION` (in `test_build_plan_view_omits_meals_with_no_foods`)
- `APPLE_NUTRITION` (in `test_generate_daily_plan_view_returns_the_built_view_on_success`)

(That's six call sites, all five distinct `X` values above — `APPLE_NUTRITION` appears three times.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_plan_view.py -v`
Expected: FAIL — `plan_view.py:85` still calls `get_nutrition_tool(food.fdc_id)`, and `_FakeNutritionTool` has no `__call__`, so every test hits `TypeError: '_FakeNutritionTool' object is not callable`.

- [ ] **Step 3: Fix the call site**

In `core/agent/plan_view.py`, change line 85:

```python
    nutrition = get_nutrition_tool(food.fdc_id)
```

to:

```python
    nutrition = get_nutrition_tool.invoke({"fdc_id": food.fdc_id})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_plan_view.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add core/agent/plan_view.py tests/test_plan_view.py
git commit -m "fix(plan_view): call get_nutrition_tool via .invoke() now that it's a StructuredTool"
```

---

### Task 4: Rewrite `core/agent/providers/gemini.py` around `ChatGoogleGenerativeAI`

**Files:**
- Modify: `core/agent/providers/gemini.py`
- Test: `tests/test_agent_provider_gemini.py`

**Interfaces:**
- Produces: `get_llm() -> ChatGoogleGenerativeAI` and `classify_exception(exc) -> str | None` (one of `"rate_limited"`/`"timeout"`/`None`; never `"invalid_output"` for this provider). Consumed by Task 6 (`graph.py`'s `build_graph(llm, tools, provider)` and `_invoke_with_retry`) and Task 7 (`llm_adapter.py`'s `_provider`).

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_agent_provider_gemini.py` with:

```python
"""Tests for core.agent.providers.gemini: the thin LangChain-facing adapter.
get_llm() only constructs a ChatGoogleGenerativeAI instance -- no network call happens
here. classify_exception() is pure and tested directly against real
google.genai.errors instances (constructing one needs no network call either)."""
from google.genai import errors as genai_errors
from langchain_google_genai import ChatGoogleGenerativeAI

from core.agent.providers import gemini


def test_get_llm_returns_a_configured_chat_google_generative_ai_instance():
    llm = gemini.get_llm()

    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model == gemini.GEMINI_MODEL


def test_get_llm_disables_the_sdks_own_retries():
    """core.agent.graph._invoke_with_retry owns retry/backoff now -- see Task 6."""
    llm = gemini.get_llm()

    assert llm.max_retries == 0


def test_classify_exception_returns_rate_limited_for_a_429_client_error():
    exc = genai_errors.ClientError(code=429, response_json={"error": {"message": "quota"}})

    assert gemini.classify_exception(exc) == "rate_limited"


def test_classify_exception_returns_none_for_a_non_429_client_error():
    exc = genai_errors.ClientError(code=400, response_json={"error": {"message": "bad request"}})

    assert gemini.classify_exception(exc) is None


def test_classify_exception_returns_timeout_for_any_server_error():
    exc = genai_errors.ServerError(code=503, response_json={"error": {"message": "unavailable"}})

    assert gemini.classify_exception(exc) == "timeout"


def test_classify_exception_returns_none_for_an_unrelated_exception():
    assert gemini.classify_exception(RuntimeError("boom")) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_provider_gemini.py -v`
Expected: FAIL — `gemini.get_llm`/`gemini.classify_exception` don't exist yet on the current hand-rolled module.

- [ ] **Step 3: Rewrite the module**

Replace `core/agent/providers/gemini.py` with:

```python
"""Gemini provider adapter: a LangChain ChatGoogleGenerativeAI instance plus the one bit
core.agent.graph needs to translate this SDK's own failures into the canonical error
codes GenerationResult can carry -- retry/backoff itself now lives once,
provider-agnostically, in core.agent.graph._invoke_with_retry.
"""
import os

import httpx
from dotenv import load_dotenv
from google.genai import errors as genai_errors
from langchain_core.exceptions import ModelRateLimitError
from langchain_google_genai import ChatGoogleGenerativeAI

# Verified live against this SDK/account on 2026-08-25: "gemini-2-flash" doesn't exist, and
# every Gemini 2.x flash model on this account is dead -- gemini-2.5-flash and
# gemini-2.5-flash-lite both 404 with "no longer available to new users", redirecting to
# gemini-3.6-flash (rate-limited) and gemini-3.5-flash-lite respectively. gemini-3.5-flash-lite
# is a genuinely separate model from gemini-3.6-flash (confirmed responding live), so it's used
# here as the working fallback while gemini-3.6-flash's quota is exhausted.
GEMINI_MODEL = "gemini-3.5-flash-lite"


def classify_exception(exc: Exception) -> str | None:
    """Return "rate_limited"/"timeout" for a failure core.agent.graph should retry, or
    None to let it propagate as "api_error". langchain-google-genai (the google-genai
    SDK, not the deprecated google-generativeai/google-api-core stack) raises
    google.genai.errors.ClientError/ServerError for every HTTP failure, with the status
    code on .code -- not a distinct exception class per status the way
    google.api_core.exceptions used to have, so the code itself is what's inspected here.
    Gemini has no equivalent of Groq's tool_use_failed refusal on a forced tool_choice,
    so this never returns "invalid_output".

    ChatGoogleGenerativeAI re-raises a 429 ClientError as its own GoogleRateLimitError
    (a langchain_core.exceptions.ModelRateLimitError), NOT a ClientError subclass --
    verified live against langchain-google-genai 4.3.5. Check the LangChain-classified
    type first; keep the raw genai_errors.ClientError check as a fallback for anything
    that bypasses the chat model layer. Similarly, max_retries=0 (get_llm(), below)
    disables the SDK's own retry of transient httpx.TimeoutException/ConnectError, so
    those are classified here too, not just genai_errors.ServerError.
    """
    if isinstance(exc, ModelRateLimitError):
        return "rate_limited"
    if isinstance(exc, genai_errors.ClientError) and exc.code == 429:
        return "rate_limited"
    if isinstance(exc, genai_errors.ServerError):
        return "timeout"
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return "timeout"
    return None


def _require_api_key(value: str | None) -> str:
    if not value:
        raise RuntimeError(
            "GEMINI_API_KEY is absent or empty. Define it in a .env file at the root of the "
            "project (see .env.example)."
        )
    return value


load_dotenv()
GEMINI_API_KEY = _require_api_key(os.getenv("GEMINI_API_KEY"))


def get_llm() -> ChatGoogleGenerativeAI:
    """Build a fresh chat model instance for one generate() call. max_retries=0: retrying
    what classify_exception() recognizes is core.agent.graph's job (shared across
    providers, bounded, and sleep-mockable in tests), not this SDK's own opaque policy.
    """
    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, max_retries=0)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_provider_gemini.py -v`
Expected: PASS (all 6 tests).

- [ ] **Step 5: Commit**

```bash
git add core/agent/providers/gemini.py tests/test_agent_provider_gemini.py
git commit -m "refactor(gemini): rewrite provider around ChatGoogleGenerativeAI"
```

---

### Task 5: Rewrite `core/agent/providers/groq.py` around `ChatGroq`

**Files:**
- Modify: `core/agent/providers/groq.py`
- Test: `tests/test_agent_provider_groq.py`

**Interfaces:**
- Produces: `get_llm() -> ChatGroq` and `classify_exception(exc) -> str | None` (one of `"rate_limited"`/`"timeout"`/`"invalid_output"`/`None`). Same consumers as Task 4.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_agent_provider_groq.py` with:

```python
"""Tests for core.agent.providers.groq: the thin LangChain-facing adapter.
get_llm() only constructs a ChatGroq instance -- no network call happens here.
classify_exception() is pure and tested directly against real groq SDK exception
instances (constructing one needs no network call either)."""
import groq as groq_sdk
from langchain_groq import ChatGroq

from core.agent.providers import groq


def fake_response(status_code):
    return type("Response", (), {"request": None, "status_code": status_code, "headers": {}})()


def test_get_llm_returns_a_configured_chat_groq_instance():
    llm = groq.get_llm()

    assert isinstance(llm, ChatGroq)
    assert llm.model_name == groq.GROQ_MODEL


def test_get_llm_disables_the_sdks_own_retries():
    """core.agent.graph._invoke_with_retry owns retry/backoff now -- see Task 6."""
    llm = groq.get_llm()

    assert llm.max_retries == 0


def test_classify_exception_returns_rate_limited_for_rate_limit_error():
    error = groq_sdk.RateLimitError("rate limited", response=fake_response(429), body=None)

    assert groq.classify_exception(error) == "rate_limited"


def test_classify_exception_returns_timeout_for_transient_errors():
    errors = [
        groq_sdk.APITimeoutError(request=None),
        groq_sdk.APIConnectionError(request=None),
        groq_sdk.InternalServerError("down", response=fake_response(500), body=None),
    ]

    for error in errors:
        assert groq.classify_exception(error) == "timeout"


def test_classify_exception_returns_invalid_output_when_forced_tool_choice_is_refused():
    """Verified live: a forced tool_choice the model doesn't honor surfaces as
    groq.BadRequestError with body["error"]["code"] == "tool_use_failed"."""
    error = groq_sdk.BadRequestError(
        "tool refused", response=fake_response(400), body={"error": {"code": "tool_use_failed"}}
    )

    assert groq.classify_exception(error) == "invalid_output"


def test_classify_exception_returns_none_for_other_bad_request_errors():
    error = groq_sdk.BadRequestError(
        "bad schema", response=fake_response(400), body={"error": {"code": "invalid_request_error"}}
    )

    assert groq.classify_exception(error) is None


def test_classify_exception_returns_none_for_an_unrelated_exception():
    assert groq.classify_exception(RuntimeError("boom")) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_provider_groq.py -v`
Expected: FAIL — `groq.get_llm`/`groq.classify_exception` don't exist yet on the current hand-rolled module.

- [ ] **Step 3: Rewrite the module**

Replace `core/agent/providers/groq.py` with:

```python
"""Groq provider adapter: a LangChain ChatGroq instance plus the one bit core.agent.graph
needs to translate this SDK's own failures into the canonical error codes
GenerationResult can carry -- retry/backoff itself now lives once, provider-agnostically,
in core.agent.graph._invoke_with_retry.

Secondary provider (Decisions.docx: "Ajouter llm secondaire au cas où"), not the actively
used path -- Gemini is primary.
"""
import os

import groq
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Verified live against this account on 2026-08-25: llama-3.3-70b-versatile no longer
# exists on this account; openai/gpt-oss-120b is the closest available equivalent with
# confirmed tool-calling support.
GROQ_MODEL = "openai/gpt-oss-120b"


def classify_exception(exc: Exception) -> str | None:
    """Return "rate_limited"/"timeout" for a failure core.agent.graph should retry,
    "invalid_output" for one it should report immediately without retrying, or None to
    let it propagate as "api_error". Verified live: a forced tool_choice the model
    doesn't honor surfaces as groq.BadRequestError with
    body["error"]["code"] == "tool_use_failed".
    """
    if isinstance(exc, groq.BadRequestError):
        if isinstance(exc.body, dict) and exc.body.get("error", {}).get("code") == "tool_use_failed":
            return "invalid_output"
        return None
    if isinstance(exc, groq.RateLimitError):
        return "rate_limited"
    if isinstance(exc, (groq.APITimeoutError, groq.APIConnectionError, groq.InternalServerError)):
        return "timeout"
    return None


def _require_api_key(value: str | None) -> str:
    if not value:
        raise RuntimeError(
            "GROQ_API_KEY is absent or empty. Define it in a .env file at the root of the "
            "project (see .env.example)."
        )
    return value


load_dotenv()
GROQ_API_KEY = _require_api_key(os.getenv("GROQ_API_KEY"))


def get_llm() -> ChatGroq:
    """Build a fresh chat model instance for one generate() call. max_retries=0: retrying
    what classify_exception() recognizes is core.agent.graph's job (shared across
    providers, bounded, and sleep-mockable in tests), not this SDK's own opaque policy.
    """
    return ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, max_retries=0)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_provider_groq.py -v`
Expected: PASS (all 7 tests).

- [ ] **Step 5: Commit**

```bash
git add core/agent/providers/groq.py tests/test_agent_provider_groq.py
git commit -m "refactor(groq): rewrite provider around ChatGroq"
```

---

### Task 6: New `core/agent/graph.py` — the LangGraph tool-calling loop

**Files:**
- Create: `core/agent/graph.py`
- Test: `tests/test_agent_graph.py`

**Interfaces:**
- Consumes: `core.agent.errors.{LLMRateLimitedError,LLMTimeoutError,LLMInvalidOutputError}` (unchanged); `core.agent.schemas.{PlanFood,PlanPropose}` (unchanged); a `provider` object exposing `classify_exception(exc) -> str | None` (Tasks 4/5).
- Produces: `MAX_AUTO_TURNS: int`, `SUBMIT_PLAN_TOOL_NAME: str`, `build_graph(llm, data_tools: list[BaseTool], provider) -> CompiledGraph` whose `.invoke(initial_state, config={"recursion_limit": N})` returns a `dict` with keys `messages`, `turn`, `tool_was_called`, `plan: PlanPropose | None`, `error: str | None`. Consumed by Task 7 (`llm_adapter.generate`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agent_graph.py`:

```python
"""Tests for core.agent.graph: the LangGraph tool-calling loop. The chat model is faked
(FakeChatModel) so these tests never call a real provider -- core.agent.providers.{gemini,
groq} are only reached through the `provider` argument's classify_exception(), itself
faked here too (FakeProvider)."""
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from core.agent import graph as agent_graph

APPLE = {"description": "Apple", "fdc_id": "1", "meal": "snack", "grams": 100.0}


@tool
def fake_tool(query: str) -> dict:
    """A fake data tool."""
    return {"results": [{"fdc_id": "1", "description": query}]}


@tool
def broken_tool(query: str) -> dict:
    """A fake data tool that raises instead of returning."""
    raise TypeError("boom")


def ai_message(tool_calls=None):
    return AIMessage(content="", tool_calls=tool_calls or [])


def submit_call(id_, foods):
    return {"name": "submit_plan", "args": {"foods": foods}, "id": id_, "type": "tool_call"}


def data_call(id_, name, args):
    return {"name": name, "args": args, "id": id_, "type": "tool_call"}


class _BoundFakeChatModel:
    def __init__(self, parent, tool_choice):
        self._parent = parent
        self.tool_choice = tool_choice

    def invoke(self, messages):
        self._parent.calls.append(self.tool_choice)
        item = self._parent.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeChatModel:
    """Replays a scripted list of turns; each turn is either an AIMessage or an
    exception instance to raise from invoke(). bind_tools() records the tool_choice
    each subsequent invoke() call was bound with, in self.calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def bind_tools(self, tools, tool_choice=None):
        return _BoundFakeChatModel(self, tool_choice)


class FakeProvider:
    """Stands in for core.agent.providers.{gemini,groq}: only classify_exception()
    matters to core.agent.graph."""

    def __init__(self, classify=lambda exc: None):
        self.classify_exception = classify


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(agent_graph.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


def _initial_state():
    return {
        "messages": [SystemMessage(content="system"), HumanMessage(content="user")],
        "turn": 0,
        "tool_was_called": False,
        "plan": None,
        "error": None,
    }


def _tool_messages(result):
    return [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]


def test_max_auto_turns_is_generous_enough_for_one_tool_call_per_turn_models():
    """Verified live against Groq's openai/gpt-oss-120b (2026-08-25): unlike Gemini, which
    batches many tool calls into a single turn, it calls exactly one tool per turn --
    search then lookup, one food at a time. A budget only large enough for Gemini's
    calling pattern starves it before it finishes gathering data, so the forced final
    turn fails instead of ever reaching submit_plan."""
    assert agent_graph.MAX_AUTO_TURNS >= 15


def test_finalizes_immediately_when_submit_plan_called_first_turn():
    model = FakeChatModel([ai_message([submit_call("1", [APPLE])])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert result["plan"].foods[0].description == "Apple"


def test_executes_data_tool_then_finalizes():
    model = FakeChatModel(
        [
            ai_message([data_call("1", "fake_tool", {"query": "chicken gravy"})]),
            ai_message([submit_call("2", [APPLE])]),
        ]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    tool_messages = _tool_messages(result)
    assert len(tool_messages) == 1
    assert json.loads(tool_messages[0].content) == {"results": [{"fdc_id": "1", "description": "chicken gravy"}]}
    assert result["tool_was_called"] is True


def test_feeds_back_unknown_tool_error_and_continues():
    model = FakeChatModel(
        [ai_message([data_call("1", "not_a_real_tool", {})]), ai_message([submit_call("2", [])])]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert json.loads(_tool_messages(result)[0].content) == {"error": "unknown_tool"}


def test_feeds_back_tool_execution_error_and_continues():
    model = FakeChatModel(
        [
            ai_message([data_call("1", "broken_tool", {"query": "chicken gravy"})]),
            ai_message([submit_call("2", [])]),
        ]
    )
    compiled = agent_graph.build_graph(model, [broken_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert json.loads(_tool_messages(result)[0].content) == {"error": "tool_execution_error"}


def test_forces_submit_plan_after_max_auto_turns():
    model = FakeChatModel(
        [ai_message([])] * agent_graph.MAX_AUTO_TURNS + [ai_message([submit_call("1", [APPLE])])]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert model.calls == [None] * agent_graph.MAX_AUTO_TURNS + ["submit_plan"]


def test_returns_invalid_output_when_forced_turn_still_skips_submit_plan():
    model = FakeChatModel([ai_message([])] * agent_graph.MAX_AUTO_TURNS + [ai_message([])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"


def test_returns_invalid_output_when_submit_plan_is_empty_and_no_tool_was_called():
    model = FakeChatModel([ai_message([submit_call("1", [])])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"
    assert result["plan"] is None


def test_allows_empty_submit_plan_when_a_tool_was_called_first():
    model = FakeChatModel(
        [
            ai_message([data_call("1", "fake_tool", {"query": "nonexistent food"})]),
            ai_message([submit_call("2", [])]),
        ]
    )
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert result["plan"].foods == []


def test_returns_invalid_output_when_submit_plan_arguments_fail_validation():
    bad_call = {"name": "submit_plan", "args": {"foods": [{"description": "Apple"}]}, "id": "1", "type": "tool_call"}
    model = FakeChatModel([ai_message([bad_call])])
    compiled = agent_graph.build_graph(model, [fake_tool], FakeProvider())

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"


@pytest.mark.parametrize("outcome", ["rate_limited", "timeout"])
def test_retries_then_reports_error_once_retries_exhausted(no_real_sleep, outcome):
    model = FakeChatModel([RuntimeError("boom")] * 3)
    provider = FakeProvider(classify=lambda exc: outcome)
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == outcome
    assert no_real_sleep == [1, 2]


def test_retries_transient_failure_then_succeeds(no_real_sleep):
    model = FakeChatModel([RuntimeError("boom"), ai_message([submit_call("1", [APPLE])])])
    provider = FakeProvider(classify=lambda exc: "timeout")
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] is None
    assert no_real_sleep == [1]


def test_reports_invalid_output_immediately_without_retrying(no_real_sleep):
    model = FakeChatModel([RuntimeError("refused")])
    provider = FakeProvider(classify=lambda exc: "invalid_output")
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "invalid_output"
    assert no_real_sleep == []


def test_reports_api_error_for_an_unclassified_exception_without_retrying(no_real_sleep):
    model = FakeChatModel([RuntimeError("mystery")])
    provider = FakeProvider(classify=lambda exc: None)
    compiled = agent_graph.build_graph(model, [fake_tool], provider)

    result = compiled.invoke(_initial_state(), config={"recursion_limit": 50})

    assert result["error"] == "api_error"
    assert no_real_sleep == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_graph.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.agent.graph'`.

- [ ] **Step 3: Write the graph**

Create `core/agent/graph.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_graph.py -v`
Expected: PASS (all 15 tests).

- [ ] **Step 5: Commit**

```bash
git add core/agent/graph.py tests/test_agent_graph.py
git commit -m "feat(agent): add core.agent.graph -- LangGraph tool-calling loop"
```

---

### Task 7: Reduce `core/agent/llm_adapter.py` to build state and invoke the graph

**Files:**
- Modify: `core/agent/llm_adapter.py`
- Test: `tests/test_llm_adapter.py`

**Interfaces:**
- Consumes: `core.agent.graph.build_graph` (Task 6); `_provider.get_llm()` (Tasks 4/5).
- Produces: `generate(system_prompt: str, user_prompt: str, tools: list[BaseTool]) -> GenerationResult` — signature and `GenerationResult` shape unchanged (Global Constraints), so `plan_generator.py` needs no change.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_llm_adapter.py` with:

```python
"""Tests for core.agent.llm_adapter: builds the LangGraph graph (core.agent.graph) for
the configured provider and translates its final state into GenerationResult.
core.agent.graph itself is never touched here -- llm_adapter.agent_graph.build_graph is
monkeypatched to return a fake compiled graph with a scripted final state.
"""
import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from core.agent import llm_adapter
from core.agent.schemas import PlanFood, PlanPropose


class FakeCompiledGraph:
    def __init__(self, final_state):
        self.final_state = final_state
        self.invoke_calls = []

    def invoke(self, initial_state, config=None):
        self.invoke_calls.append((initial_state, config))
        return self.final_state


@pytest.fixture
def fake_build_graph(monkeypatch):
    def _install(final_state):
        fake_graph = FakeCompiledGraph(final_state)
        monkeypatch.setattr(llm_adapter.agent_graph, "build_graph", lambda *a, **k: fake_graph)
        return fake_graph

    return _install


def test_generate_returns_the_plan_from_the_final_state_on_success(fake_build_graph):
    plan = PlanPropose(foods=[PlanFood(description="Apple", fdc_id="1", meal="snack", grams=100.0)])
    fake_build_graph({"plan": plan, "error": None})

    result = llm_adapter.generate("system", "user", [])

    assert result == llm_adapter.GenerationResult(plan, None)


@pytest.mark.parametrize("error", ["rate_limited", "timeout", "api_error", "invalid_output"])
def test_generate_returns_the_error_from_the_final_state(fake_build_graph, error):
    fake_build_graph({"plan": None, "error": error})

    result = llm_adapter.generate("system", "user", [])

    assert result == llm_adapter.GenerationResult(None, error)


def test_generate_builds_the_initial_state_with_system_and_user_messages(fake_build_graph):
    fake_graph = fake_build_graph({"plan": None, "error": "timeout"})

    llm_adapter.generate("sys prompt", "user prompt", [])

    initial_state, config = fake_graph.invoke_calls[0]
    assert isinstance(initial_state["messages"][0], SystemMessage)
    assert initial_state["messages"][0].content == "sys prompt"
    assert isinstance(initial_state["messages"][1], HumanMessage)
    assert initial_state["messages"][1].content == "user prompt"
    assert initial_state["turn"] == 0
    assert initial_state["tool_was_called"] is False
    assert initial_state["plan"] is None
    assert initial_state["error"] is None
    assert config["recursion_limit"] >= 50


def test_generate_returns_api_error_if_the_graph_itself_raises(monkeypatch):
    """Defense in depth for the "never raises" contract: core.agent.graph's own nodes
    already turn every LLM/tool failure into a state["error"] string, but LangGraph's
    runtime can still raise between node executions on its own (e.g. GraphRecursionError
    if a provider ever violated tool_choice badly enough to blow the turn budget) --
    that exception happens outside any node's try/except, so generate() must catch it too,
    not just trust the graph's final_state["error"] to always be reachable."""

    class RaisingGraph:
        def invoke(self, initial_state, config=None):
            raise RuntimeError("graph blew up")

    monkeypatch.setattr(llm_adapter.agent_graph, "build_graph", lambda *a, **k: RaisingGraph())

    result = llm_adapter.generate("system", "user", [])

    assert result == llm_adapter.GenerationResult(None, "api_error")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_llm_adapter.py -v`
Expected: FAIL — `llm_adapter` has no `agent_graph` attribute yet (still the old hand-rolled `_provider`/`_call_provider` loop), and `generate()`'s current signature/behavior don't match.

- [ ] **Step 3: Reduce the module**

Replace `core/agent/llm_adapter.py` with:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_llm_adapter.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Run the full suite to catch anything downstream**

Run: `venv/Scripts/python.exe -m pytest tests -v`
Expected: everything passes except `tests/test_agent_tool_schema.py`, which Task 8 removes.

- [ ] **Step 6: Commit**

```bash
git add core/agent/llm_adapter.py tests/test_llm_adapter.py
git commit -m "refactor(llm_adapter): reduce generate() to building state + invoking the graph"
```

---

### Task 8: Remove `core/agent/tool_schema.py`

**Files:**
- Delete: `core/agent/tool_schema.py`
- Delete: `tests/test_agent_tool_schema.py`

**Interfaces:**
- Nothing left imports `core.agent.tool_schema` after Tasks 4–7 (its `ToolDeclaration`/`ToolCall`/`build_tool_declaration`/`build_submit_plan_declaration` are replaced by LangChain's own `@tool`/`bind_tools`/`AIMessage.tool_calls` — see Discovery notes).

- [ ] **Step 1: Verify nothing else references it**

Run: `grep -rn "tool_schema" core tests --include=*.py`
Expected: only `core/agent/tool_schema.py` and `tests/test_agent_tool_schema.py` themselves. If anything else shows up, stop and investigate before deleting — this plan's scope (Global Constraints) assumed only those two files touch it, confirmed at planning time by the same grep.

- [ ] **Step 2: Delete both files**

```bash
git rm core/agent/tool_schema.py tests/test_agent_tool_schema.py
```

- [ ] **Step 3: Run the full suite**

Run: `venv/Scripts/python.exe -m pytest tests -v`
Expected: PASS, no collection errors (nothing imports the deleted module).

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove core.agent.tool_schema -- superseded by LangChain's own tool schema generation"
```

---

## Post-implementation fixes (found by the final whole-branch review, applied before Task 9)

Executing this plan (subagent-driven development, 2026-08-26) surfaced findings a task-scoped review can't catch — cross-task interface correctness against the *actual* installed SDK behavior, not just against each task's own tests. All of the following were fixed in one consolidated pass and are already reflected in the code blocks above and in the real files:

- **Critical:** `gemini.classify_exception` didn't recognize `langchain_core.exceptions.ModelRateLimitError` — what `ChatGoogleGenerativeAI` actually raises for a real 429, verified live against the installed `langchain-google-genai` 4.3.5. The original Task 4 code and its test both used the pre-migration `google.api_core.exceptions`-era assumption that a raw `genai_errors.ClientError(code=429)` is what reaches this function; in production it's wrapped first. Fixed by checking `ModelRateLimitError` first, keeping the raw check as a fallback.
- **Important:** `llm_adapter.generate()`'s try/except originally wrapped only `compiled.invoke(...)`, not `get_llm()`/`build_graph()` — narrower than the pre-migration loop's guard, which covered model/tool-declaration construction too. Widened to cover both.
- **Important:** `graph.py`'s `route_after_agent` checked `tool_calls` before the turn-overflow check, so a forced-turn response that isn't `submit_plan` would loop instead of finalizing after exactly one forced call (bounded only by `_RECURSION_LIMIT`, not by the intended `MAX_AUTO_TURNS + 1`). Reordered.
- **Important:** `gemini.classify_exception` didn't recognize raw `httpx.TimeoutException`/`httpx.ConnectError` — with `max_retries=0` disabling the SDK's own retry, Gemini had zero resilience to network blips (asymmetric with Groq, which already classified its own transient exceptions correctly). Added.
- **Minor:** stale docstrings in `core/agent/providers/__init__.py`, `core/agent/errors.py`, and `tests/test_plan_view.py` still described the deleted hand-rolled protocol or the pre-migration `llm_adapter._provider` patching pattern. Updated.
- **Minor:** `requirements.txt` now declares `google-genai` explicitly (see Task 1, above).
- **Minor:** two spots in `tests/test_agent_graph.py` used `[x] * N` (N references to one object, silently deduped by LangGraph's `add_messages` reducer) instead of a list comprehension — fixed so the turn-budget tests actually exercise a growing history.

Full detail (who found what, the exact fix, the re-review verdict) is in the SDD ledger for this plan run, not reproduced here.

---

### Task 9: Full regression pass + one real (manual) end-to-end check

**Files:** none (verification only).

- [ ] **Step 1: Run the full automated suite**

Run: `venv/Scripts/python.exe -m pytest tests -v`
Expected: 100% pass, zero warnings about `google.generativeai` deprecation (confirms Task 4 fully dropped that import).

- [ ] **Step 2: Manually verify against a real provider (needs a populated `.env`)**

This is the one thing no fake can cover: whether `tool_choice="submit_plan"` actually forces the tool call against the *real* Gemini and Groq APIs (structurally verified against both SDKs' `bind_tools` in this plan's Discovery notes, but never invoked live).

Run: `venv/Scripts/python.exe main.py monday` once with `LLM_PROVIDER=gemini` in `.env`, and once with `LLM_PROVIDER=groq`.
Expected both times: a JSON plan printed (not an error line). If either prints `Plan generation failed (invalid_output): ...`, re-check `bind_tools(..., tool_choice=SUBMIT_PLAN_TOOL_NAME)`'s translation for that provider (Discovery notes) — this is exactly the forced-final-turn path (`MAX_AUTO_TURNS` exhausted) if it only fails after a long pause, or the model refusing tool use entirely if it fails on the very first call.

- [ ] **Step 3: Confirm the Streamlit app still boots**

Run: `venv/Scripts/python.exe -m streamlit run app.py` and generate one plan through the UI.
Expected: no `ImportError`/`AttributeError` from `core.agent.*` or `core.tools.usda_tool` (the `developing-with-streamlit` skill covers any Streamlit-specific issues, out of scope for this plan).

No commit for this task — it's verification, not a change. If Step 2 or 3 surfaces a real bug, fix it as its own small commit and re-run the full suite before considering this plan done.
