"""Tests for data.usda.nutrients."""
import warnings

import pytest

from data.usda import nutrients as usda_nutrients

# Real /food/2620254 response (CHICKEN GRAVY, CHICKEN, Branded), foodNutrients only.
# Each entry nests the nutrient number as a string under "nutrient", with "amount"
# as a sibling key -- the real FDC API shape, not a flattened mock.
CHICKEN_GRAVY_FOOD_NUTRIENTS = [
    {
        "type": "FoodNutrient",
        "nutrient": {"id": 1008, "number": "208", "name": "Energy", "rank": 300, "unitName": "kcal"},
        "id": 32752606,
        "amount": 65.0,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {"id": 1093, "number": "307", "name": "Sodium, Na", "rank": 5800, "unitName": "mg"},
        "id": 32752607,
        "amount": 468.0,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {
            "id": 1258,
            "number": "606",
            "name": "Fatty acids, total saturated",
            "rank": 9700,
            "unitName": "g",
        },
        "id": 32752611,
        "amount": 0.81,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {
            "id": 1005,
            "number": "205",
            "name": "Carbohydrate, by difference",
            "rank": 1110,
            "unitName": "g",
        },
        "id": 32752605,
        "amount": 4.84,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {"id": 1114, "number": "328", "name": "Vitamin D (D2 + D3)", "rank": 8700, "unitName": "µg"},
        "id": 32752608,
        "amount": 0.0,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {"id": 1003, "number": "203", "name": "Protein", "rank": 600, "unitName": "g"},
        "id": 32752603,
        "amount": 1.61,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {
            "id": 1257,
            "number": "605",
            "name": "Fatty acids, total trans",
            "rank": 15400,
            "unitName": "g",
        },
        "id": 32752610,
        "amount": 0.0,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {"id": 1253, "number": "601", "name": "Cholesterol", "rank": 15700, "unitName": "mg"},
        "id": 32752609,
        "amount": 8.0,
    },
    {
        "type": "FoodNutrient",
        "nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)", "rank": 800, "unitName": "g"},
        "id": 32752604,
        "amount": 4.03,
    },
]


def test_extract_macros_matches_chicken_gravy_sample():
    """Real API shape: nutrient.number is a string, amount is a sibling key."""
    macros = usda_nutrients.extract_macros(CHICKEN_GRAVY_FOOD_NUTRIENTS)

    assert macros == {"kcal": 65.0, "protein_g": 1.61, "fat_g": 4.03, "carbs_g": 4.84}


def test_extract_macros_defaults_missing_nutrient_to_zero_and_warns():
    """A macro absent from foodNutrients (e.g. carbs on a pure-fat food) -> 0.0, with a warning."""
    food_nutrients_without_carbs = [
        entry for entry in CHICKEN_GRAVY_FOOD_NUTRIENTS if entry["nutrient"]["number"] != usda_nutrients.CARBS_G
    ]

    with pytest.warns(UserWarning, match="carbs"):
        macros = usda_nutrients.extract_macros(food_nutrients_without_carbs)

    assert macros["carbs_g"] == 0.0
    assert macros == {"kcal": 65.0, "protein_g": 1.61, "fat_g": 4.03, "carbs_g": 0.0}


def test_extract_macros_returns_all_zero_and_warns_four_times_when_empty():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        macros = usda_nutrients.extract_macros([])

    assert macros == {"kcal": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0}
    assert len(caught) == 4


def test_extract_macros_ignores_non_matching_number_type():
    """An int 208 (not the string "208") must not match ENERGY_KCAL -- guards against loose equality."""
    with pytest.warns(UserWarning):
        macros = usda_nutrients.extract_macros(
            [{"nutrient": {"number": 208, "name": "Energy"}, "amount": 999.0}]
        )

    assert macros["kcal"] == 0.0


# --- kcal fallback chain (Foundation Foods that omit nutrient number "208") ---

