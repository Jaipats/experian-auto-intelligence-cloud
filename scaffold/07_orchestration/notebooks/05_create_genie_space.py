# Databricks notebook source
# MAGIC %md
# MAGIC # 05 - Create / update the Genie space
# MAGIC Idempotently creates (or updates) the "Experian Auto Intelligence — Genie" space over
# MAGIC the fused analytics table plus the two drilldown tables, with curated instructions and
# MAGIC certified example SQL. Runs after the fusion pipeline so analytics_market_360 exists.
# COMMAND ----------
import json
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("schema", "experian_auto")
dbutils.widgets.text("warehouse_id", "")
dbutils.widgets.text("genie_space_title", "Experian Auto Intelligence — Genie")
dbutils.widgets.text("app_name", "experian-copilot")
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA = dbutils.widgets.get("schema").strip()
WAREHOUSE_ID = dbutils.widgets.get("warehouse_id").strip()   # warehouse the space runs SQL on
SPACE_TITLE = dbutils.widgets.get("genie_space_title").strip()
APP_NAME = dbutils.widgets.get("app_name").strip()
assert CATALOG and SCHEMA and WAREHOUSE_ID, "catalog, schema and warehouse_id parameters are required"

w = WorkspaceClient()

INSTRUCTIONS = """You are the Experian Auto Intelligence analyst. You answer questions about the U.S.
automotive market using Experian Automotive data: Vehicles-in-Operation (VIO) and market
statistics, AutoCheck vehicle history, and auto lending. Audience: franchise dealers, auto
lenders, and OEM analysts.

Domain glossary: VIO = registered vehicles on the road; market_share_pct = registration share
within state+month (higher = more popular); avg_days_to_turn = days a used unit takes to sell
(lower = stronger demand); avg_accs_score = AutoCheck condition score 1-100 (higher = cleaner);
clean_title_rate = fraction with Clean title; credit_tier = Super Prime/Prime/Near Prime/Subprime;
delinquency_rate/default_rate = fraction 30d+ delinquent / in default; LTV = loan-to-value %.

Rules: prefer analytics_market_360 for market/segment questions; gold_autocheck_vin for per-VIN
history; gold_lending for loan-level. 'Fastest-turning' => order by avg_days_to_turn asc.
State the snapshot_month used (default latest). If asked for data not in these tables (e.g. PII),
say it is not exposed here."""

TABLES = [
    f"{CATALOG}.{SCHEMA}.analytics_market_360",
    f"{CATALOG}.{SCHEMA}.gold_autocheck_vin",
    f"{CATALOG}.{SCHEMA}.gold_lending",
]

