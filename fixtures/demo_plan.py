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
                {
                    "food": "Flocons d'avoine, cuits",
                    "grams": 150,
                    "kcal": 220,
                    "source": "FDC 169705",
                    "source_status": "ok",
                },
                {
                    "food": "Bleuets, frais",
                    "grams": 100,
                    "kcal": 57,
                    "source": "FDC 173946",
                    "source_status": "ok",
                },
            ],
        },
        {
            "name": "Dîner",
            "kcal": 618,
            "items": [
                {
                    "food": "Poitrine de poulet, grillée",
                    "grams": 180,
                    "kcal": 297,
                    "source": "FDC 171077",
                    "source_status": "ok",
                },
                {
                    "food": "Riz brun, cuit",
                    "grams": 150,
                    "kcal": 167,
                    "source": "FDC 168880",
                    "source_status": "ok",
                },
                {
                    "food": "Brocoli, vapeur",
                    "grams": 120,
                    "kcal": 41,
                    "source": "FDC 170379",
                    "source_status": "ok",
                },
            ],
        },
        {
            "name": "Souper",
            "kcal": 542,
            "items": [
                {
                    "food": "Saumon, cuit au four",
                    "grams": 150,
                    "kcal": 312,
                    "source": "FDC 175167",
                    "source_status": "ok",
                },
                {
                    "food": "Quinoa, cuit",
                    "grams": 140,
                    "kcal": 172,
                    "source": "estimation — FDC indisponible",
                    "source_status": "warn",
                },
            ],
        },
        {
            "name": "Collation",
            "kcal": 120,
            "items": [
                {
                    "food": "Amandes, nature",
                    "grams": 20,
                    "kcal": 120,
                    "source": "FDC 170567",
                    "source_status": "ok",
                },
            ],
        },
    ],
    "guardrails": [
        {
            "status": "ok",
            "message": "Déficit plafonné respecté",
        },
        {
            "status": "ok",
            "message": "Aucun aliment exclu détecté",
        },
        {
            "status": "warn",
            "message": "Quinoa estimé — FDC indisponible",
        },
    ],
}
