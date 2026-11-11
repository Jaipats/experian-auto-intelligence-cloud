# scaffold/: source for each stage

Everything here is deployed and wired together by the bundle at the repo root
(`databricks.yml` + `resources/`). See the root `README.md` for deployment.

| Folder | Stage | Deployed as |
|---|---|---|
| `01_data/` | Synthetic Experian feeds → CSV drops in a UC Volume | job task `generate_data` (local script for ad-hoc runs) |
| `02_visual_prep/` | Lakeflow pipeline: Auto Loader bronze → governed gold → fusion | bundle pipeline `experian_auto_fusion` |
| `03_genie/` | Genie space instructions + certified SQL | job task `create_genie_space` |
| `04_models/` | Residual value / days-to-turn / default-risk models | job tasks `train_models`, `deploy_serving` |
| `05_app/` | Inventory & Risk Co-Pilot (FastAPI + JS) | bundle app `copilot` |
| `06_sharing/` | UC entitlements (row filter + column mask); Delta Sharing | job task `setup`; `create_share.sh` (manual, needs metastore privilege) |
| `07_orchestration/` | Job notebooks (`00_setup` … `06_sync_lakebase`) | bundle job `experian_auto_e2e` |
| `08_lakebase/` | Lakebase synced table design notes | job task `sync_lakebase` |
