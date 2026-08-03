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

```bash
cd app/backend
uv run --with fastapi --with uvicorn --with databricks-sql-connector \
  --with databricks-sdk --with requests \
  uvicorn main:app --reload --port 8000
# open http://localhost:8000
```

Set env (see `app.yaml` for the deployed equivalents):

```bash
export DATABRICKS_HOST=https://fevm-experian-agent-demo.cloud.databricks.com
export DATABRICKS_WAREHOUSE_ID=<serverless-sql-warehouse-id>
export GENIE_SPACE_ID=<genie-space-id>
export CATALOG=experian_agent_demo_catalog
export SCHEMA=auto
# auth: `databricks auth login` profile, or DATABRICKS_TOKEN
```

## Deploy as a Databricks App

```bash
databricks apps create experian-copilot --profile fe-vm-experian-agent-demo
databricks sync ./app /Workspace/Users/<you>/experian-copilot --profile fe-vm-experian-agent-demo
databricks apps deploy experian-copilot \
  --source-code-path /Workspace/Users/<you>/experian-copilot \
  --profile fe-vm-experian-agent-demo
```

The app's service principal needs `SELECT` on the `auto` schema tables, `CAN QUERY` on the
serving endpoints, and `CAN RUN` on the Genie Space. `app.yaml` declares the resource
bindings and env.

> This is a scaffold: the SQL and serving/Genie calls are wired and will run once the
> tables (01), pipeline (02), Genie space (03), and endpoints (04) exist. Until then the
> backend falls back to illustrative sample rows so the UI is demoable standalone.
