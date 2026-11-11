# 04 — Mosaic AI Models

Three models power the Co-Pilot App, all trained on `feat_vehicle_fusion` (from
`02_visual_prep`):

| Model | Target | Used by App module |
|---|---|---|
| **residual_value** | estimated resale value | Price & Risk |
| **days_to_turn**   | predicted days to sell | Acquire |
| **default_risk**   | P(default) for a loan on this VIN's segment | Price & Risk (lenders) |

The job's `train_models` task (`../07_orchestration/notebooks/03_train_models.py`) trains
all three with scikit-learn gradient-boosted trees, logs them to MLflow and registers them in
the Unity Catalog model registry. `deploy_serving` (`04_deploy_serving.py`) then
points the Model Serving endpoints the app calls at the latest versions.

> These are demo-grade models on synthetic data. The point is the end-to-end wiring
> (feature table → training → registry → serving → app), not predictive accuracy.

Reference metrics from the captured run: default-risk AUC 0.90, days-to-turn MAE 4.0 days,
residual MAE $932 (`../../evidence/04b_mlflow_runs.md`).

## Registered model names (UC)

- `<catalog>.<schema>.residual_value_model`
- `<catalog>.<schema>.days_to_turn_model`
- `<catalog>.<schema>.default_risk_model`

## Serving endpoints

- `<prefix>-residual-value`
- `<prefix>-days-to-turn`
- `<prefix>-default-risk`

(`<prefix>` = bundle variable `endpoint_prefix`, default `experian`; endpoints scale to zero.)
