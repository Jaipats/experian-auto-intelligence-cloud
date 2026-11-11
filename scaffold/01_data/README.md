# 01 — Synthetic Data Generation

Generates the three Experian Automotive feeds with Polars + NumPy + Mimesis and lands
them as **CSV flat-file drops** in the Unity Catalog Volume
`<catalog>.<schema>.raw` (via Databricks Connect, serverless). That mirrors
how Experian ships data today. Each run writes a new `batch_<UTC timestamp>/` folder per
feed; the Lakeflow pipeline (`../02_visual_prep`) ingests new files with Auto Loader and
builds the gold tables. Seed = 42, so runs are reproducible and re-landed keys de-duplicate.

## Feeds landed → gold tables built by Lakeflow

| Volume folder → gold table | Rows | Notes |
|---|---|---|
| `raw/vio_market/` → `gold_vio_market` | ~4,320  | 6 monthly snapshots (2025-01 → 2025-06), share computed within state+month |
| `raw/autocheck_vin/` → `gold_autocheck_vin` | 20,000  | `accs_score` derived from accidents/owners/mileage/title/rollback |
| `raw/lending/` → `gold_lending` | 30,000  | APR/LTV/delinquency/default keyed off `credit_tier`; real amortized payment |

**Join keys overlap by construction:** all three tables draw make/model/model_year from
one 18-model pool and state/region/zip from one shared 40-ZIP geography pool. This is what
lets `02_visual_prep` fuse them.

## How it runs

In a deployment the job's `generate_data` task runs
`../07_orchestration/notebooks/01_generate_data.py`, which contains the same generator on
ambient serverless Spark. Each job run lands a new batch, and Auto Loader ingests only the new
files.

To land a batch from your laptop instead (Databricks Connect, serverless):

```bash
# uses .env at the repo root: DATABRICKS_CONFIG_PROFILE, CATALOG, optional SCHEMA
set -a; . ./.env; set +a
uv run --python 3.12 \
  --with polars --with numpy --with mimesis --with pandas --with "databricks-connect>=16.4,<17.0" \
  scaffold/01_data/gen_experian_auto.py
```

The generator:
1. Creates the schema and the `raw` Volume if they don't exist.
2. Builds the three DataFrames in memory, with the correlations described above.
3. Writes each one as a single CSV with a header to `/Volumes/<catalog>/<schema>/raw/<feed>/batch_<ts>/`.
4. Prints the landed paths. Then run the pipeline (or the job) to ingest them.

Table and column `COMMENT`s (Genie relies on them), data-quality expectations and the UC
row filter / column mask are declared in the pipeline DDL, not here.

## Verify

```sql
SELECT 'vio' t, COUNT(*) n FROM <catalog>.<schema>.gold_vio_market
UNION ALL SELECT 'autocheck', COUNT(*) FROM <catalog>.<schema>.gold_autocheck_vin
UNION ALL SELECT 'lending', COUNT(*) FROM <catalog>.<schema>.gold_lending;
```
