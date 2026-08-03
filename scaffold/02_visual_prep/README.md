# 02 — Databricks Visual Prep (Lakeflow Designer)

**Databricks Visual Prep** (the no-code/low-code authoring surface of Lakeflow Designer)
is where Experian domain analysts productize data without hand-writing Spark. Every visual
pipeline compiles down to a **Lakeflow Declarative Pipeline** — so this folder ships the
declarative SQL that a Visual Prep canvas generates, plus notes on how to rebuild it
visually.

## What we build here

Four flows, matching the plan:

| Flow | Output table | Purpose |
|---|---|---|
| A | `gold_vio_market` *(from 01)* | VIO / market statistics — already gold from the generator |
| B | `gold_autocheck_vin` *(from 01)* | AutoCheck condition features — already gold |
| C | `gold_lending` *(from 01)* | Lending risk features — already gold |
| **D** | **`feat_vehicle_fusion`** & **`analytics_market_360`** | **Fuse A+B+C** into a model-ready feature table and a Genie-ready analytics table |

Flows A–C are produced directly by the `01_data` generator (already clean, standardized,
and aggregated). Flow **D** is the fusion step that Visual Prep is ideal for: joining three
governed products on shared keys, then shaping two consumption-specific outputs.

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

- `fusion_pipeline.sql` — the declarative pipeline Visual Prep emits (drop into a Lakeflow
  pipeline, target = `experian_agent_demo_catalog.auto`).
- `deploy_pipeline.sh` — creates/starts the Lakeflow pipeline via the Databricks CLI.
