# Experian Auto Intelligence Cloud — Scaffold

End-to-end scaffold for the **Experian Auto Intelligence Cloud** POC on Databricks.
This turns three Experian Automotive datasets into governed, AI-ready data products, then
exposes them through Visual Prep pipelines, a Genie natural-language interface, Mosaic AI
models, and an "Inventory & Risk Co-Pilot" Databricks App — all shareable to customers
via Delta Sharing.

```
Workspace : https://fevm-experian-agent-demo.cloud.databricks.com/
Catalog   : experian_agent_demo_catalog
Schema    : auto
```

## The three datasets (bronze → gold)

| Table | Grain | Description |
|---|---|---|
| `gold_vio_market`    | make/model/trim × geo × month | Vehicles-in-Operation & market statistics |
| `gold_autocheck_vin` | one row per VIN               | Vehicle history: title, accidents, owners, ACCS score |
| `gold_lending`       | one row per loan              | Auto loan/lease originations, risk, delinquency |

## Layout

```
scaffold/
├── 01_data/            Synthetic data generator (Polars + Mimesis → UC)
├── 02_visual_prep/     Lakeflow Designer / Visual Prep gold pipelines (SQL + notes)
├── 03_genie/           Genie Space config: instructions, sample Qs, certified SQL
├── 04_models/          Mosaic AI models: residual, demand, risk (training notebooks)
├── 05_app/             "Inventory & Risk Co-Pilot" Databricks App (FastAPI + React)
└── 06_sharing/         Delta Sharing + Unity Catalog entitlements (row/column governance)
```

## Run order

1. **`01_data`** — generate the raw/gold tables (needs catalog `CREATE SCHEMA` — see note below).
2. **`02_visual_prep`** — build the fused feature/analytics tables from the three golds.
3. **`03_genie`** — create the Genie Space over the fused analytics table.
4. **`04_models`** — train & register residual / demand / risk models; deploy to Model Serving.
5. **`05_app`** — deploy the Co-Pilot Databricks App (calls models + embeds Genie).
6. **`06_sharing`** — publish gold products via Delta Sharing with per-customer entitlements.

## ⚠️ Prerequisite: catalog permission

The generator writes to `experian_agent_demo_catalog.auto`. Creating that schema requires
`CREATE SCHEMA` on the catalog. The catalog owner (`jaideep.patel@databricks.com`) must
either run `01_data` under their own profile, or grant a service principal:

```sql
GRANT CREATE SCHEMA ON CATALOG experian_agent_demo_catalog TO `<principal>`;
```

See `01_data/README.md` for the exact commands.
