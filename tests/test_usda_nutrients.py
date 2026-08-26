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