# Real /food/2346401-shaped response (potatoes, Foundation): energy is reported only
# via Atwater General/Specific Factors (ids 2047/2048), never "208".
POTATO_FOOD_NUTRIENTS = [
    {"nutrient": {"id": 1003, "number": "203", "name": "Protein"}, "amount": 2.05},
    {"nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)"}, "amount": 0.1},
    {"nutrient": {"id": 1005, "number": "205", "name": "Carbohydrate, by difference"}, "amount": 17.5},
    {"nutrient": {"id": 2047, "number": "957", "name": "Energy (Atwater General Factors)"}, "amount": 79.0},
    {"nutrient": {"id": 2048, "number": "958", "name": "Energy (Atwater Specific Factors)"}, "amount": 77.0},
]


def test_extract_macros_falls_back_to_atwater_general_factors_when_208_absent():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        macros = usda_nutrients.extract_macros(POTATO_FOOD_NUTRIENTS)

    assert macros["kcal"] == 79.0
    assert not caught  # no warning at all: 203/204/205 present, kcal resolved via fallback


def test_extract_macros_falls_back_to_atwater_specific_factors_when_general_absent():
    food_nutrients = [
        entry for entry in POTATO_FOOD_NUTRIENTS if entry["nutrient"]["number"] != usda_nutrients.ATWATER_GENERAL_NUM
    ]

    macros = usda_nutrients.extract_macros(food_nutrients)

    assert macros["kcal"] == 77.0


def test_extract_macros_falls_back_to_nutrient_id_1008_when_number_208_absent():
    """Some responses key the same Energy (kcal) nutrient by id 1008 without a "number" field."""
    food_nutrients = [
        {"nutrient": {"id": 1008, "name": "Energy"}, "amount": 65.0},
        {"nutrient": {"id": 1003, "number": "203", "name": "Protein"}, "amount": 1.61},
    ]

    macros = usda_nutrients.extract_macros(food_nutrients)

    assert macros["kcal"] == 65.0


def test_extract_macros_falls_back_to_kj_divided_by_4_184_when_no_kcal_field_present():
    food_nutrients = [
        {"nutrient": {"id": 1062, "number": "268", "name": "Energy", "unitName": "kJ"}, "amount": 418.4},
        {"nutrient": {"id": 1003, "number": "203", "name": "Protein"}, "amount": 1.61},
    ]

    macros = usda_nutrients.extract_macros(food_nutrients)

    assert macros["kcal"] == pytest.approx(100.0)


def test_extract_macros_prefers_208_over_atwater_fallbacks_when_both_present():
    food_nutrients = CHICKEN_GRAVY_FOOD_NUTRIENTS + [
        {"nutrient": {"id": 2047, "number": "957", "name": "Energy (Atwater General Factors)"}, "amount": 999.0},
    ]

    macros = usda_nutrients.extract_macros(food_nutrients)

    assert macros["kcal"] == 65.0  # the "208" value, not the 957 one


def test_extract_macros_estimates_kcal_via_atwater_formula_when_no_energy_field_at_all():
    """No 208/1008/2047/2048/268 field anywhere -- estimate from the macros we do have."""
    food_nutrients = [
        {"nutrient": {"id": 1003, "number": "203", "name": "Protein"}, "amount": 10.0},
        {"nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)"}, "amount": 5.0},
        {"nutrient": {"id": 1005, "number": "205", "name": "Carbohydrate, by difference"}, "amount": 20.0},
    ]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        macros = usda_nutrients.extract_macros(food_nutrients)

    assert macros["kcal"] == 4 * 10.0 + 9 * 5.0 + 4 * 20.0
    assert not caught  # Atwater estimate counts as resolved, no warning


def test_extract_macros_warns_once_when_no_energy_source_or_macros_available():
    """Nothing to compute kcal from at all (not even a partial macro) -- 0.0 with one warning."""
    food_nutrients = [
        {"nutrient": {"id": 1093, "number": "307", "name": "Sodium, Na"}, "amount": 100.0},
    ]

    with pytest.warns(UserWarning, match="energy .kcal. unavailable"):
        macros = usda_nutrients.extract_macros(food_nutrients)

    assert macros["kcal"] == 0.0
