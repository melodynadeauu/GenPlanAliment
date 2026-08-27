"""Extract macronutrients from a USDA FoodData Central foodNutrients list.
`nutrient.number` in the API is a string, so the constants below are too.
"""
import warnings

ENERGY_KCAL = "208"
PROTEIN_G = "203"
FAT_G = "204"
CARBS_G = "205"

# Public: cache/client compare cached keys against MACRO_FIELDS.values() to
# detect stale rows.
MACRO_FIELDS = {
    ENERGY_KCAL: "kcal",
    PROTEIN_G: "protein_g",
    FAT_G: "fat_g",
    CARBS_G: "carbs_g",
}

# Fallback energy fields when "208" is absent, checked in this order (id first,
# then number).
ENERGY_KCAL_ID = 1008  # same nutrient as number "208", keyed by id instead
ATWATER_GENERAL_ID = 2047
ATWATER_GENERAL_NUM = "957" 
ATWATER_SPECIFIC_ID = 2048
ATWATER_SPECIFIC_NUM = "958"
ENERGY_KJ_NUM = "268"  # Energy (kJ) -- convert to kcal
KJ_PER_KCAL = 4.184


def _find_energy_fallback_kcal(food_nutrients: list[dict]) -> float | None:
    """Kcal from a fallback energy field, in priority order (1008, Atwater
    general, Atwater specific, kJ). None if none present."""
    by_key = {}

    for entry in food_nutrients:
        nutrient = entry.get("nutrient", {})
        number = nutrient.get("number")
        nutrient_id = nutrient.get("id")
        amount = entry.get("amount")
        if amount is None:
            continue  # no value to fall back to; also narrows amount for float() below

        if nutrient_id == ENERGY_KCAL_ID and "1008" not in by_key:
            by_key["1008"] = float(amount)
        elif (nutrient_id == ATWATER_GENERAL_ID or number == ATWATER_GENERAL_NUM) and "957" not in by_key:
            by_key["957"] = float(amount)
        elif (nutrient_id == ATWATER_SPECIFIC_ID or number == ATWATER_SPECIFIC_NUM) and "958" not in by_key:
            by_key["958"] = float(amount)
        elif number == ENERGY_KJ_NUM and "268" not in by_key:
            by_key["268"] = float(amount) / KJ_PER_KCAL

    for key in ("1008", "957", "958", "268"):
        if key in by_key:
            return by_key[key]
    return None


def extract_macros(food_nutrients: list[dict]) -> dict:
    """Pull kcal/protein/fat/carbs (per 100g) out of a `foodNutrients` list.

    Missing protein/fat/carbs default to 0.0 with a warning. kcal falls back
    through id 1008, Atwater factors, or kJ before being estimated via
    4*protein + 9*fat + 4*carbs, and only then defaults to 0.0 with a warning.
    """
    macros = {field: 0.0 for field in MACRO_FIELDS.values()}
    found = set()

    for entry in food_nutrients:
        number = entry.get("nutrient", {}).get("number")
        field = MACRO_FIELDS.get(number)
        if field is not None:
            macros[field] = float(entry["amount"])
            found.add(field)

    if "kcal" not in found:
        fallback_kcal = _find_energy_fallback_kcal(food_nutrients)
        if fallback_kcal is not None:
            macros["kcal"] = fallback_kcal
            found.add("kcal")

    if "kcal" not in found and (found & {"protein_g", "fat_g", "carbs_g"}):
        macros["kcal"] = 4 * macros["protein_g"] + 9 * macros["fat_g"] + 4 * macros["carbs_g"]
        found.add("kcal")

    for number, field in MACRO_FIELDS.items():
        if field in found:
            continue
        if field == "kcal":
            warnings.warn(
                "USDA energy (kcal) unavailable from foodNutrients (no 208/1008/2047/2048/268 "
                "field and not enough macros for an Atwater estimate); defaulting to 0.0"
            )
        else:
            warnings.warn(f"USDA nutrient {number} ({field}) missing from foodNutrients; defaulting to 0.0")

    return macros
