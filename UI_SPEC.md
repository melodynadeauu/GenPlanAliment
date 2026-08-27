# Spec UI Streamlit — Agent Meal Prep

Spec d'implémentation pour Claude Code. Portée = **UI seulement**, toutes les
valeurs sont hardcodées (fixtures françaises). But: reproduire la maquette
([lien artifact](https://claude.ai/code/artifact/046fb928-6b99-4a6c-9b62-20f64fae2e2a))
avec une structure évolutive — quand la vraie logique (agent LangGraph, USDA,
SQLite) arrivera, elle remplacera les fixtures sans toucher aux composants UI.

Contraintes du projet à respecter (issues du dossier de défense) :
- Tout le code (noms de fichiers, modules, fonctions, variables, docstrings,
  commentaires) **en anglais**. Les valeurs hardcodées affichées à l'utilisateur
  (labels, données démo) **en français**.
- Aucune logique métier dans `app.py` — c'est un chef d'orchestre de rendu.
- Aucun appel LLM/API dans le corps du script : tout déclenchement se fait
  dans un `if st.button(...)`, résultat rangé dans `st.session_state`
  (règle anti-piège Streamlit du dossier D3).
- `core/` (agent, tools, data, guardrails) reste vide/non touché à cette étape
  — cette spec ne construit que la couche présentation.

---

## 1. Arborescence à créer

```
app.py                          # entry point Streamlit — layout only, no logic

ui/
  __init__.py
  theme.py                      # design tokens (colors, fonts, spacing) as constants
  layout.py                     # page_config + global CSS injection
  state.py                      # session_state schema + init/get/set helpers
  components/
    __init__.py
    top_bar.py                  # brand mark, day selector, activity summary, generate button
    sidebar_profile.py          # profile form (age, weight, height, goal)
    sidebar_preferences.py      # segmented control + search filter + scrollable chip list
    totals_row.py                # 4 stat cards (target kcal, actual kcal, protein, meal count)
    meal_plan.py                 # scrollable list of meal cards
    guardrails_bar.py            # guardrail badges + disclaimer footer

fixtures/
  __init__.py
  demo_profile.py               # hardcoded profile dict (FR values)
  demo_preferences.py           # hardcoded likes/dislikes lists (FR values)
  demo_week.py                  # hardcoded weekly activity calendar (FR values)
  demo_plan.py                  # hardcoded generated meal plan (FR values)
```

Rationale : `ui/` ne connaît jamais où les données viennent (fixture
aujourd'hui, `core/agent` demain) — chaque composant reçoit ses données en
paramètres, jamais en important une fixture directement. Ça garde `ui/`
swappable en un seul point (`app.py`).

---

## 2. `ui/theme.py` — design tokens

Reprendre exactement les valeurs de la maquette (cohérence avec les autres
livrables du dossier). Exposer comme dict Python + une fonction qui génère le
CSS à injecter.

```python
"""Design tokens shared across all UI components."""

COLORS = {
    "paper": "#f3f6f5",
    "surface": "#ffffff",
    "surface_2": "#eef2f1",
    "ink": "#16211e",
    "ink_2": "#4b5a56",
    "ink_3": "#71817c",
    "line": "#d7e0dd",
    "line_strong": "#b9c7c3",
    "accent": "#0e6a5a",
    "accent_ink": "#0a5245",
    "accent_soft": "#e0eeeb",
    "ochre": "#8a6412",
    "ochre_soft": "#f5eedd",
    "danger": "#9d3a2d",
    "danger_soft": "#f7e6e2",
}

RADIUS = "6px"
SHADOW = "0 1px 2px rgba(20,40,35,.05), 0 8px 24px -16px rgba(20,40,35,.28)"

FONT_SANS = "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace"
FONT_SERIF = "'Newsreader', Georgia, serif"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap"
)


def build_global_css() -> str:
    """Return the <style> block injected once by ui/layout.py."""
    ...
```

`build_global_css()` doit notamment :
- importer `GOOGLE_FONTS_URL` via `@import`
- forcer `body`/`.stApp` en `background: COLORS["paper"]`, `font-family: FONT_SANS`
- retirer le padding par défaut de Streamlit (`.block-container { padding-top: ...; }`)
- styliser `.stButton>button` primaire pour matcher l'accent teal
- styliser les chips (voir §5) en classes CSS réutilisables (`.chip`, `.chip-accent`,
  `.chip-danger`, `.badge-ok`, `.badge-warn`)

---

## 3. `ui/layout.py` — squelette de page

Responsabilité unique : configurer la page et injecter le CSS. Appelé une
seule fois depuis `app.py`.

```python
"""Page configuration and global styling for the Streamlit app."""

import streamlit as st
from ui.theme import build_global_css


def configure_page() -> None:
    """Set page config and inject global CSS. Call once at the top of app.py."""
    st.set_page_config(
        page_title="Agent Meal Prep",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(f"<style>{build_global_css()}</style>", unsafe_allow_html=True)
```

---

## 4. `ui/state.py` — schéma `session_state`

Centralise TOUTES les clés de `session_state` pour éviter les strings
magiques dispersées. Chaque composant importe ces constantes, jamais une
string littérale.

```python
"""session_state schema for the app. Import keys from here, never hardcode strings."""

import streamlit as st

KEY_SELECTED_DAY = "selected_day"          # str, e.g. "mercredi"
KEY_ACTIVE_PREF_TAB = "active_pref_tab"    # str, "likes" | "dislikes"
KEY_PREF_FILTER = "pref_filter_query"      # str, search box content
KEY_GENERATED_PLAN = "generated_plan"      # dict | None — result of "Générer"
KEY_IS_GENERATING = "is_generating"        # bool — guards the button handler

DEFAULTS = {
    KEY_SELECTED_DAY: "mercredi",
    KEY_ACTIVE_PREF_TAB: "likes",
    KEY_PREF_FILTER: "",
    KEY_GENERATED_PLAN: None,
    KEY_IS_GENERATING: False,
}


def init_state() -> None:
    """Populate any missing session_state keys with their defaults. Idempotent."""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
```

Point d'évolution : quand `core/agent` existe, `KEY_GENERATED_PLAN` contiendra
le vrai résultat du graphe au lieu de `fixtures/demo_plan.py` — aucune autre
clé ne change.

---

## 5. Fixtures (`fixtures/`) — valeurs FR hardcodées

Chaque fixture retourne un objet Python simple (dict/list de dicts) — pas de
classe, pas de logique. Signature pensée pour matcher exactement ce que
`core/agent` retournera plus tard (même forme de données).

### `fixtures/demo_profile.py`
```python
"""Hardcoded profile — stand-in for the future editable profile form (F2)."""

DEMO_PROFILE = {
    "age": 45,
    "weight_kg": 100,
    "height_cm": 196,
    "goal": "Perte de poids",  # French label, shown as-is
}
```

### `fixtures/demo_preferences.py`
```python
"""Hardcoded food preferences — stand-in for food_preferences.json (F4)."""

DEMO_LIKES = [
    "poulet", "riz", "brocoli", "saumon", "quinoa", "avoine", "amandes",
    "bleuets", "dinde", "lentilles", "patate douce", "yogourt grec", "épinards",
]

DEMO_DISLIKES = [
    "fruits de mer", "agneau", "olives", "champignons",
]
```

### `fixtures/demo_week.py`
```python
"""Hardcoded weekly activity calendar — stand-in for SQLite activity_calendar (F3)."""

DEMO_WEEK = [
    {"day": "lundi", "label": "L", "activity": "Repos", "duration_min": 0, "intensity": None},
    {"day": "mardi", "label": "M", "activity": "Musculation", "duration_min": 40, "intensity": "modérée"},
    {"day": "mercredi", "label": "M", "activity": "Course à pied", "duration_min": 45, "intensity": "modérée"},
    {"day": "jeudi", "label": "J", "activity": "Repos", "duration_min": 0, "intensity": None},
    {"day": "vendredi", "label": "V", "activity": "Natation", "duration_min": 30, "intensity": "légère"},
    {"day": "samedi", "label": "S", "activity": "Vélo", "duration_min": 60, "intensity": "élevée"},
    {"day": "dimanche", "label": "D", "activity": "Repos", "duration_min": 0, "intensity": None},
]
```

### `fixtures/demo_plan.py`
```python
"""Hardcoded generated meal plan — stand-in for the LangGraph agent's output."""

DEMO_PLAN = {
    "day": "mercredi",
    "generated_at": "09:41",
    "model_label": "Gemini 2.5 Flash",
    "target_kcal": 1806,
    "total_kcal": 1792,
    "total_protein_g": 132,
    "meals": [
        {
            "name": "Déjeuner",
            "kcal": 512,
            "items": [
                {"food": "Flocons d'avoine, cuits", "grams": 150, "kcal": 220, "source": "FDC 169705", "source_status": "ok"},
                {"food": "Bleuets, frais", "grams": 100, "kcal": 57, "source": "FDC 173946", "source_status": "ok"},
            ],
        },
        {
            "name": "Dîner",
            "kcal": 618,
            "items": [
                {"food": "Poitrine de poulet, grillée", "grams": 180, "kcal": 297, "source": "FDC 171077", "source_status": "ok"},
                {"food": "Riz brun, cuit", "grams": 150, "kcal": 167, "source": "FDC 168880", "source_status": "ok"},
                {"food": "Brocoli, vapeur", "grams": 120, "kcal": 41, "source": "FDC 170379", "source_status": "ok"},
            ],
        },
        {
            "name": "Souper",
            "kcal": 542,
            "items": [
                {"food": "Saumon, cuit au four", "grams": 150, "kcal": 312, "source": "FDC 175167", "source_status": "ok"},
                {"food": "Quinoa, cuit", "grams": 140, "kcal": 172, "source": "estimation — FDC indisponible", "source_status": "warn"},
            ],
        },
        {
            "name": "Collation",
            "kcal": 120,
            "items": [
                {"food": "Amandes, nature", "grams": 20, "kcal": 120, "source": "FDC 170567", "source_status": "ok"},
            ],
        },
    ],
    "guardrails": [
        {"status": "ok", "message": "Déficit plafonné respecté"},
        {"status": "ok", "message": "Aucun aliment exclu détecté"},
        {"status": "warn", "message": "Quinoa estimé — FDC indisponible"},
    ],
}
```

`source_status` (`"ok" | "warn"`) et `guardrails[].status` (`"ok" | "warn"`)
pilotent la couleur du badge (accent vs ochre) — c'est le contrat que
`core/agent` devra respecter plus tard.

---

## 6. Composants (`ui/components/`)

Chaque composant est **une fonction pure de rendu** : elle prend des données
en paramètres et retourne éventuellement une valeur d'interaction (le
sélecteur de jour retourne le jour choisi, par ex.) — elle ne lit/écrit
`session_state` que pour SA PROPRE clé, jamais celle d'un autre composant.

### `ui/components/top_bar.py`
```python
"""Top bar: brand mark, day selector, activity summary, generate button."""

import streamlit as st

def render_top_bar(week: list[dict], selected_day: str) -> tuple[str, bool]:
    """Render the fixed top bar.

    Returns:
        (new_selected_day, generate_clicked)
    """
    ...
```
- Layout : `st.columns([2, 5, 2, 2])` ou équivalent pour brand / sélecteur de
  jour / résumé activité / bouton.
- Sélecteur de jour : 7 boutons courts (`st.button("L")`, etc.) ou
  `st.segmented_control` (Streamlit ≥1.34) si disponible dans la version
  installée — sinon fallback boutons. Le jour actif est stylé via une classe
  CSS (`.day-pill-active`) déclarée dans `theme.py`.
- Résumé activité : lit l'entrée de `week` correspondant à `new_selected_day`
  et affiche `"{activity} · {duration_min} min · intensité {intensity}"`.
- Bouton "Générer le plan" : `st.button("Générer le plan", type="primary")`
  — **ne déclenche rien ici**, retourne juste `True`/`False`; c'est
  `app.py` qui décide quoi faire avec (règle D3 anti-piège).

### `ui/components/sidebar_profile.py`
```python
"""Sidebar section: profile fields (F2)."""

import streamlit as st

def render_profile_section(profile: dict) -> None:
    """Render read-only-styled profile fields. Values are hardcoded for now."""
    ...
```
- `st.number_input` pour âge/poids/taille, `st.selectbox` pour objectif —
  valeurs par défaut = `fixtures.demo_profile.DEMO_PROFILE` (le dossier F2
  précise que l'énoncé donne les valeurs par défaut du formulaire, pas des
  constantes figées). Pas de logique de sauvegarde à ce stade — les widgets
  existent, leur valeur n'est pas encore persistée nulle part.

### `ui/components/sidebar_preferences.py`
```python
"""Sidebar section: scalable food preferences (likes/dislikes)."""

import streamlit as st

def render_preferences_section(likes: list[str], dislikes: list[str]) -> None:
    """Render the segmented tab + search filter + scrollable chip list."""
    ...
```
- Segmented control "J'aime (N) / Évite (N)" → écrit dans
  `state.KEY_ACTIVE_PREF_TAB`.
- `st.text_input` filtre → écrit dans `state.KEY_PREF_FILTER`, filtre la
  liste affichée (`str.lower()` substring match).
- Liste de chips dans **`st.container(height=160)`** (conteneur Streamlit
  natif à hauteur fixe et scroll interne — c'est le mécanisme qui reproduit
  la "liste scrollable" de la maquette sans JS custom). Chaque chip = un
  badge stylé (classe `.chip-accent` pour likes, `.chip-danger` pour
  dislikes) rendu via `st.markdown(..., unsafe_allow_html=True)`.

### `ui/components/totals_row.py`
```python
"""Four stat cards: target kcal, actual kcal, protein, meal count."""

import streamlit as st

def render_totals_row(plan: dict | None) -> None:
    """Render the totals row. If plan is None, show placeholder dashes."""
    ...
```
- `st.columns(4)`, chaque colonne = une carte stylée (`.stat-card`, classe
  CSS avec `border`, `border-radius`, `box-shadow` repris de `theme.py`).
- Si `plan is None` (aucune génération encore faite) : afficher `"—"` dans
  chaque carte plutôt que planter — c'est l'état initial avant le premier
  clic sur "Générer".

### `ui/components/meal_plan.py`
```python
"""Scrollable list of meal cards — the only part of the screen that scrolls."""

import streamlit as st

def render_meal_plan(plan: dict | None) -> None:
    """Render meals in a fixed-height scrollable container."""
    ...
```
- **`st.container(height=..., border=False)`** autour de la boucle sur
  `plan["meals"]` — c'est le mécanisme qui reproduit "seule cette zone
  scrolle" (contrainte explicite de l'utilisateur). Hauteur calculée pour
  remplir l'espace restant (valeur fixe raisonnable, ex. `420`, à ajuster
  visuellement — documenter dans le code que c'est une valeur à raffiner).
- Chaque repas = un bloc avec en-tête (nom + kcal) et lignes d'aliments
  (nom, grammes, kcal, badge source). Badge source coloré selon
  `item["source_status"]`.
- Si `plan is None` : afficher un message d'état vide
  (`"Aucun plan généré — clique sur *Générer le plan*."`).

### `ui/components/guardrails_bar.py`
```python
"""Fixed footer: guardrail badges + medical disclaimer."""

import streamlit as st

def render_guardrails_bar(plan: dict | None) -> None:
    """Render guardrail badges. Renders nothing but the disclaimer if plan is None."""
    ...
```
- Boucle sur `plan["guardrails"]`, badge pill coloré selon `status`
  (`ok` → accent, `warn` → ochre) — classes CSS `.badge-ok` / `.badge-warn`.
- Toujours afficher, même sans plan : `"Ceci n'est pas un avis médical."`

---

## 7. `app.py` — orchestration

```python
"""Streamlit entry point. Wires components together — no business logic here."""

import streamlit as st

from ui.layout import configure_page
from ui.state import init_state, KEY_SELECTED_DAY, KEY_GENERATED_PLAN
from ui.components.top_bar import render_top_bar
from ui.components.sidebar_profile import render_profile_section
from ui.components.sidebar_preferences import render_preferences_section
from ui.components.totals_row import render_totals_row
from ui.components.meal_plan import render_meal_plan
from ui.components.guardrails_bar import render_guardrails_bar

from fixtures.demo_profile import DEMO_PROFILE
from fixtures.demo_preferences import DEMO_LIKES, DEMO_DISLIKES
from fixtures.demo_week import DEMO_WEEK
from fixtures.demo_plan import DEMO_PLAN


def main() -> None:
    configure_page()
    init_state()

    selected_day, generate_clicked = render_top_bar(
        week=DEMO_WEEK,
        selected_day=st.session_state[KEY_SELECTED_DAY],
    )
    st.session_state[KEY_SELECTED_DAY] = selected_day

    if generate_clicked:
        # TODO(agent): replace DEMO_PLAN with core.agent.generate_plan(...)
        st.session_state[KEY_GENERATED_PLAN] = DEMO_PLAN

    with st.sidebar:
        render_profile_section(DEMO_PROFILE)
        render_preferences_section(DEMO_LIKES, DEMO_DISLIKES)

    plan = st.session_state[KEY_GENERATED_PLAN]
    render_totals_row(plan)
    render_meal_plan(plan)
    render_guardrails_bar(plan)


if __name__ == "__main__":
    main()
```

Note sur la règle D3 (piège Streamlit) : le seul endroit qui écrit
`KEY_GENERATED_PLAN` est le bloc `if generate_clicked:` — jamais un appel
inconditionnel exécuté à chaque rerun. C'est déjà la structure à respecter
quand `DEMO_PLAN` sera remplacé par un vrai appel agent (potentiellement
coûteux/lent).

---

## 8. Points d'extension (pour plus tard, ne pas implémenter maintenant)

| Aujourd'hui | Deviendra |
|---|---|
| `fixtures/demo_profile.py` | Formulaire éditable persistant en `st.session_state` + sauvegarde disque |
| `fixtures/demo_preferences.py` | Lecture/écriture de `food_preferences.json` (F4) |
| `fixtures/demo_week.py` | Requête SQLite `activity_calendar` (F3) |
| `fixtures/demo_plan.py` | Retour de `core.agent.generate_plan(profile, prefs, day)` (LangGraph) |
| `DEMO_PLAN` hardcodé dans `app.py` | Appel réel dans le bloc `if generate_clicked:`, avec spinner (`st.spinner`) et gestion d'erreur (F9) |

Aucun composant `ui/` n'a besoin de changer pour ces évolutions — seule la
provenance des données change dans `app.py`.

---

## 9. Checklist d'acceptation visuelle

- [ ] Aucun scroll de page — seule la liste des repas scrolle (via
      `st.container(height=...)`).
- [ ] Sélecteur de jour + bouton "Générer" en haut, pas dans la sidebar.
- [ ] Sidebar : profil (grille 2 colonnes) + préférences (segmented +
      filtre + liste scrollable de chips).
- [ ] Palette/typo identiques à `ui/theme.py` (paper/teal, IBM Plex +
      Newsreader).
- [ ] Avant tout clic sur "Générer" : cartes de totaux à `"—"`, message
      d'état vide dans la zone repas, disclaimer toujours visible.
- [ ] Après clic : données de `fixtures/demo_plan.py` affichées, badge
      ochre visible sur la ligne Quinoa (démontre le cas "FDC indisponible").

---

## 10. Dépendances

```
streamlit>=1.34   # pour st.container(height=...) et éventuellement segmented_control
```

Rien d'autre à cette étape (pas de `langgraph`, `google-generativeai`, etc. —
hors scope de cette spec UI).
