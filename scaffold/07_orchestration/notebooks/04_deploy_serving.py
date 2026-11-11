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

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("schema", "experian_auto")
dbutils.widgets.text("endpoint_prefix", "experian")
dbutils.widgets.text("app_name", "experian-copilot")
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
PREFIX = dbutils.widgets.get("endpoint_prefix").strip()
APP_NAME = dbutils.widgets.get("app_name").strip()
assert CATALOG and SCHEMA, "catalog and schema parameters are required"

ENDPOINTS = {
    f"{PREFIX}-residual-value": "residual_value_model",
    f"{PREFIX}-days-to-turn":   "days_to_turn_model",
    f"{PREFIX}-default-risk":   "default_risk_model",
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

# COMMAND ----------
# Let the Co-Pilot app's service principal query the endpoints.
try:
    app_sp = w.apps.get(APP_NAME).service_principal_client_id
    for endpoint in ENDPOINTS:
        ep_id = w.serving_endpoints.get(endpoint).id
        w.api_client.do("PATCH", f"/api/2.0/permissions/serving-endpoints/{ep_id}", body={
            "access_control_list": [{"service_principal_name": app_sp, "permission_level": "CAN_QUERY"}]})
    print(f"Granted CAN_QUERY on {len(ENDPOINTS)} endpoints to app SP {app_sp}")
except Exception as e:
    print(f"NOTE: could not grant the app SP endpoint access ({e})")
