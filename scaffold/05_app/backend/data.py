"""Illustrative sample data so the UI is demoable before the UC tables / models /
Genie space are wired up. Every /api endpoint falls back to these on error."""

SAMPLE_ACQUIRE = [
    {"make": "Toyota", "model": "RAV4", "model_year": 2022, "body_style": "SUV", "state": "CA",
     "avg_days_to_turn": 21, "market_share_pct": 6.4, "avg_accs_score": 86, "clean_title_rate": 0.91,
     "avg_orig_amount": 31200, "predicted_days_to_turn": 19},
    {"make": "Honda", "model": "CR-V", "model_year": 2021, "body_style": "SUV", "state": "CA",
     "avg_days_to_turn": 24, "market_share_pct": 5.1, "avg_accs_score": 84, "clean_title_rate": 0.89,
     "avg_orig_amount": 28900, "predicted_days_to_turn": 23},
    {"make": "Tesla", "model": "Model Y", "model_year": 2022, "body_style": "SUV", "state": "CA",
     "avg_days_to_turn": 26, "market_share_pct": 7.8, "avg_accs_score": 88, "clean_title_rate": 0.94,
     "avg_orig_amount": 46500, "predicted_days_to_turn": 25},
]

SAMPLE_VIN = {
    "vin": "1HGxxxxxxxxxxxxxx", "make": "Honda", "model": "CR-V", "trim": "EX-L",
    "model_year": 2021, "mileage": 38120, "owner_count": 1, "accident_count": 0,
    "title_brand": "Clean", "odometer_rollback_flag": 0, "auction_count": 1,
    "accs_score": 90, "garaged_state": "CA",
    "predicted_residual_value": 27450, "segment_default_risk": 0.031,
}

SAMPLE_LENDER_SHARE = [
    {"lender_type": "Captive", "loans": 812, "avg_apr": 6.1, "delinquency_rate": 0.038},
    {"lender_type": "Bank", "loans": 640, "avg_apr": 7.3, "delinquency_rate": 0.052},
    {"lender_type": "Credit Union", "loans": 415, "avg_apr": 6.6, "delinquency_rate": 0.041},
    {"lender_type": "Fintech", "loans": 233, "avg_apr": 9.4, "delinquency_rate": 0.089},
]

SAMPLE_UNDERSERVED = [
    {"make": "Nissan", "model": "Altima", "model_year": 2019, "avg_days_to_turn": 58,
     "lender_count": 3, "market_share_pct": 2.1},
    {"make": "Ford", "model": "Explorer", "model_year": 2018, "avg_days_to_turn": 51,
     "lender_count": 4, "market_share_pct": 3.0},
]

# Richer Ask payload used when Genie isn't reachable — mirrors the live shape so the
# transparency panel (thinking / SQL / results / follow-ups) renders standalone.
SAMPLE_ASK = {
    "answer": "Genie is not configured yet. Once the Genie space is created and "
              "GENIE_SPACE_ID is set, this returns a live answer, Genie's reasoning, "
              "the generated SQL, the result table, and suggested follow-ups.",
    "description": "You want the top fastest-turning SUVs in California for the latest month.",
    "thoughts": "Interpreting the request as a ranking by avg_days_to_turn, filtered to "
                "body_style = 'SUV' and state = 'CA' for the most recent snapshot_month.",
    "sql": "SELECT make, model, model_year, avg_days_to_turn, market_share_pct\n"
           "FROM <catalog>.experian_auto.analytics_market_360\n"
           "WHERE body_style = 'SUV' AND state = 'CA'\n"
           "ORDER BY avg_days_to_turn ASC LIMIT 5",
    "row_count": 3,
    "result": {
        "columns": ["make", "model", "model_year", "avg_days_to_turn", "market_share_pct"],
        "rows": [
            ["Hyundai", "Tucson", "2018", "17", "2.4"],
            ["Ford", "Explorer", "2015", "20", "3.1"],
            ["Subaru", "Outback", "2021", "36", "2.9"],
        ],
    },
    "suggested_questions": [
        "Which of these have the highest ACCS condition score?",
        "How does their default rate compare?",
        "Show the same list for Texas",
    ],
}
