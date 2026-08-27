# `feat/wip-ui-usda-scaler` — our changes, and the rebase onto `main`

Written 2026-08-27, after rebasing this branch onto `origin/main` (`5c44c1c`).

## TL;DR

- Everything that was uncommitted is now committed (two commits on this branch).
- The branch is rebased onto current `main`. Tests: **170 passed**.
- Both sides independently built a **gram/portion adjuster** and a **USDA kcal
  fallback**. Main's versions won; ours were dropped from the branch.
- Our version is preserved intact on `backup/wip-ui-usda-scaler-pre-rebase`.
- The UI work — which had no counterpart on main — survived in full.

## Branch layout

| Branch | Head | What it is |
| --- | --- | --- |
| `feat/wip-ui-usda-scaler` | `96f5acb` | The live branch, rebased onto main. Our UI work + main's core work. |
| `backup/wip-ui-usda-scaler-pre-rebase` | `24b46e1` | Frozen pre-rebase snapshot. **Our scaler and kcal fallback live here and nowhere else.** |
| `main` | `5c44c1c` | Fast-forwarded to `origin/main`. |

Nothing was pushed — this repo is local-only per `CLAUDE.md`.

To read our dropped scaler:

```bash
git show backup/wip-ui-usda-scaler-pre-rebase:core/agent/graph.py
```

## The two commits on this branch

**`af86688` — Add UI energy chain, week fixtures, and repo docs**
Originally titled "Add kcal gram scaler + accumulated working-tree changes". It
was reworded after the rebase, because the scaler it described no longer exists
in it. What is left: `ui/energy.py`, `ui/components/energy_chain.py`, the
presentation pass over `top_bar` / `totals_row` / `meal_plan` / `guardrails_bar`
/ `week_strip` / `theme` / `layout`, richer `fixtures/demo_week.py`, `CLAUDE.md`
(the no-push rule), `.claude/launch.json` (port 8502 + `runOnSave`), and
`case_study_requirement.txt`.

**`96f5acb` — Rework UI shell: masthead, week strip, energy chain, icon set**
The formerly-uncommitted working tree. Page now reads top to bottom in the
product's own order: masthead → training week → calorie target → the plan.

- `ui/icons.py` (new): inline SVG icon set, 16px box, 1.5px stroke,
  `currentColor`, replacing emoji so an icon inherits its row's colour.
- `ui/theme.py`: large token/CSS pass; day-card height tokens; dropped the old
  `RADIUS`/`SHADOW` constants.
- `ui/components/week_strip.py`: expandable week strip (`KEY_WEEK_EXPANDED`),
  per-day cards with burn text.
- Renames: `render_top_bar` → `render_masthead`, `render_totals_row` →
  `render_plan_summary`.
- `ui/state.py`: `KEY_PLAN_DAY` ties a generated plan to the day it was
  generated for; `KEY_WEEK_EXPANDED`.
- `app.py`: rewired to the new component names, plainer user-facing error copy.
- `ui/components/sidebar_preferences.py`: **the preferences tab bug fix** (below).
- `tests/test_preferences_tab_roundtrip.py` (new): what each tab may write.

Net against main: **22 files, +1732 / −425**.

## The preferences tab bug

Only one of the two multiselects is mounted at a time. Switching tabs unmounts
the other, and a real browser resets an unmounted widget to its default — the
empty list — while leaving its key in `session_state`. The old
`if key not in st.session_state` seed therefore found the key, left it empty,
showed no chips, and let the next edit write that empty list over
`food_preferences.json`.

Fix: track mount state explicitly (`_mounted_key`), so returning to a tab
re-seeds it from the file, and save only from an `on_change` callback that a
real user edit triggers.

Caveat worth knowing: `AppTest` keeps widget state across the round trip and
never reproduces this, so the new tests **pass against the broken version too**.
The fix was verified in the browser instead — tab round-trip, all 12 chips
return, file untouched.

`data/preferences/food_preferences.json` is committed with an emptied
`"dislikes"`. That is runtime residue of this same bug, not an intentional edit.
To restore it:

```bash
git checkout cdba58b -- data/preferences/food_preferences.json
```

## Gram adjustment: ours vs main's

Both sides solved the same problem — a plan that misses `target_kcal` only on
portion size — and neither knew about the other. **Main's is the one in the
tree.**

| | Ours (`scale_portions_node`) | Main (`adjust_portions_node`) — kept |
| --- | --- | --- |
| Fires | Immediately on a kcal-only violation, **before** any LLM retry | Only after `MAX_ATTEMPTS` is exhausted, as the last step before `degrade` |
| Bound | Scale factor clamped to `[0.5, 2.0]` | Gap must be within `ADJUST_MAX_FRACTION = 0.15` of target |
| Gram rounding | `round(g * factor, 1)` — 0.1 g | Nearest 5 g (`ADJUST_ROUND_GRAMS`), floor 5 g |
| Totals after scaling | Computed analytically: `total * factor` | Routes back through `resolve_recompute` — re-derived from USDA |
| Re-entry guard | `scaled`, reset each retry (can run once per attempt) | `adjusted`, never reset (once per `generate()`) |
| Handles `unresolved` fdc_ids | No — predates that feature | Yes — refuses to adjust when any exist |
| State keys | `kcal_violated`, `dislikes_violated`, `scaled` | `adjustable`, `adjusted` |

