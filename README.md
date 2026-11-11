# Experian Auto Intelligence Cloud

An end-to-end Databricks demo. It turns three Experian Automotive-style datasets
(**Vehicles-in-Operation / market statistics**, **AutoCheck vehicle history** and
**automotive credit & lending**) into governed, AI-ready data products, then exposes them
through Genie (plain-English questions), Model Serving and an **"Inventory & Risk Co-Pilot"**
Databricks App. The whole thing deploys with one command as a Declarative Automation Bundle.

> All data is **synthetic**, generated for illustration only.

## What it demonstrates

| Stage | Databricks product | What happens | Evidence |
|---|---|---|---|
| Ingest | **Lakeflow** | Raw CSV drops in a UC Volume → Auto Loader → `bronze_*` → typed, de-duplicated `gold_*` with data-quality expectations | [`evidence/01`](evidence/01_lakeflow_ingest.md), [`02`](evidence/02_fusion_pipeline.md) |
| Govern | **Unity Catalog** | Per-customer row filter + column mask driven by an entitlements table; column docs; automatic lineage | [`evidence/07`](evidence/07_unity_catalog_governance.md) |
| Serve (OLTP) | **Lakebase** | Synced table pushes the per-VIN record to Postgres; sub-millisecond primary-key lookups | [`evidence/03`](evidence/03_lakebase_serving.md) |
| Intelligence | **MLflow + Model Serving** | Residual value, days-to-turn and default-risk models, registered in UC and served | [`evidence/04`](evidence/04_models_predictions.md), [`04b`](evidence/04b_mlflow_runs.md) |
| NL analytics | **Genie** | Genie space with curated instructions and certified SQL | [`evidence/06`](evidence/06_genie.md) |
| Business surface | **Databricks Apps** | Co-Pilot app: Acquire, Price & Risk (VIN lookup), Market Radar, Ask (Genie) | [`evidence/05`](evidence/05_app_responses.md) |

## Architecture

```
 raw CSV drops ──Auto Loader──▶ bronze_* ──▶ gold_*  (expectations · row filter · column mask)
 (UC Volume)                                  │
                         Lakeflow pipeline    │ Visual Prep fusion
              ┌───────────────────────────────┼──────────────────────────────┐
              ▼                               ▼                              ▼
   analytics_market_360            feat_vehicle_fusion                  vin_serving
        │                                     │                              │ Lakebase synced table
        ▼                                     ▼                              ▼
   Genie space                 MLflow models → Model Serving       Lakebase Postgres (PK vin)
        └──────────────┬──────────────────────┴──────────────────────────────┘
                       ▼
        Inventory & Risk Co-Pilot (Databricks App)
```

One Lakeflow pipeline owns everything from raw files to consumption tables, so Unity
Catalog lineage runs end to end. One job orchestrates it:

```
setup ──▶ generate_data ──▶ build_fusion ──┬──▶ sync_lakebase
                                            ├──▶ train_models ──▶ deploy_serving
                                            └──▶ create_genie_space
```

## Deploy

### Prerequisites

- A Databricks workspace with Unity Catalog, serverless compute, Databricks Apps, Genie and
  Lakebase (Autoscaling) enabled.
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html), authenticated:
  `databricks auth login --host https://<workspace-host> --profile <profile>`.
- An existing **catalog** where you have `CREATE SCHEMA`, and a **SQL warehouse** (serverless
  recommended) you can use.
- Permission to create apps, serving endpoints, Genie spaces and Lakebase projects.

### Quickstart

```bash
git clone <this-repo> && cd <this-repo>
cp .env.example .env          # set DATABRICKS_CONFIG_PROFILE, CATALOG, WAREHOUSE_ID
scripts/deploy.sh
```

`scripts/deploy.sh`:
1. creates the Lakebase project if it doesn't exist,
2. runs `databricks bundle deploy` (pipeline, job, app and its bindings),
3. starts the app (`databricks bundle run copilot`),
4. runs the end-to-end job (`databricks bundle run experian_auto_e2e`). The first run takes
   roughly 20–30 minutes.

It prints the app URL when done. Use `scripts/deploy.sh --deploy-only` to skip steps 3–4.

### What gets created

| Resource | Name (defaults) | Created by |
|---|---|---|
| Schema, `raw` Volume, `entitlements` table, `rf_state` / `mask_orig_amount` functions | `<catalog>.experian_auto` | job `setup` |
| Lakeflow pipeline + tables (`bronze_*`, `gold_*`, `analytics_market_360`, `feat_vehicle_fusion`, `vin_serving`) | `experian_auto_fusion_<schema>` | bundle |
| Job | `experian_auto_intelligence_e2e_<schema>` | bundle |
| Databricks App | `experian-copilot` | bundle |
| Lakebase project + synced table `<schema>.vin_serving_online` | `experian-auto-oltp` | `deploy.sh` + job `sync_lakebase` |
| UC models + serving endpoints | `<prefix>-residual-value`, `-days-to-turn`, `-default-risk` | job `train_models`, `deploy_serving` |
| Genie space | `Experian Auto Intelligence — Genie` | job `create_genie_space` |

The job also grants the app's service principal everything it reads: UC tables, endpoints,
the Genie space and the Lakebase table.

