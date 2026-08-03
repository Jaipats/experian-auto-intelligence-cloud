# Databricks notebook source
# MAGIC %md
# MAGIC # 04 - Deploy / update Model Serving endpoints
# MAGIC Creates or updates the three serving endpoints to the LATEST registered version
# MAGIC of each model. Idempotent: safe to re-run as part of the end-to-end job.
# COMMAND ----------
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput, ServedEntityInput,
)

CATALOG = "experian_agent_demo_catalog"
SCHEMA = "auto"

ENDPOINTS = {
    "experian-residual-value": "residual_value_model",
    "experian-days-to-turn":   "days_to_turn_model",
    "experian-default-risk":   "default_risk_model",
}

w = WorkspaceClient()


def latest_version(model_full_name: str) -> str:
    versions = w.model_versions.list(full_name=model_full_name)
    nums = [int(v.version) for v in versions]
    return str(max(nums))


for endpoint, model in ENDPOINTS.items():
    full = f"{CATALOG}.{SCHEMA}.{model}"
    ver = latest_version(full)
    served = ServedEntityInput(
        entity_name=full,
        entity_version=ver,
        workload_size="Small",
        scale_to_zero_enabled=True,
    )
    config = EndpointCoreConfigInput(name=endpoint, served_entities=[served])

    existing = None
    try:
        existing = w.serving_endpoints.get(endpoint)
    except Exception:
        existing = None

    if existing is None:
        print(f"creating {endpoint} -> {full} v{ver}")
        w.serving_endpoints.create(name=endpoint, config=config)
    else:
        print(f"updating {endpoint} -> {full} v{ver}")
        w.serving_endpoints.update_config(
            name=endpoint, served_entities=[served])

print("Serving deployment requested for all endpoints (rollout continues async).")
