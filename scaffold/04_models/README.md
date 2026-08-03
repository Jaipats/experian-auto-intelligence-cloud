# 04 — Mosaic AI Models

Three models power the Co-Pilot App, all trained on `feat_vehicle_fusion` (from
`02_visual_prep`):

| Model | Target | Used by App module |
|---|---|---|
| **residual_value** | estimated resale value | Price & Risk |
| **days_to_turn**   | predicted days to sell | Acquire |
| **default_risk**   | P(default) for a loan on this VIN's segment | Price & Risk (lenders) |

`train_models.py` trains all three with scikit-learn (gradient-boosted trees), logs them to
MLflow, and registers them in Unity Catalog Model Registry. `serve_models.sh` deploys the
registered models to Model Serving endpoints the App calls.

> These are demo-grade models on synthetic data — the point is the end-to-end wiring
> (feature table → training → registry → serving → app), not predictive accuracy.

## Run

```bash
# In a Databricks notebook or via Databricks Connect:
DBX_PROFILE=fe-vm-experian-agent-demo uv run --python 3.12 \
  --with scikit-learn --with mlflow --with pandas \
  --with "databricks-connect>=16.4,<17.0" \
  train_models.py

# Then deploy the registered models to serving endpoints:
bash serve_models.sh
```

## Registered model names (UC)

- `experian_agent_demo_catalog.auto.residual_value_model`
- `experian_agent_demo_catalog.auto.days_to_turn_model`
- `experian_agent_demo_catalog.auto.default_risk_model`

## Serving endpoints

- `experian-residual-value`
- `experian-days-to-turn`
- `experian-default-risk`
