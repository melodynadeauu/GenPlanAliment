"""Hardcoded generated meal plan -- stand-in for the LangGraph agent's output."""

DEMO_PLAN = {
    "day": "wednesday",
    "generated_at": "09:41",
    "target_kcal": 1806,
    "total_kcal": 1792,
    "total_protein_g": 132,
    "meals": [
        {
            "name": "Breakfast",
            "kcal": 512,
            "items": [
                {"food": "Oatmeal, cooked", "grams": 150, "kcal": 220, "source": "FDC 169705", "source_status": "ok"},
                {"food": "Blueberries, fresh", "grams": 100, "kcal": 57, "source": "FDC 173946", "source_status": "ok"},
            ],
        },
        {
            "name": "Lunch",
            "kcal": 618,
            "items": [
                {"food": "Chicken breast, grilled", "grams": 180, "kcal": 297, "source": "FDC 171077", "source_status": "ok"},
                {"food": "Brown rice, cooked", "grams": 150, "kcal": 167, "source": "FDC 168880", "source_status": "ok"},
                {"food": "Broccoli, steamed", "grams": 120, "kcal": 41, "source": "FDC 170379", "source_status": "ok"},
            ],
        },
        {
            "name": "Dinner",
            "kcal": 542,
            "items": [
                {"food": "Salmon, baked", "grams": 150, "kcal": 312, "source": "FDC 175167", "source_status": "ok"},
                {"food": "Quinoa, cooked", "grams": 140, "kcal": 172, "source": "estimated (FDC unavailable)", "source_status": "warn"},
            ],
        },
        {
            "name": "Snack",
            "kcal": 120,
            "items": [
                {"food": "Almonds, plain", "grams": 20, "kcal": 120, "source": "FDC 170567", "source_status": "ok"},
            ],
        },
    ],
    "guardrails": [
        {"status": "ok", "message": "Calorie target within safe limits"},
        {"status": "ok", "message": "No disliked foods in this plan"},
        {"status": "warn", "message": "Quinoa uses estimated nutrition. USDA data was unavailable for this item."},
    ],
}
