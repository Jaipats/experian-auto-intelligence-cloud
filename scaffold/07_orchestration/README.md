# 07 — End-to-End Orchestration (Job + Lakeflow pipeline)

One Databricks **Job**, defined in `../../resources/experian_auto.job.yml`, runs the whole flow.
Every task is idempotent, so re-running the job refreshes the demo: new raw files are ingested
incrementally, models are retrained, and endpoints, Genie and Lakebase are updated in place.

## The job DAG

```
setup ──▶ generate_data ──▶ build_fusion ──┬──▶ sync_lakebase
                                            ├──▶ train_models ──▶ deploy_serving
                                            └──▶ create_genie_space
```

| Task | Type | Notebook / resource | Does |
|---|---|---|---|
| `setup` | notebook | `notebooks/00_setup.py` | Creates the schema and the `raw` Volume; applies `../06_sharing/entitlements.sql` (contract table, `rf_state` row filter, `mask_orig_amount` column mask); loads contracts for the deployer, the app SP, `full_access_principals` and `tenant_contracts` |
| `generate_data` | notebook | `notebooks/01_generate_data.py` | Lands the three synthetic feeds as CSV batches in `/Volumes/<catalog>/<schema>/raw/<feed>/batch_<ts>/` |
| `build_fusion` | **pipeline** | `resources/experian_auto.pipeline.yml` → `../02_visual_prep/fusion_pipeline.sql` | Auto Loader → `bronze_*` → governed `gold_*` → `analytics_market_360`, `feat_vehicle_fusion`, `vin_serving` |
| `sync_lakebase` | notebook | `notebooks/06_sync_lakebase.py` | UC grants for the app SP and tenants; creates/refreshes the Lakebase synced table; Postgres `SELECT` for the app SP |
| `train_models` | notebook | `notebooks/03_train_models.py` | Trains and registers the residual / days-to-turn / default-risk models in UC |
| `deploy_serving` | notebook | `notebooks/04_deploy_serving.py` | Creates or updates `<prefix>-residual-value`, `-days-to-turn`, `-default-risk` at the latest versions; grants the app `CAN_QUERY` |
| `create_genie_space` | notebook | `notebooks/05_create_genie_space.py` | Creates or updates the Genie space (instructions + 9 certified SQLs); grants the app `CAN_RUN` |

Job parameters (`catalog`, `schema`, `warehouse_id`, `app_name`, `endpoint_prefix`, …) come
from the bundle variables and are passed to every notebook as widgets. All tasks run on
serverless compute.

## Run

```bash
scripts/deploy.sh                                 # deploy + start app + run the job (first time)
databricks bundle run experian_auto_e2e           # re-run the job later
databricks bundle run experian_auto_e2e --only generate_data,build_fusion,sync_lakebase   # just refresh data
```

## Notes

- **Order matters on the first run.** `setup` must create the row-filter/mask functions before
  the pipeline runs, because the gold DDL attaches them. The DAG enforces this.
- **Run-as identity.** The job and pipeline run as the deploying user, who needs
  `CREATE SCHEMA` on the catalog, model-registry write, serving-endpoint create, Genie space
  create, and Lakebase project ownership (or `databricks_superuser`).
- **Serving deploys always target the latest registered version**, so re-runs pick up newly
  trained models automatically.
