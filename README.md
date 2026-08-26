# GenPlanAliment

AI agent for daily meal planning. An LLM (Gemini 2.5 Flash, Groq as fallback)
composes the plan; every safety calculation (calorie target, floor, exclusions) is
deterministic Python — see `docs/architecture.md` for the graph and the Dossier de
défense for the reasoning behind each choice.

## Installation

```bash
python -m venv venv
venv\Scripts\activate            # Windows; source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env           # then fill in USDA_API_KEY, GEMINI_API_KEY, GROQ_API_KEY
python -m data.activity.seed_activity_calendar
```

## Running it

```bash
streamlit run app.py
```

## Architecture decisions

See the Dossier de défense (D1–D10) for the full reasoning. Summary:

- **LLM**: Gemini 2.5 Flash primary, Groq as fallback (`LLM_PROVIDER` in `.env`) — a single adapter, portable to Azure OpenAI by changing an environment variable.
- **Orchestration**: LangGraph — the graph *is* the architecture diagram (`core/agent/graph.py`, `docs/architecture.md`).
- **Metabolic calculation**: Mifflin-St Jeor (sex-neutral constant; biological sex isn't collected, per data minimization) + Compendium of Physical Activities METs, additive and daily, never a weekly activity factor.
- **UI**: Streamlit, with a strict layering rule — `core/` never imports `streamlit`.

## Guardrails

| Ref. | Guardrail | Where |
|---|---|---|
| G1 | Calorie floor (1200 kcal) + capped deficit (500 kcal or 25% of TDEE) | `core/nutrition/targets.py` |
| G2 | Disliked foods excluded in Python, never delegated to the LLM | `core/agent/guardrails.py` |
| G3 | Every total recomputed from USDA, never the LLM's own arithmetic | `core/agent/graph.py::resolve_recompute_node` |
| G4 | Medical disclaimer | System prompt + UI footer |
| G5 | Plausible bounds on age/weight/height | `ui/components/sidebar_profile.py` |
| G6 | Preferences sanitized before entering the prompt | `core/agent/guardrails.py::sanitize_preference_items` |
| G7 | Max 2 attempts, then degraded mode with a visible warning | `core/agent/graph.py` |

Demo mode: the "Demo plan" button in the top bar reloads a plan that was already
generated (`fixtures/demo_plan.py`), no LLM call or network — the quota fallback.

## Known limits (assumed, not oversights)

- Biological sex isn't collected — see D5 of the Dossier de défense (±83 kcal on the BMR, within the formula's own error margin).
- Only 4 macros (kcal, protein, fat, carbs) are exposed to the LLM — see D10 (prototype scope).
- Sedentary base is fixed at ×1.2 — doesn't distinguish a physical job from a desk job.
- Not every Compendium activity is graded (e.g. yoga) — intensity then has no effect, with a visible note.

## Tests

```bash
pytest -v
```

Tests cover the safety-critical deterministic logic (`core/nutrition/`,
`core/agent/guardrails.py`, `core/agent/graph.py`) and the USDA client. No Streamlit
UI tests.
