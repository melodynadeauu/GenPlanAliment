# USDA kcal fallback — implementation plan

Fix silent **0 kcal** foods when USDA stores energy under a field other than nutrient `"208"`, which causes inflated guardrail failures and `UserWarning: USDA nutrient 208 (kcal) missing…`.

## Problem

`get_nutrition_tool` → `data/usda/client.get_nutrition()` → `extract_macros(foodNutrients)`.

Today only nutrient **number `"208"`** is read for kcal. Many **Foundation Foods** report energy as:

| Nutrient id | Number | Name |
|-------------|--------|------|
| 1008 | 208 | Energy (kcal) — branded / legacy |
| 2047 | 957 | Energy (Atwater General Factors) |
| 2048 | 958 | Energy (Atwater Specific Factors) |
| — | 268 | Energy (kJ) |

Verified live on FDC `2346401` (potatoes): only **957/958** (ids 2047/2048), no 208.

**Search is not affected** — `search_food_tool` returns `{fdc_id, description}` only.

## Data flow

```
search_food_tool(query)     → fdc_id + description (no kcal)
get_nutrition_tool(fdc_id)  → extract_macros()  ← fix here
  → graph resolve_recompute (guardrails)
  → plan_view _build_item (UI totals)
  → usda_cache.db
```

## Implementation (done in this branch)

### 1. `data/usda/nutrients.py`

- Parse protein / fat / carbs from numbers `"203"`, `"204"`, `"205"` (unchanged).
- Resolve kcal via priority chain:
  1. number `"208"`
  2. nutrient id `1008`
  3. id `2047` or number `"957"`
  4. id `2048` or number `"958"`
  5. number `"268"` → divide by `4.184`
  6. Atwater estimate: `4×protein + 9×fat + 4×carbs` when macros present
  7. else `0.0` + single warning (`USDA energy (kcal) unavailable…`)
- Do **not** warn for missing 208 when a fallback succeeds.

### 2. `data/usda/client.py`

- Treat cached rows with `kcal == 0` but non-zero protein/fat/carbs as **stale**; refetch from USDA once.

### 3. `tests/test_usda_nutrients.py`

- Tests for each fallback path and preference of 208 over 957.

## Verification

```bash
.\venv\Scripts\python.exe -m pytest tests/test_usda_nutrients.py tests/test_usda_client.py -v
.\venv\Scripts\python.exe -m pytest -q
streamlit run app.py
```

1. Click **Generate plan** — fewer/no `208 missing` warnings in the terminal.
2. **Planned kcal** should be closer to **target kcal** (within ±10% more often).
3. Optional: delete `data/usda/usda_cache.db` if old zero-kcal rows persist (auto-refresh should handle most cases).

## Acceptance criteria

- [x] Foods with 2047/2048/268 no longer return `kcal: 0.0` when energy exists
- [x] Branded foods with `"208"` still pass (chicken gravy fixture)
- [x] Full pytest suite green (142 tests)
- [ ] Generate plan produces fewer degraded (yellow) warnings — verify manually

## Out of scope

- LLM portion tuning / extra guardrail retries
- UI copy in `plan_view.py` (keep core logic only)
- Search API changes

## Follow-ups (separate)

- Deterministic gram scaler after LLM submit to hit target kcal
- Stronger model for demo if Generate plan still misses target occasionally
