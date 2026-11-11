# Execution evidence

> Captured from the original reference deployment. Workspace URL, catalog (`experian_agent_demo_catalog.auto`), ids and principals are the values from that deployment. A fresh `scripts/deploy.sh` deployment uses your own catalog/schema (default schema `experian_auto`).

Text-only proof that the Experian Auto Intelligence Cloud build **actually runs** on
Databricks (workspace `fevm-experian-agent-demo`, catalog `experian_agent_demo_catalog.auto`).
Every file here is real output captured from the live workspace — query results, model
predictions, Genie-generated SQL, and authenticated HTTP responses from the deployed app.
Captured 2026-09-25; stages 1, 2, 3, 5 (VIN lookup) and 7 re-captured 2026-11-11.

| File | Stage | What it proves |
|---|---|---|
| [01_lakeflow_ingest.md](01_lakeflow_ingest.md) | **Lakeflow** ingest → UC | Raw CSV drops in a UC Volume → Auto Loader (incremental: 2nd batch ingested alone) → bronze → gold (4,320 / 20,000 / 30,000 rows), all expectations passing, row-for-row parity with the previous gold |
| [02_fusion_pipeline.md](02_fusion_pipeline.md) | **Lakeflow** Visual Prep | Same pipeline builds `analytics_market_360`, `feat_vehicle_fusion` and `vin_serving` |
| [03_lakebase_serving.md](03_lakebase_serving.md) | **Lakebase** OLTP | Synced table ONLINE (Delta `vin_serving` → Postgres, refreshed by the job); 20,000 VINs; **0.088 ms** indexed point lookup |
| [04_models_predictions.md](04_models_predictions.md) | **ML** serving | Live predictions from all three READY Model Serving endpoints |
| [04b_mlflow_runs.md](04b_mlflow_runs.md) | **ML** training | Logged metrics — default-risk AUC 0.90, days-to-turn MAE 4.03, residual MAE $932 |
| [05_app_responses.md](05_app_responses.md) | **Databricks App** | Authenticated live responses; VIN lookup `served_by: lakebase` with real predictions |
| [06_genie.md](06_genie.md) | **Genie** | Three NL questions → Genie-generated SQL + returned rows |
| [07_unity_catalog_governance.md](07_unity_catalog_governance.md) | **Unity Catalog** | Same SQL as 3 identities → 25 / 3 / 2 states; `orig_amount` masked for the standard tier; tenants denied on `vin_serving`; end-to-end lineage from `system.access.table_lineage`; models, docs |

## How the end-to-end journey connects

```
raw CSV drops (UC Volume) ─ Auto Loader ─→ bronze_* ─→ gold_* (expectations · row filter · mask)
                                                            │ Lakeflow / Visual Prep fusion
                       ┌────────────────────────────────────┼───────────────────────────────┐
                       ▼                                    ▼                               ▼
            analytics_market_360 ─→ Genie + AI/BI   feat_vehicle_fusion ─→ Mosaic AI   vin_serving
                                                            models ─→ Model Serving        │ synced table
                                                                                           ▼
                                                     Lakebase Postgres (auto.vin_serving_online) ─→ App /api/vin (sub-ms)
                                                                                    │
                                        Inventory & Risk Co-Pilot app ─────────────┘ (+ models + Genie)
```

To regenerate this evidence, re-run the capture queries against the workspace (the app URL
and warehouse id are noted in each file's header).
