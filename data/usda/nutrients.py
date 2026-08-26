"""Extract macronutrients from a USDA FoodData Central foodNutrients list.

FDC nutrient numbers, e.g. from https://fdc.nal.usda.gov/ (the `nutrient.number`
field of the API is a string, not an int -- constants below are strings so the
comparison against parsed JSON matches).

Lives under data.usda (not core.nutrition) because it's a parser for USDA's specific
response shape, not a nutrition domain calculation -- and data.usda.cache/client need
MACRO_FIELDS themselves, to tell a cached entry apart from one written before a field
was added here (see data.usda.client.get_nutrition's self-healing cache).
"""
import warnings

ENERGY_KCAL = "208"
PROTEIN_G = "203"
FAT_G = "204"
CARBS_G = "205"

# Public (no leading underscore): data.usda.cache/client compare a cached entry's keys
# against MACRO_FIELDS.values() to detect a row cached before a field was added here.
MACRO_FIELDS = {
    ENERGY_KCAL: "kcal",
    PROTEIN_G: "protein_g",
    FAT_G: "fat_g",
    CARBS_G: "carbs_g",
}


def extract_macros(food_nutrients: list[dict]) -> dict:
    """Pull kcal/protein/fat/carbs out of a `foodNutrients` list (the shape
    returned by data.usda.client.get_nutrition() for /food/{fdcId}: each entry
    has a "nutrient" dict with a "number" string, and an "amount" sibling key).

    Returns {"kcal": ..., "protein_g": ..., "fat_g": ..., "carbs_g": ...}.

    These values are always per 100g of the food, regardless of dataType
    (Branded, Foundation, SR Legacy, ...) -- that's an FDC convention, not a
    unit to convert.

    Any of the four missing from `food_nutrients` defaults to 0.0 and emits a
    warnings.warn instead of raising.
    """
    macros = {field: 0.0 for field in MACRO_FIELDS.values()}
    found = set()

    for entry in food_nutrients:
        number = entry.get("nutrient", {}).get("number")
        field = MACRO_FIELDS.get(number)
        if field is not None:
            macros[field] = float(entry["amount"])
            found.add(field)

    for number, field in MACRO_FIELDS.items():
        if field not in found:
            warnings.warn(f"USDA nutrient {number} ({field}) missing from foodNutrients; defaulting to 0.0")

    return macros
