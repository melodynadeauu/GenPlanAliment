# Schéma d'architecture — Agent Meal Prep

Flux de données du profil utilisateur jusqu'au plan affiché. Chaque boîte correspond
à un module réel du code (voir le nom entre parenthèses) -- ce diagramme et le graphe
`core/agent/graph.py` sont la même structure, pas un dessin fait après coup (D2).

```mermaid
flowchart TD
    UI["Streamlit UI\n(app.py, ui/)"] -->|profil, jour, préférences| PG["plan_generator.py"]
    SQLITE[("SQLite\nmeal_prep.db\nactivity_calendar")] -->|activité du jour| PG
    JSON[("food_preferences.json")] -->|likes/dislikes| PG
    PG -->|BMR→TDEE→cible, G1| GRAPH["core/agent/graph.py"]

    subgraph GRAPH["Graphe LangGraph"]
        direction TB
        N1["1 · load_context"] --> N2["agent (LLM)"]
        N2 <-->|tool calls| TOOL["USDA tool + cache"]
        N2 --> N3["collect_proposal"]
        N3 --> N4["resolve_recompute (G3)"]
        N4 --> N5["validate_guardrails (G1/G2)"]
        N5 -->|non conforme, tentative < 2| N2
        N5 -->|conforme| N6["finalize"]
        N5 -->|tentatives épuisées| N6b["degrade (G7)"]
    end

    USDA[("USDA FoodData Central API\n(1000 req/h)")] <-->|search/get, avec cache| TOOL
    GRAPH -->|plan + garde-fous| PV["plan_view.py"]
    PV -->|meals, totals, guardrails| UI

    classDef llm fill:#e0eeeb,stroke:#0e6a5a;
    classDef store fill:#eef2f1,stroke:#71817c;
    class N2 llm;
    class SQLITE,JSON,USDA store;
```

## Évolutions possibles (hors périmètre actuel)

- Human-in-the-loop : nœud de validation humaine entre `validate_guardrails` et `finalize`.
- Multi-agent : un second agent spécialisé (ex. macros) en parallèle du nœud 2.
- RAG : aucun corpus documentaire dans l'énoncé — non construit, placé ici comme extension.
- Multi-utilisateurs, authentification, plan hebdomadaire complet, liste d'épicerie,
  déploiement cloud, base vectorielle, fine-tuning.
