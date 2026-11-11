# Evidence — Stage 6: Databricks App (Inventory & Risk Co-Pilot)

_Captured 2026-09-25T21:51:07Z (VIN lookup re-captured 2026-11-11). Live HTTP responses from the deployed app at `https://experian-copilot-7474648980404788.aws.databricksapps.com` (authenticated calls). The app fuses all six stages: Lakebase serving, Unity Catalog analytics, Model Serving, and Genie._

## GET /api/health — resource wiring (all four backends live)
```json
{
    "status": "ok",
    "sql_configured": true,
    "genie_configured": true,
    "lakebase_configured": true
}
```

## GET /api/vin/RUU340BML37JXA5WT: per-VIN lookup **served_by lakebase** + live model predictions
_Re-captured 2026-11-11 after the switch to the Lakebase **synced table** (`auto.vin_serving_online`, kept in step with the Lakeflow `vin_serving` view)._
```json
{
    "source": "live",
    "served_by": "lakebase",
    "vehicle": {
        "vin": "RUU340BML37JXA5WT",
        "make": "Toyota",
        "model": "Camry",
        "trim": "XSE",
        "model_year": 2020,
        "mileage": 70240,
        "owner_count": 2,
        "accident_count": 0,
        "title_brand": "Clean",
        "odometer_rollback_flag": 0,
        "auction_count": 1,
        "accs_score": 84,
        "state": "FL",
        "garaged_state": "FL",
        "garaged_zip": "32801",
        "last_reported_date": "2024-12-28T00:00:00+00:00",
        "local_market_share_pct": 1.74,
        "local_avg_days_to_turn": 62.0,
        "local_vio_count": 23924.0,
        "segment_avg_apr": 9.05,
        "segment_avg_ltv_pct": 90.7,
        "segment_delinquency_rate": 0.0,
        "segment_default_rate": 0.0,
        "predicted_residual_value": 22403.0,
        "segment_default_risk": 0.0
    }
}
```

## GET /api/acquire?state=CA&body_style=SUV — ranked acquisition candidates (UC analytics + days-to-turn model)
```json
{
    "source": "live",
    "rows": [
        {
            "make": "Hyundai",
            "model": "Tucson",
            "model_year": 2018,
            "body_style": "SUV",
            "state": "CA",
            "avg_days_to_turn": 17,
            "market_share_pct": 1.54,
            "avg_accs_score": 65.4,
            "clean_title_rate": 0.923,
            "avg_orig_amount": 28562.0
        },
        {
            "make": "Ford",
            "model": "Explorer",
            "model_year": 2015,
            "body_style": "SUV",
            "state": "CA",
            "avg_days_to_turn": 20,
            "market_share_pct": 1.18,
            "avg_accs_score": 42.5,
            "clean_title_rate": 0.769,
            "avg_orig_amount": 28205.0
        },
        {
            "make": "Ford",
            "model": "Explorer",
            "model_year": 2015,
            "body_style": "SUV",
            "state": "CA",
            "avg_days_to_turn": 31,
            "market_share_pct": 1.69,
            "avg_accs_score": 42.5,
            "clean_title_rate": 0.769,
            "avg_orig_amount": 28205.0
        },
        {
            "make": "Subaru",
            "model": "Outback",
            "model_year": 2025,
            "body_style": "SUV",
            "state": "CA",
            "avg_days_to_turn": 36,
            "market_share_pct": 1.67,
            "avg_accs_score": 80.5,
            "clean_title_rate": 0.846,
            "avg_orig_amount": 35321.0
        },
        {
            "make": "Subaru",
            "model": "Outback",
            "model_year": 2021,
            "body_style": "SUV",
            "state": "CA",
            "avg_days_to_turn": 36,
            "market_share_pct": 0.89,
            "avg_accs_score": 81.8,
            "clean_title_rate": 1.0,
            "avg_orig_amount": 28387.0
        }
    ]
}
```

## GET /api/market-radar?region=West — lender share + underserved segments (UC analytics)
```json
{
    "source": "live",
    "lender_share": [
        {
            "lender_type": "Bank",
            "loans": 2191,
            "avg_apr": 9.8,
            "delinquency_rate": 0.058
        },
        {
            "lender_type": "Captive",
            "loans": 1337,
            "avg_apr": 9.73,
            "delinquency_rate": 0.065
        },
        {
            "lender_type": "Credit Union",
            "loans": 915,
            "avg_apr": 9.75,
            "delinquency_rate": 0.056
        },
        {
            "lender_type": "Fintech",
            "loans": 876,
            "avg_apr": 9.69,
            "delinquency_rate": 0.064
        }
    ],
    "underserved": [
        {
            "make": "Toyota",
            "model": "Sienna",
            "model_year": 2019,
            "avg_days_to_turn": 88,
            "lender_count": 1,
            "market_share_pct": 2.06
        },
        {
            "make": "Toyota",
            "model": "Sienna",
            "model_year": 2017,
            "avg_days_to_turn": 87,
            "lender_count": 1,
            "market_share_pct": 1.59
        },
        {
            "make": "Toyota",
            "model": "Sienna",
            "model_year": 2025,
            "avg_days_to_turn": 82,
            "lender_count": 1,
            "market_share_pct": 1.67
        },
        {
            "make": "Toyota",
            "model": "Sienna",
            "model_year": 2025,
            "avg_days_to_turn": 80,
            "lender_count": 1,
            "market_share_pct": 1.49
        },
        {
            "make": "Toyota",
            "model": "Sienna",
            "model_year": 2020,
            "avg_days_to_turn": 80,
            "lender_count": 1,
            "market_share_pct": 0.51
        },
        {
            "make": "Ram",
            "model": "1500",
            "model_year": 2021,
            "avg_days_to_turn": 80,
            "lender_count": 1,
            "market_share_pct": 6.52
        },
        {
            "make": "Toyota",
            "model": "Camry",
            "model_year": 2022,
            "avg_days_to_turn": 78,
            "lender_count": 1,
            "market_share_pct": 3.67
        },
        {
            "make": "Ford",
            "model": "F-150",
            "model_year": 2021,
            "avg_days_to_turn": 77,
            "lender_count": 1,
            "market_share_pct": 2.56
        },
        {
            "make": "Ram",
            "model": "1500",
            "model_year": 2022,
            "avg_days_to_turn": 76,
            "lender_count": 1,
            "market_share_pct": 3.49
        },
        {
            "make": "Toyota",
            "model": "Sienna",
            "model_year": 2016,
            "avg_days_to_turn": 76,
            "lender_count": 1,
            "market_share_pct": 0.78
        }
    ]
}
```
