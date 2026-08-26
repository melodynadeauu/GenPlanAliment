# GenPlanAliment

Agent IA de planification alimentaire quotidienne. Un LLM (Gemini 2.5 Flash, secours
Groq) compose le plan ; tout calcul de sécurité (cible calorique, plancher, exclusions)
est déterministe, en Python — voir `docs/architecture.md` pour le détail du graphe et
le Dossier de défense pour la justification de chaque choix.

## Installation

```bash
python -m venv venv
venv\Scripts\activate            # Windows ; source venv/bin/activate sur macOS/Linux
pip install -r requirements.txt
copy .env.example .env           # puis remplir USDA_API_KEY, GEMINI_API_KEY, GROQ_API_KEY
python -m data.activity.seed_activity_calendar
```

## Lancement

```bash
streamlit run app.py
```

## Décisions d'architecture

Voir le Dossier de défense (D1–D10) pour la justification complète. Résumé :

- **LLM** : Gemini 2.5 Flash primaire, Groq en secours (`LLM_PROVIDER` dans `.env`) — un adaptateur unique, portable vers Azure OpenAI en changeant une variable.
- **Orchestration** : LangGraph — le graphe *est* le schéma d'architecture (`core/agent/graph.py`, `docs/architecture.md`).
- **Calcul métabolique** : Mifflin-St Jeor (constante sexe neutre, sexe biologique non collecté par minimisation des données) + MET du Compendium of Physical Activities, additif et quotidien, jamais un facteur d'activité hebdomadaire.
- **UI** : Streamlit, avec une règle stricte de couches — `core/` n'importe jamais `streamlit`.

## Garde-fous

| Réf. | Garde-fou | Où |
|---|---|---|
| G1 | Plancher calorique (1200 kcal) + déficit plafonné (500 kcal ou 25% du TDEE) | `core/nutrition/targets.py` |
| G2 | Aliments détestés exclus en Python, jamais délégué au LLM | `core/agent/guardrails.py` |
| G3 | Tous les totaux recalculés depuis USDA, jamais l'arithmétique du LLM | `core/agent/graph.py::resolve_recompute_node` |
| G4 | Avis de non-responsabilité médicale | Prompt système + pied de page UI |
| G5 | Bornes plausibles sur âge/poids/taille | `ui/components/sidebar_profile.py` |
| G6 | Assainissement des préférences avant insertion dans le prompt | `core/agent/guardrails.py::sanitize_preference_items` |
| G7 | Max 2 tentatives puis mode dégradé avec avertissement visible | `core/agent/graph.py` |

Mode démo : bouton "Plan de démo" dans la barre du haut, recharge un plan déjà généré
(`fixtures/demo_plan.py`) sans appel LLM ni réseau — filet de sécurité anti-quota.

## Limites connues (assumées, pas des oublis)

- Sexe biologique non collecté — voir D5 du Dossier de défense (±83 kcal sur le BMR, dans la marge d'erreur de la formule).
- Seules 4 macros (kcal, protéines, lipides, glucides) sont exposées au LLM — voir D10 (portée prototype).
- Base sédentaire fixe à ×1.2 — ne distingue pas un métier physique d'un travail de bureau.
- Toutes les activités du Compendium ne sont pas graduées (ex. yoga) — l'intensité n'a alors aucun effet, avec une note visible.

## Tests

```bash
pytest -v
```

Les tests couvrent la logique déterministe sécurité-critique (`core/nutrition/`,
`core/agent/guardrails.py`, `core/agent/graph.py`) et le client USDA. Pas de tests UI
Streamlit.
