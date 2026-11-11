# Databricks notebook source
# MAGIC %pip install "psycopg[binary]>=3.1"
# COMMAND ----------
# MAGIC %md
# MAGIC # 06 - Lakebase sync + access grants
# MAGIC Runs after the Lakeflow pipeline. Idempotent.
# MAGIC
# MAGIC 1. **Unity Catalog grants**: the Co-Pilot app's service principal gets `SELECT` on the
# MAGIC    tables it reads. Each demo tenant in the `entitlements` table gets `SELECT` on the
# MAGIC    governed customer products (the row filter / column mask scope what they see).
# MAGIC 2. **Lakebase synced table**: `<catalog>.<schema>.vin_serving_online` syncs the Lakeflow view
# MAGIC    `vin_serving` into Postgres `<schema>.vin_serving_online` (SNAPSHOT mode; CDF reads
# MAGIC    from materialized views are still Beta). It's created on the first run and
# MAGIC    refreshed on every later run.
# MAGIC 3. **Postgres grants**: the app's service principal gets `SELECT` on the synced table.
# COMMAND ----------
import time

from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("schema", "experian_auto")
dbutils.widgets.text("app_name", "experian-copilot")
dbutils.widgets.text("lakebase_project", "experian-auto-oltp")
dbutils.widgets.text("lakebase_branch", "production")
dbutils.widgets.text("lakebase_pg_database", "databricks_postgres")

CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
APP_NAME = dbutils.widgets.get("app_name").strip()
PROJECT = dbutils.widgets.get("lakebase_project").strip()
BRANCH = f"projects/{PROJECT}/branches/{dbutils.widgets.get('lakebase_branch').strip()}"
PG_DB = dbutils.widgets.get("lakebase_pg_database").strip()
assert CATALOG and SCHEMA, "catalog and schema parameters are required"

FQ = f"{CATALOG}.{SCHEMA}"
SOURCE = f"{FQ}.vin_serving"
SYNCED = f"{FQ}.vin_serving_online"
w = WorkspaceClient()
app_sp = w.apps.get(APP_NAME).service_principal_client_id
print("app service principal:", app_sp)

# COMMAND ----------
# 1. Unity Catalog grants
APP_TABLES = ["gold_vio_market", "gold_autocheck_vin", "gold_lending",
              "analytics_market_360", "feat_vehicle_fusion"]
TENANT_TABLES = ["gold_vio_market", "gold_lending", "analytics_market_360"]

def grant(principal, tables):
    spark.sql(f"GRANT USE CATALOG ON CATALOG {CATALOG} TO `{principal}`")
    spark.sql(f"GRANT USE SCHEMA ON SCHEMA {FQ} TO `{principal}`")
    for t in tables:
        spark.sql(f"GRANT SELECT ON TABLE {FQ}.{t} TO `{principal}`")

grant(app_sp, APP_TABLES)
tenants = [r.principal for r in spark.sql(
    f"SELECT DISTINCT principal FROM {FQ}.entitlements WHERE state <> '*'").collect()]
for p in tenants:
    grant(p, TENANT_TABLES)
print(f"UC grants: app SP on {len(APP_TABLES)} tables; {len(tenants)} tenant(s) on {TENANT_TABLES}")

# COMMAND ----------
# 2. Lakebase synced table: create on first run, refresh afterwards
def get_synced():
    try:
        return w.api_client.do("GET", f"/api/2.0/postgres/synced_tables/{SYNCED}")
    except Exception as e:
        if "does not exist" in str(e) or "NOT_FOUND" in str(e) or "404" in str(e):
            return None
        raise

st = get_synced()
if st is None:
    print(f"Creating synced table {SYNCED} <- {SOURCE}")
    w.api_client.do("POST", "/api/2.0/postgres/synced_tables",
                    query={"synced_table_id": SYNCED},
                    body={"spec": {
                        "source_table_full_name": SOURCE,
                        "primary_key_columns": ["vin"],
                        "scheduling_policy": "SNAPSHOT",
                        "branch": BRANCH,
                        "postgres_database": PG_DB,
                        "create_database_objects_if_missing": True,
                        "new_pipeline_spec": {"storage_catalog": CATALOG, "storage_schema": SCHEMA},
                    }})
    triggered = False
else:
    pid = st["status"]["pipeline_id"]
    print(f"Refreshing synced table {SYNCED} (pipeline {pid})")
    w.pipelines.start_update(pipeline_id=pid)
    triggered = True

# Wait for the initial snapshot / refresh to land.
deadline = time.time() + 30 * 60
time.sleep(30 if triggered else 10)
while True:
    st = get_synced() or {}
    state = st.get("status", {}).get("detailed_state", "UNKNOWN")
    print("  state:", state)
    if state.startswith("SYNCED_TABLE_ONLINE") and "FAILED" not in state:
        pid = st["status"]["pipeline_id"]
        latest = list(w.pipelines.list_updates(pipeline_id=pid, max_results=1).updates or [])
        if not latest or latest[0].state.value in ("COMPLETED",):
            break
    if "FAILED" in state:
        raise RuntimeError(f"Synced table failed: {st.get('status', {}).get('message')}")
    if time.time() > deadline:
        raise TimeoutError(f"Synced table not online after 30 min (state {state})")
    time.sleep(20)
print("Synced table online:", SYNCED)

# COMMAND ----------
# 3. Postgres grants for the app SP (the sync owns the table; the job identity owns the project)
import psycopg

ep = w.api_client.do("GET", f"/api/2.0/postgres/{BRANCH}/endpoints/primary")
host = ep["status"]["hosts"]["host"]
token = w.api_client.do("POST", "/api/2.0/postgres/credentials",
                        body={"endpoint": f"{BRANCH}/endpoints/primary"})["token"]
me = spark.sql("SELECT current_user()").first()[0]
with psycopg.connect(host=host, dbname=PG_DB, user=me, password=token,
                     sslmode="require", autocommit=True) as conn:
    conn.execute(f'GRANT USAGE ON SCHEMA "{SCHEMA}" TO "{app_sp}"')
    conn.execute(f'GRANT SELECT ON "{SCHEMA}".vin_serving_online TO "{app_sp}"')
    n = conn.execute(f'SELECT count(*) FROM "{SCHEMA}".vin_serving_online').fetchone()[0]
print(f"Postgres {PG_DB}.{SCHEMA}.vin_serving_online: {n:,} rows; SELECT granted to {app_sp}")