# (title, single-line SQL) — stored one-line so the API doesn't concatenate lines.
EXAMPLES = [
    ("Fastest-turning used SUVs in a state (latest month)",
     f"SELECT make, model, model_year, avg_days_to_turn, market_share_pct FROM {CATALOG}.{SCHEMA}.analytics_market_360 WHERE body_style = 'SUV' AND state = 'CA' AND snapshot_month = (SELECT MAX(snapshot_month) FROM {CATALOG}.{SCHEMA}.analytics_market_360) ORDER BY avg_days_to_turn ASC LIMIT 10"),
    ("Highest default rate segments relative to APR",
     f"SELECT make, model, model_year, avg_apr, avg_ltv_pct, delinquency_rate, default_rate FROM {CATALOG}.{SCHEMA}.analytics_market_360 WHERE loan_count >= 20 ORDER BY default_rate DESC LIMIT 15"),
    ("Lending share by lender type in a region",
     f"SELECT lender_type, COUNT(*) AS loans, ROUND(AVG(apr),2) AS avg_apr, ROUND(AVG(delinquency_30d_flag),3) AS delinquency_rate FROM {CATALOG}.{SCHEMA}.gold_lending WHERE region = 'Midwest' GROUP BY lender_type ORDER BY loans DESC"),
    ("Condition-adjusted acquisition candidates",
     f"SELECT make, model, model_year, body_style, avg_days_to_turn, market_share_pct, avg_accs_score, clean_title_rate FROM {CATALOG}.{SCHEMA}.analytics_market_360 WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM {CATALOG}.{SCHEMA}.analytics_market_360) AND avg_accs_score >= 80 ORDER BY avg_days_to_turn ASC, market_share_pct DESC LIMIT 20"),
    ("EV market share trend by state",
     f"SELECT snapshot_month, state, ROUND(SUM(CASE WHEN fuel_type='EV' THEN vio_count ELSE 0 END)*100.0/NULLIF(SUM(vio_count),0),2) AS ev_share_pct FROM {CATALOG}.{SCHEMA}.analytics_market_360 GROUP BY snapshot_month, state ORDER BY state, snapshot_month"),
    ("Data product: join coverage across all three datasets",
     f"SELECT COUNT(*) AS segments, COUNT(avg_accs_score) AS with_autocheck_condition, COUNT(avg_apr) AS with_lending FROM {CATALOG}.{SCHEMA}.analytics_market_360"),
    ("Data product: condition vs default-rate correlation by make and body style",
     f"SELECT make, body_style, ROUND(AVG(avg_accs_score),1) AS avg_condition, ROUND(AVG(default_rate),4) AS avg_default_rate, COUNT(*) AS segments FROM {CATALOG}.{SCHEMA}.analytics_market_360 WHERE avg_accs_score IS NOT NULL AND default_rate IS NOT NULL GROUP BY make, body_style ORDER BY avg_condition DESC LIMIT 20"),
    ("Data product: underserved segments (high demand, few lenders)",
     f"SELECT make, model, model_year, avg_days_to_turn, market_share_pct, lender_count FROM {CATALOG}.{SCHEMA}.analytics_market_360 WHERE lender_count IS NOT NULL AND avg_days_to_turn < (SELECT AVG(avg_days_to_turn) FROM {CATALOG}.{SCHEMA}.analytics_market_360) ORDER BY lender_count ASC, market_share_pct DESC LIMIT 20"),
    ("Data product: composite investability index across all three datasets",
     f"WITH b AS (SELECT MIN(avg_days_to_turn) mn_d, MAX(avg_days_to_turn) mx_d, MIN(avg_accs_score) mn_a, MAX(avg_accs_score) mx_a, MIN(default_rate) mn_r, MAX(default_rate) mx_r FROM {CATALOG}.{SCHEMA}.analytics_market_360 WHERE avg_accs_score IS NOT NULL AND default_rate IS NOT NULL) SELECT make, model, model_year, ROUND(0.35*(1-(avg_days_to_turn-mn_d)/nullif(mx_d-mn_d,0)) + 0.25*((avg_accs_score-mn_a)/nullif(mx_a-mn_a,0)) + 0.20*clean_title_rate + 0.20*(1-(default_rate-mn_r)/nullif(mx_r-mn_r,0)),3) AS investability_index FROM {CATALOG}.{SCHEMA}.analytics_market_360, b WHERE avg_accs_score IS NOT NULL AND default_rate IS NOT NULL AND snapshot_month = (SELECT MAX(snapshot_month) FROM {CATALOG}.{SCHEMA}.analytics_market_360) ORDER BY investability_index DESC LIMIT 20"),
]

# COMMAND ----------
# Build the serialized_space payload. IDs must be unique and each id-keyed list sorted by id.
import uuid

def _uid():
    return uuid.uuid4().hex

examples = sorted(
    [{"id": _uid(), "question": [t], "sql": [sql]} for t, sql in EXAMPLES],
    key=lambda x: x["id"],
)

serialized = {
    "version": 2,
    "data_sources": {"tables": sorted([{"identifier": t} for t in TABLES],
                                       key=lambda x: x["identifier"])},
    "instructions": {
        "text_instructions": [{"id": _uid(), "content": [INSTRUCTIONS]}],
        "example_question_sqls": examples,
    },
}

payload = {
    "title": SPACE_TITLE,
    "description": "Natural-language analyst over Experian Automotive VIO/market, AutoCheck "
                   "vehicle history, and auto lending data.",
    "warehouse_id": WAREHOUSE_ID,
    "serialized_space": json.dumps(serialized),
}

# COMMAND ----------
# Idempotent: patch the space if one with this title already exists, else create.
existing_id = None
for s in w.api_client.do("GET", "/api/2.0/genie/spaces").get("spaces", []):
    if s.get("title") == SPACE_TITLE:
        existing_id = s.get("space_id") or s.get("id")
        break

if existing_id:
    print(f"Updating existing Genie space {existing_id}")
    w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{existing_id}", body=payload)
    space_id = existing_id
else:
    print("Creating new Genie space")
    resp = w.api_client.do("POST", "/api/2.0/genie/spaces", body=payload)
    space_id = resp.get("space_id") or resp.get("id")

print("Genie space ready:", space_id)
dbutils.jobs.taskValues.set(key="genie_space_id", value=space_id)

# COMMAND ----------
# Let the Co-Pilot app's service principal run the space (the app resolves it by title).
try:
    app_sp = w.apps.get(APP_NAME).service_principal_client_id
    w.api_client.do("PATCH", f"/api/2.0/permissions/genie/{space_id}", body={
        "access_control_list": [{"service_principal_name": app_sp, "permission_level": "CAN_RUN"}]})
    print(f"Granted CAN_RUN on the Genie space to app SP {app_sp}")
except Exception as e:
    print(f"NOTE: could not grant the app SP Genie access ({e})")
