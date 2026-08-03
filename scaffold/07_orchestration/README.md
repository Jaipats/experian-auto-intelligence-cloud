# 07 — End-to-End Orchestration (Job + Pipeline)

Runs the entire Experian Auto Intelligence flow as one repeatable Databricks **Job**
that chains a notebook, a **Lakeflow pipeline**, and two more notebooks. Everything below
is **already created and loaded in the workspace** (see IDs). The job has NOT been run.

```
Workspace: https://fevm-experian-agent-demo.cloud.databricks.com/
Owner:     jaideep.patel@databricks.com
```

## What was created

| Object | Name | ID |
|---|---|---|
| Job | `experian_auto_intelligence_e2e` | `729857403662711` |
| Lakeflow pipeline | `experian_auto_fusion` | `c6259e3f-7d6a-4661-a58a-cec0442310de` |
| Notebook | `01_generate_data` | in `/Workspace/Users/jaideep.patel@databricks.com/experian_auto/notebooks` |
| Notebook | `03_train_models` | (same dir) |
| Notebook | `04_deploy_serving` | (same dir) |
| Pipeline source | `fusion_pipeline.sql` | `.../experian_auto/pipeline/` |

## The job DAG

```
generate_data ──▶ build_fusion ──┬──▶ train_models ──▶ deploy_serving
 (notebook)        (pipeline)     │     (notebook)        (notebook)
                                  └──▶ create_genie_space
                                        (notebook)
```

After `build_fusion`, two independent branches run in parallel: the model chain
(`train_models → deploy_serving`) and `create_genie_space` (which only needs the fused
`analytics_market_360`, not the models).

| Task | Type | Does |
|---|---|---|
| `generate_data` | notebook | Builds the 3 gold tables in `experian_agent_demo_catalog.auto` (Polars/Mimesis on ambient spark) |
| `build_fusion` | **pipeline** | Runs `experian_auto_fusion` → `analytics_market_360`, `feat_vehicle_fusion`, rollups |
| `train_models` | notebook | Trains + registers residual / days-to-turn / default-risk models; logs to workspace experiment |
| `deploy_serving` | notebook | Creates/updates the 3 serving endpoints to the latest model versions (idempotent) |
| `create_genie_space` | notebook | Idempotently creates/updates the "Experian Auto Intelligence — Genie" space over the fused + drilldown tables, with curated instructions and 9 certified example SQLs. Takes a `warehouse_id` param; publishes the resulting `genie_space_id` as a task value. |

All notebook tasks run on a **serverless job environment** with `polars, mimesis,
scikit-learn, mlflow` declared as dependencies. The pipeline task is serverless too.

## Run it

- **UI:** Workflows → `experian_auto_intelligence_e2e` → Run now.
- **CLI:**
  ```bash
  databricks jobs run-now 729857403662711 --profile fe-vm-experian-agent-demo
  ```

## Re-create from source (if needed)

```bash
P=fe-vm-experian-agent-demo
WS=/Workspace/Users/jaideep.patel@databricks.com/experian_auto
databricks workspace mkdirs $WS/notebooks --profile $P
databricks workspace mkdirs $WS/pipeline  --profile $P
for f in 01_generate_data 03_train_models 04_deploy_serving; do
  databricks workspace import $WS/notebooks/$f --file notebooks/$f.py \
    --language PYTHON --format SOURCE --overwrite --profile $P
done
databricks workspace import $WS/pipeline/fusion_pipeline.sql \
  --file ../02_visual_prep/fusion_pipeline.sql --language SQL --format SOURCE --overwrite --profile $P
databricks pipelines create --json @pipeline.json --profile $P   # note the new pipeline_id
# update job.json's pipeline_id if it changed, then:
databricks jobs create --json @job.json --profile $P
```

## Notes / caveats

- **Notebooks 01 & 03 are the workspace-adapted versions** of the local scripts: the
  Databricks Connect session was swapped for ambient `spark`, and (for training) explicit
  MLflow tracking URIs were dropped since the job runtime is already Databricks-backed.
  UC registry is kept via `mlflow.set_registry_uri("databricks-uc")`.
- **`build_fusion` and the standalone MVs:** step 1 earlier created `analytics_market_360`
  etc. as standalone materialized views via ad-hoc SQL. When the pipeline first runs it will
  want to **own** those objects. If it errors that the tables already exist and aren't
  managed by the pipeline, drop them first
  (`DROP MATERIALIZED VIEW ... ` for the four fusion objects) and let the pipeline
  recreate them. Fresh workspaces won't hit this.
- **Serving deploy uses the SDK** (`04_deploy_serving`) and always targets the *latest*
  registered version, so re-runs pick up newly trained models automatically.
- The job's run-as identity needs: `CREATE SCHEMA`/write on the catalog, pipeline run
  rights, model-registry write, and serving-endpoint create/update.
