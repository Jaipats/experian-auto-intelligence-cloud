# Databricks notebook source
# MAGIC %pip install scikit-learn mlflow
# COMMAND ----------
# MAGIC %md
# MAGIC # 03 - Train & register models
# MAGIC Trains residual / days-to-turn / default-risk models on `feat_vehicle_fusion`, logs runs to the workspace experiment, and registers them in Unity Catalog.
# COMMAND ----------
# =============================================================================
# Train + register the three Co-Pilot models on feat_vehicle_fusion.
#   residual_value_model, days_to_turn_model, default_risk_model
# Logs to MLflow and registers in Unity Catalog Model Registry.
#
# Demo-grade: synthetic targets are derived from the features so the models have
# signal to learn. Swap in real Experian targets for production.
# =============================================================================
import os
import mlflow
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder

CATALOG = "experian_agent_demo_catalog"
SCHEMA = "auto"
PROFILE = os.environ.get("DBX_PROFILE", "fe-vm-experian-agent-demo")
EXPERIMENT = os.environ.get(
    "MLFLOW_EXPERIMENT",
    "/Users/jaideep.patel@databricks.com/experian_auto_models")

# Log experiments to the Databricks WORKSPACE (not a local ./mlruns dir) and
# register models in Unity Catalog.
mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(EXPERIMENT)

# ---- load feature table via Databricks Connect ----
# Running inside a Databricks Job: ambient spark + automatic MLflow tracking.
pdf = spark.table(f"{CATALOG}.{SCHEMA}.feat_vehicle_fusion").toPandas()
print(f"loaded feat_vehicle_fusion: {pdf.shape}")

CAT = ["make", "model", "body_style" if "body_style" in pdf.columns else "title_brand", "title_brand", "state"]
CAT = [c for c in dict.fromkeys(CAT) if c in pdf.columns]
NUM = [c for c in ["model_year", "mileage", "owner_count", "accident_count", "auction_count",
                   "accs_score", "local_market_share_pct", "local_avg_days_to_turn",
                   "local_vio_count", "segment_avg_apr", "segment_avg_ltv_pct",
                   "segment_delinquency_rate", "segment_default_rate"] if c in pdf.columns]

def make_pipeline(estimator):
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
         ("num", SimpleImputer(strategy="median"), NUM)])
    return Pipeline([("pre", pre), ("model", estimator)])

# ---- synthetic targets (replace with real Experian targets in prod) ----
rng = np.random.default_rng(42)
base_value = 40000 - (2025 - pdf["model_year"]) * 2500 - pdf["mileage"] * 0.06
base_value -= pdf["accident_count"] * 1500 + pdf["owner_count"] * 400
pdf["y_residual"] = np.clip(base_value + rng.normal(0, 1200, len(pdf)), 2000, 80000)
pdf["y_dtt"] = np.clip(pdf["local_avg_days_to_turn"].fillna(45)
                       + (100 - pdf["accs_score"]) * 0.3
                       + rng.normal(0, 5, len(pdf)), 5, 180)
p_default = (pdf["segment_default_rate"].fillna(0.03)
             + (pdf["accident_count"] > 2) * 0.05
             + (pdf["title_brand"] != "Clean") * 0.08)
pdf["y_default"] = (rng.random(len(pdf)) < np.clip(p_default, 0, 0.9)).astype(int)

def train_and_register(target, estimator, uc_name, metric_fn, metric_name, classifier=False):
    X = pdf[CAT + NUM]
    y = pdf[target]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    pipe = make_pipeline(estimator)
    with mlflow.start_run(run_name=uc_name):
        pipe.fit(Xtr, ytr)
        if classifier:
            pred = pipe.predict_proba(Xte)[:, 1]
        else:
            pred = pipe.predict(Xte)
        score = metric_fn(yte, pred)
        mlflow.log_metric(metric_name, float(score))
        signature = mlflow.models.infer_signature(Xtr.head(5), pred[:5])
        mlflow.sklearn.log_model(
            pipe, "model",
            serialization_format="cloudpickle",  # avoid skops trusted-types issue
            input_example=Xtr.head(2),
            signature=signature,
            registered_model_name=f"{CATALOG}.{SCHEMA}.{uc_name}")
        print(f"{uc_name}: {metric_name}={score:.4f}  registered as {CATALOG}.{SCHEMA}.{uc_name}")

train_and_register("y_residual", HistGradientBoostingRegressor(random_state=42),
                   "residual_value_model", mean_absolute_error, "mae")
train_and_register("y_dtt", HistGradientBoostingRegressor(random_state=42),
                   "days_to_turn_model", mean_absolute_error, "mae")
train_and_register("y_default", HistGradientBoostingClassifier(random_state=42),
                   "default_risk_model", roc_auc_score, "auc", classifier=True)

print("All three models trained and registered.")
