# 02 — Databricks Visual Prep (Lakeflow Designer)

**Databricks Visual Prep** (the no-code/low-code authoring surface of Lakeflow Designer)
is where Experian domain analysts productize data without hand-writing Spark. Every visual
pipeline compiles down to a **Lakeflow Declarative Pipeline** — so this folder ships the
declarative SQL that a Visual Prep canvas generates, plus notes on how to rebuild it
visually.

## What we build here

One Lakeflow pipeline (`experian_auto_fusion`) owns the whole path from raw files to
consumption tables:

```
/Volumes/<catalog>/<schema>/raw/<feed>/batch_<ts>/*.csv   (landed by 01_data)
   │ Auto Loader: STREAM read_files (incremental, exactly-once per file)
   ▼
bronze_vio_market · bronze_autocheck_vin · bronze_lending      streaming tables, raw STRINGs,
   │                                                            + _source_file/_ingested_at
   │ typed casts · de-dup (latest file wins per key) · EXPECT constraints
   ▼
gold_vio_market · gold_autocheck_vin · gold_lending            materialized views, documented
   │                                                            columns, UC row filter / mask
   │ Flow D: fusion (Visual Prep)
   ▼
analytics_market_360 (Genie) · feat_vehicle_fusion (ML) · vin_serving (→ Lakebase synced table)
```

| Flow | Output table | Purpose |
|---|---|---|
| A | `bronze_vio_market` → `gold_vio_market` | VIO / market statistics |
| B | `bronze_autocheck_vin` → `gold_autocheck_vin` | AutoCheck vehicle history |
| C | `bronze_lending` → `gold_lending` | Lending risk |
| **D** | **`feat_vehicle_fusion`**, **`analytics_market_360`**, **`vin_serving`** | **Fuse A+B+C** into model-ready, Genie-ready and operational-serving outputs |

**Data quality**: each gold table declares `CONSTRAINT … EXPECT` rules. Malformed keys,
out-of-range APR/LTV/share/ACCS score and invalid VINs are dropped, and soft checks are
logged as warnings. Pass/fail counts land in the pipeline event log (see
`../../evidence/01_lakeflow_ingest.md`).

**Governance in the DDL**: gold, `analytics_market_360` and `feat_vehicle_fusion` attach the
`rf_state` row filter, and `gold_lending.orig_amount` attaches the `mask_orig_amount` mask.
Both are declared in the pipeline, so every refresh re-applies them. **Prereq:** the job's
`setup` task applies `../06_sharing/entitlements.sql` before the pipeline runs, so the functions exist.

- `feat_vehicle_fusion` — **model-ready**: one row per VIN enriched with the local VIO
  demand signal and the lending risk profile for that vehicle's make/model/geo. Feeds
  `04_models`.
- `analytics_market_360` — **Genie-ready**: a wide, human-readable market table joining
  VIO share + AutoCheck condition rollups + lending share by make/model/geo/month. Feeds
  `03_genie` and AI/BI dashboards.

## Rebuild in the Visual Prep canvas (no-code)

1. **New pipeline → Lakeflow Designer → blank canvas.**
2. Add three **Source** nodes: `gold_vio_market`, `gold_autocheck_vin`, `gold_lending`.
3. On the AutoCheck source, add a **Group by** node (key: make/model/model_year/garaged_state)
   producing condition rollups (avg ACCS, accident rate, clean-title rate).
4. On the Lending source, add a **Group by** node (key: make/model/model_year/state)
   producing lending rollups (avg APR, delinquency rate, lender count, avg LTV).
5. Add **Join** nodes to combine VIO ⟕ condition rollups ⟕ lending rollups on the shared
   make/model/model_year + state keys.
6. Add a **Select / Rename** node to finalize columns → materialize as
   `analytics_market_360`.
7. For the feature table, branch from the AutoCheck source, **Join** each VIN to its
   make/model/geo VIO demand and lending risk rollups → materialize `feat_vehicle_fusion`.
8. **Publish** — Visual Prep generates the declarative pipeline (equivalent to
   `fusion_pipeline.sql`) and schedules it in Unity Catalog.

## Files

- `fusion_pipeline.sql`: the complete declarative pipeline: Auto Loader bronze, governed
  gold, and the fusion flow Visual Prep emits. Catalog and schema are the pipeline
  configuration values `${experian.catalog}` / `${experian.schema}`, set by the bundle in
  `../../resources/experian_auto.pipeline.yml`. That's why the same SQL deploys anywhere.
