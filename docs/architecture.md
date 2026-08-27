# Architecture diagram — Agent Meal Prep

Data flow from the user profile to the displayed plan. Each box maps to a real
module (named in parentheses) — this diagram and `core/agent/graph.py` are the
same structure, not a drawing made after the fact.

```mermaid
flowchart TD
    UI["Streamlit UI\n(app.py, ui/)"] -->|profile, day, preferences| PG["plan_generator.py"]
    SQLITE[("SQLite\nmeal_prep.db\nactivity_calendar")] -->|today's activity| PG
    JSON[("food_preferences.json")] -->|likes/dislikes| PG
    PG -->|BMR→TDEE→target, G1| GRAPH["core/agent/graph.py"]

    subgraph GRAPH["LangGraph graph"]
        direction TB
        N1["1 · load_context"] --> N2["agent (LLM)"]
        N2 <-->|tool calls| TOOL["USDA tool + cache"]
        N2 --> N3["collect_proposal"]
        N3 --> N4["resolve_recompute (G3)"]
        N4 --> N5["validate_guardrails (G1/G2/G-exists)"]
        N5 -->|non-compliant, attempt < 2| N2
        N5 -->|compliant| N6["finalize"]
        N5 -->|attempts exhausted| N6b["degrade (G7)"]
    end

    USDA[("USDA FoodData Central API\n(1000 req/h)")] <-->|search/get, cached| TOOL
    GRAPH -->|plan + guardrails| PV["plan_view.py"]
    PV -->|meals, totals, guardrails| UI

    classDef llm fill:#e0eeeb,stroke:#0e6a5a;
    classDef store fill:#eef2f1,stroke:#71817c;
    class N2 llm;
    class SQLITE,JSON,USDA store;
```

## Possible evolutions (out of current scope)

- Human-in-the-loop: a human validation node between `validate_guardrails` and `finalize`.
- Multi-agent: a second specialized agent (e.g. macros) alongside node 2.
- RAG: no document corpus in the requirements — not built, listed here as an extension.
- Multi-user support, authentication, a full weekly plan, a grocery list, cloud
  deployment, a vector store, fine-tuning.
