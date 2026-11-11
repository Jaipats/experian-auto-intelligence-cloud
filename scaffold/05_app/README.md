# 05 — "Inventory & Risk Co-Pilot" Databricks App

A Databricks App (FastAPI backend + lightweight HTML/JS frontend) with four modules:

| Module | Data / Model | What it shows |
|---|---|---|
| **Acquire** | `analytics_market_360` + `days_to_turn_model` | Ranked vehicles to acquire: demand, predicted days-to-turn, target price |
| **Price & Risk** | `gold_autocheck_vin` + residual & default models | Per-VIN condition, residual value, and segment default risk |
| **Market Radar** | `analytics_market_360` + `gold_lending` | Where lending share is shifting; underserved segments |
| **Ask (Genie)** | Genie Space (from `03_genie`) | Embedded natural-language analyst |

The backend queries Unity Catalog via the SQL warehouse (Databricks SQL connector),
calls the Model Serving endpoints from `04_models`, and proxies questions to the Genie
Conversations API.

## Local dev

The app is deployed by the bundle (`../../resources/copilot.app.yml`), which sets its env
(catalog/schema, warehouse, endpoint names, Genie space title, Lakebase table) and its
resource bindings (SQL warehouse + Lakebase Postgres). The job grants the app's service
principal `SELECT` on the tables, `CAN_QUERY` on the endpoints, `CAN_RUN` on the Genie space
and `SELECT` on the Lakebase synced table.

```bash
databricks bundle run copilot      # (re)deploy the app source and start it
```

## Layout

```
05_app/
├── requirements.txt
├── backend/          FastAPI: main.py (routes), db.py (SQL warehouse), lakebase.py (Postgres pool),
│                     models.py (Model Serving), genie.py (Genie Conversations API), data.py (samples)
└── frontend/         index.html + app.js (Experian-branded UI, Genie transparency panel)
```

## Local dev

```bash
cd scaffold/05_app
export DATABRICKS_CONFIG_PROFILE=<profile> DATABRICKS_HOST=https://<workspace-host>
export DATABRICKS_WAREHOUSE_ID=<warehouse-id> CATALOG=<catalog> SCHEMA=experian_auto
export GENIE_SPACE_TITLE="Experian Auto Intelligence — Genie"   # or GENIE_SPACE_ID=<id>
uv run --with fastapi --with "uvicorn[standard]" --with databricks-sql-connector \
  --with databricks-sdk --with requests --with "psycopg[binary,pool]" \
  uvicorn backend.main:app --reload --port 8000
# open http://localhost:8000. Lakebase is optional locally: without PGHOST the VIN lookup
# falls back to the SQL warehouse, and without any config the UI shows sample rows.
```

> The serving endpoints scale to zero. The first VIN lookup after they've been idle can
> come back without predictions while they warm up; retry after about a minute.