### Configuration

All workspace-specific values live in `.env` (gitignored) and map to bundle variables in
`databricks.yml`:

| `.env` key | Bundle variable | Default | Purpose |
|---|---|---|---|
| `DATABRICKS_CONFIG_PROFILE` | n/a | `DEFAULT` | CLI profile for the target workspace |
| `CATALOG` | `catalog` | **required** | Existing catalog to deploy into |
| `WAREHOUSE_ID` | `warehouse_id` | **required** | SQL warehouse for the app and Genie |
| `SCHEMA` | `schema` | `experian_auto` | Schema for every object |
| `APP_NAME` | `app_name` | `experian-copilot` | App name (≤ 30 chars) |
| `ENDPOINT_PREFIX` | `endpoint_prefix` | `experian` | Serving endpoint name prefix |
| `GENIE_SPACE_TITLE` | `genie_space_title` | `Experian Auto Intelligence — Genie` | The app finds the space by this title |
| `LAKEBASE_PROJECT` / `_BRANCH` / `_DATABASE_ID` / `_PG_DATABASE` | `lakebase_*` | `experian-auto-oltp` / `production` / `databricks-postgres` / `databricks_postgres` | Lakebase target (reuse an existing project by setting all four) |
| `FULL_ACCESS_PRINCIPALS` | `full_access_principals` | empty | Extra users/SPs who see all states at full tier |
| `TENANT_CONTRACTS` | `tenant_contracts` | `[]` | Demo customers for the governance story (see below) |

To deploy a second, independent copy in the same workspace, change `SCHEMA`, `APP_NAME`,
`ENDPOINT_PREFIX` and `GENIE_SPACE_TITLE`.

### Day 2

```bash
databricks bundle run experian_auto_e2e                    # refresh everything
databricks bundle run experian_auto_e2e --only generate_data,build_fusion,sync_lakebase
                                                           # land a new batch → incremental ingest → Lakebase
databricks bundle deploy && databricks bundle run copilot  # ship app/pipeline/job changes
```

### Governance demo: same query, different customers

Set `TENANT_CONTRACTS` to one or more service principals (or users) and re-run the job:

```bash
TENANT_CONTRACTS='[{"principal":"<sp-app-id-1>","customer":"Contoso Dealer Group","tier":"standard","states":["CA","NV","AZ"]},
                   {"principal":"<sp-app-id-2>","customer":"Northwind Auto Finance","tier":"full","states":["TX","FL"]}]'
```

Each tenant can query `gold_vio_market`, `gold_lending` and `analytics_market_360`, but only
sees its contracted states. Standard-tier tenants see `orig_amount` rounded to $1,000.
Neither can read the operational `vin_serving` table. See
[`evidence/07`](evidence/07_unity_catalog_governance.md) for captured output.

### Tear down

```bash
databricks bundle destroy                                   # app, job, pipeline (+ its tables)
for e in residual-value days-to-turn default-risk; do databricks serving-endpoints delete "experian-$e"; done
databricks postgres delete-synced-table "synced_tables/<catalog>.experian_auto.vin_serving_online"
databricks schemas delete <catalog>.experian_auto --force   # models, Volume, remaining tables
databricks postgres delete-project projects/experian-auto-oltp   # only if dedicated to this demo
# and delete the Genie space ("Experian Auto Intelligence — Genie") in the Genie UI
```

## Repository layout

```
databricks.yml              bundle: variables, sync rules, target
resources/                  pipeline, job and app definitions
scripts/deploy.sh           one-command deploy (reads .env)
.env.example                configuration template
scaffold/
  01_data/                  synthetic data generator (Polars + Mimesis → CSV in a UC Volume)
  02_visual_prep/           Lakeflow pipeline SQL: Auto Loader bronze → governed gold → fusion
  03_genie/                 Genie instructions + certified example SQL
  04_models/                model design notes (training/serving run as job notebooks)
  05_app/                   Co-Pilot app: FastAPI backend + JS frontend
  06_sharing/               entitlements template (row filter + mask); Delta Sharing script
  07_orchestration/         job notebooks 00_setup … 06_sync_lakebase
  08_lakebase/              Lakebase synced-table design notes
evidence/                   output captured from a reference deployment
Experian_Auto_Intelligence_Cloud_Deck.md / .pdf, _OnePager.md   business narrative
```

## Design notes

- **Lakebase sync uses SNAPSHOT mode.** Incremental (TRIGGERED/CONTINUOUS) sync needs a
  Change Data Feed from the source, and CDF reads from materialized views are still Beta. A
  snapshot of 20k rows takes about 11 s. See `scaffold/08_lakebase/README.md`.
- **Serving endpoints scale to zero.** The first app request after they've been idle can
  return a VIN without predictions while they warm up.
- **Delta Sharing is scripted but not deployed.** It needs `CREATE SHARE` on the metastore,
  and shared recipients need a `current_recipient()` branch in the filter and mask. See
  `scaffold/06_sharing/README.md`.
- **Workspace admins bypass the row filter** (`is_member('admins')`), so they always see all rows.
  Test the governance story as a non-admin tenant.

Built as a Databricks Field Engineering demonstration.
