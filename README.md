# Experian Auto Intelligence Cloud

An end-to-end Databricks demonstration that turns three Experian Automotive datasets —
**Vehicles-in-Operation / Velocity market statistics**, **AutoCheck vehicle history**, and
**automotive credit & lending** — into governed, AI-ready data products, then exposes them
through a natural-language Genie interface, Mosaic AI models, and an **"Inventory & Risk
Co-Pilot"** app, with Delta Sharing for customer distribution.

> All data is **synthetic**, generated for illustration only.

## What's here

| Path | Contents |
|---|---|
| `gen_experian_auto.py` | Standalone synthetic-data generator (Polars + Mimesis → Unity Catalog) |
| `scaffold/01_data/` | Data-generation notebook + README |
| `scaffold/02_visual_prep/` | Visual Prep / Lakeflow fusion pipeline (`analytics_market_360`, `feat_vehicle_fusion`) |
| `scaffold/03_genie/` | Genie space instructions + certified example SQL |
| `scaffold/04_models/` | Mosaic AI models: residual value, days-to-turn, default risk (train + serve) |
| `scaffold/05_app/` | "Inventory & Risk Co-Pilot" Databricks App (FastAPI + Experian-branded UI, embedded Genie) |
| `scaffold/06_sharing/` | Delta Sharing + Unity Catalog row/column entitlements |
| `scaffold/07_orchestration/` | End-to-end multi-task Job + Lakeflow pipeline that runs it all |
| `Experian_Auto_Intelligence_Cloud_OnePager.md` | One-page solution brief |

## The flow

```
generate_data → build_fusion ─┬─→ train_models → deploy_serving
 (gold tables)   (Visual Prep) └─→ create_genie_space
```

Data lands in `experian_agent_demo_catalog.auto`, the fusion pipeline joins the three golds
into a market-360 analytics table and a per-VIN feature table, models train on the features
and deploy to serving endpoints, and a Genie space + the Co-Pilot app sit on top. See
`scaffold/README.md` and each numbered folder's README for details.

## Architecture at a glance

- **Storage / governance:** Unity Catalog (medallion → gold data products)
- **Prep:** Databricks Visual Prep (Lakeflow declarative pipeline)
- **NL analytics:** Genie space with certified example queries
- **ML:** Mosaic AI models on Model Serving
- **App:** Databricks App (FastAPI + React-lite) with a live Genie transparency panel
- **Distribution:** Delta Sharing + Databricks Marketplace
- **Orchestration:** a single Databricks Job chaining all of the above

Built as a Databricks Field Engineering demonstration.