### Why main's is the better default

1. **G3 integrity.** Ours sets `resolved_total_kcal = total * factor` — a number
   the code computed rather than one USDA returned. Main re-runs
   `resolve_recompute`, so every number shown to the user still comes from the
   nutrition tool. With main's 5 g rounding an analytic total would be visibly
   wrong anyway.
2. **Realistic portions.** Main caps the correction at 15% off target on the
   grounds that a bigger gap means the wrong foods, not the wrong portions.
   Ours would happily double a portion (factor 2.0) to rescue a plan that was
   never close.
3. **Serving sizes that read as chosen.** 5 g steps look human-picked; 0.1 g
   steps look like a multiplication artifact.
4. **Loop safety.** `adjusted` is never reset, so the node runs at most once per
   generation and a residual violation falls through to `degrade`.

### Where ours was better, and the follow-up worth considering

Ours fires **before** burning `MAX_ATTEMPTS` LLM calls. Main only adjusts after
those attempts are spent, so a plan that is 3% off target still costs two full
LLM round trips before a deterministic fix that never needed the LLM at all.

The obvious hybrid — main's node, fired early — is **not implemented here**. It
would mean routing to `adjust_portions` on the first kcal-only violation when
`adjustable` is true, keeping main's re-resolve, 5 g rounding and `adjusted`
guard exactly as they are. Worth raising with Melody before touching it, since
it changes the retry economics of every generation.

## Conflicts, and how each was resolved

Eight conflicts across the two replayed commits.

| File | Resolution | Why |
| --- | --- | --- |
| `core/agent/graph.py` | **Main's, wholesale** | All five hunks were the rival portion adjusters. Our commit touched nothing else in this file, so taking the file whole also swept up a stray auto-merged `add_edge("scale", ...)` that would have dangled. |
| `core/agent/llm_adapter.py` | **Main's** | Only the initial-state keys for the two rival nodes. Ours (`kcal_violated`, `dislikes_violated`, `scaled`) died with our node. |
| `data/usda/client.py` | **Main's** | Same cache-staleness rule on both sides (missing macro field, or zero-kcal with other macros present). Main extracted it into `_is_stale()`; verified equivalent before taking it. |
| `data/usda/nutrients.py` | **Main's** | Both built the same kcal fallback chain (208 → id 1008 → Atwater 957/958 → kJ 268 → Atwater estimate). Main's is single-pass and warns when it finally defaults to 0.0; ours returned 0.0 silently. |
| `tests/test_usda_nutrients.py` | **Main's** | Parallel tests for the same behaviour; main's match the implementation we kept. |
| `tests/test_usda_client.py` | **Main's** | Same. |
| `tests/test_agent_graph.py` | **Main's** | Ours tested `scale_portions_node`, which no longer exists. |
| `ui/components/sidebar_preferences.py` | **Merged by hand — both sides kept** | The only genuine merge. See below. |

### The one real merge

Main added USDA validation on newly added preference terms, driven off the old
`selected != active_items` comparison. We had replaced that comparison with an
`on_change` callback, because comparing widget state to the file fires on any
run where the two disagree and silently writes the stale list back.

Keeping only one side would have lost either the validation or the bug fix. So
main's validation now lives **inside** our callback: it checks
`find_unknown_new_items`, refuses to save an unrecognised term, and catches the
store's like/dislike overlap `ValueError`.

One wrinkle this forced: `st.error()` does nothing inside an `on_change`
callback, because the callback runs before the script reruns. The message now
travels through `session_state[_ERROR_KEY]` and is rendered after the widget.

Validation only ever checks *added* items, so removing a chip makes no USDA
call — which is why the round-trip tests still run offline.

## Verification

- `pytest -q` → **170 passed**, 8 warnings (all intentional — tests assert them).
- App boots at `localhost:8502`, no console errors.
- Sidebar renders: profile fields, `Likes · 12` with all chips.
- Tab round-trip (Likes → Dislikes → Likes) returns all 12 chips and leaves
  `food_preferences.json` untouched — the bug fix, confirmed in a real browser.
- `af86688`'s tree is byte-identical to the pre-reword commit it replaced.

## Open items

1. `docs/usda-kcal-fallback-plan.md` is our planning doc for the kcal fallback
   we no longer ship. Kept as a record of the reasoning; delete it if the
   superseded design is more confusing than useful.
2. `data/preferences/food_preferences.json` — restore `dislikes` (command above).
3. Early-firing portion adjustment — the hybrid described above.
4. `main`'s commit `5c44c1c` is titled "Add portion adjuted node" (typo,
   upstream). Left alone.
