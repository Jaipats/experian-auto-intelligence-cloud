# Evidence — Stage 4: Mosaic AI models (live Model Serving predictions)

_Real invocations of the three READY Model Serving endpoints, using an actual feature row for VIN `RUU340BML37JXA5WT` — Toyota Camry 2020, FL, clean title, 70,240 mi, ACCS 84._

**Model input (dataframe_split):**
```json
{
  "dataframe_split": {
    "columns": [
      "make",
      "model",
      "title_brand",
      "state",
      "model_year",
      "mileage",
      "owner_count",
      "accident_count",
      "auction_count",
      "accs_score",
      "local_market_share_pct",
      "local_avg_days_to_turn",
      "local_vio_count",
      "segment_avg_apr",
      "segment_avg_ltv_pct",
      "segment_default_rate",
      "segment_delinquency_rate"
    ],
    "data": [
      [
        "Toyota",
        "Camry",
        "Clean",
        "FL",
        2020,
        70240,
        2,
        0,
        1,
        84,
        1.74,
        62,
        23924,
        9.05,
        90.7,
        0,
        0
      ]
    ]
  }
}
```

## `experian-residual-value` — Predicted residual value ($)

Response:
```json
{
  "predictions": [
    22403.145486585607
  ]
}
```

## `experian-days-to-turn` — Predicted days-to-turn (days)

Response:
```json
{
  "predictions": [
    64.7583042232227
  ]
}
```

## `experian-default-risk` — Predicted default probability

Response:
```json
{
  "predictions": [
    0
  ]
}
```
