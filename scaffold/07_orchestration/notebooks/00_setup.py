# Databricks notebook source
# MAGIC %md
# MAGIC # 00 - Setup: schema, raw Volume, entitlements (row filter + column mask)
# MAGIC Idempotent first task of the end-to-end job. Creates the target schema and the `raw`
# MAGIC landing Volume, applies the entitlements template (`scaffold/06_sharing/entitlements.sql`:
# MAGIC contract table + `rf_state` row filter + `mask_orig_amount` column mask), and loads the
# MAGIC contract rows:
# MAGIC
# MAGIC * the deploying user and the Co-Pilot app's service principal: `full` tier, all states
# MAGIC * every principal in `full_access_principals` (comma-separated): `full`, all states
# MAGIC * `tenant_contracts`: JSON list of demo customers, e.g.
# MAGIC   `[{"principal": "<sp-application-id>", "customer": "Contoso Dealer Group", "tier": "standard", "states": ["CA","NV","AZ"]}]`
# MAGIC
# MAGIC Parameters arrive as job parameters (see `resources/experian_auto.job.yml`).
# COMMAND ----------
import json
import os

from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("schema", "experian_auto")
dbutils.widgets.text("app_name", "experian-copilot")
dbutils.widgets.text("full_access_principals", "")
dbutils.widgets.text("tenant_contracts", "[]")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
APP_NAME = dbutils.widgets.get("app_name").strip()
FULL_ACCESS = [p.strip() for p in dbutils.widgets.get("full_access_principals").split(",") if p.strip()]
TENANTS = json.loads(dbutils.widgets.get("tenant_contracts") or "[]")
assert CATALOG and SCHEMA, "catalog and schema parameters are required"

w = WorkspaceClient()
FQ = f"{CATALOG}.{SCHEMA}"

# COMMAND ----------
# Schema + raw landing Volume
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ} COMMENT 'Experian Auto Intelligence Cloud: governed automotive data products.'")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {FQ}.raw COMMENT "
          "'Raw landing zone: Experian flat-file drops picked up by the Lakeflow pipeline via Auto Loader.'")

# COMMAND ----------
# Entitlements table + row-filter / column-mask functions from the SQL template.
nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
repo_root = "/Workspace" + nb_path.split("/scaffold/")[0]
template = open(f"{repo_root}/scaffold/06_sharing/entitlements.sql").read()
sql = "\n".join(l for l in template.splitlines() if not l.strip().startswith("--"))
for stmt in [s.strip() for s in sql.format(catalog=CATALOG, schema=SCHEMA).split(";") if s.strip()]:
    spark.sql(stmt)
print(f"Applied entitlements template to {FQ}")

# COMMAND ----------
# Contract rows
deployer = spark.sql("SELECT current_user()").first()[0]
app_sp = None
try:
    app_sp = w.apps.get(APP_NAME).service_principal_client_id
except Exception as e:  # app not deployed yet: it can be added on a later run
    print(f"NOTE: app {APP_NAME!r} not found ({e}); its SP is not entitled yet")

rows = [(p, "Experian (internal)", "full", "*") for p in [deployer, app_sp, *FULL_ACCESS] if p]
for t in TENANTS:
    for st in t["states"]:
        rows.append((t["principal"], t["customer"], t.get("tier", "standard"), st))

spark.createDataFrame(rows, "principal STRING, customer STRING, tier STRING, state STRING") \
     .dropDuplicates(["principal", "state"]).createOrReplaceTempView("_new_entitlements")
spark.sql(f"""
MERGE INTO {FQ}.entitlements t
USING _new_entitlements s
ON t.principal = s.principal AND t.state = s.state
WHEN MATCHED THEN UPDATE SET customer = s.customer, tier = s.tier
WHEN NOT MATCHED THEN INSERT *
""")
display(spark.sql(f"SELECT customer, tier, principal, array_sort(collect_list(state)) AS states "
                  f"FROM {FQ}.entitlements GROUP BY ALL ORDER BY customer"))
