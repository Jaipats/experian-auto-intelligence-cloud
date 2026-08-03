# 01 — Synthetic Data Generation

Generates the three Experian Automotive gold datasets into
`experian_agent_demo_catalog.auto` using Polars + NumPy + Mimesis, written to Unity
Catalog via Databricks Connect (serverless). Seed = 42, so runs are reproducible.

## Tables produced

| Table | Rows | Notes |
|---|---|---|
| `gold_vio_market`    | ~4,320  | 6 monthly snapshots (2025-01 → 2025-06), share computed within state+month |
| `gold_autocheck_vin` | 20,000  | `accs_score` derived from accidents/owners/mileage/title/rollback |
| `gold_lending`       | 30,000  | APR/LTV/delinquency/default keyed off `credit_tier`; real amortized payment |

**Join keys overlap by construction:** all three tables draw make/model/model_year from
one 18-model pool and state/region/zip from one shared 40-ZIP geography pool. This is what
lets `02_visual_prep` fuse them.

## Prerequisites

1. Databricks CLI authenticated to the workspace with a profile whose identity can
   **create the `auto` schema**:

   ```bash
   databricks auth login \
     --host https://fevm-experian-agent-demo.cloud.databricks.com \
     --profile fe-vm-experian-agent-demo
   ```

   > The catalog `experian_agent_demo_catalog` is owned by `jaideep.patel@databricks.com`.
   > `CREATE SCHEMA` on the catalog is required. If you'd rather run under a service
   > principal, grant it once:
   > ```sql
   > GRANT CREATE SCHEMA ON CATALOG experian_agent_demo_catalog TO `<sp-application-id>`;
   > ```

2. `uv` (or pip) for the Python dependencies.

## Run

```bash
DBX_PROFILE=fe-vm-experian-agent-demo uv run --python 3.12 \
  --with polars --with numpy --with mimesis --with "databricks-connect>=16.4,<17.0" \
  gen_experian_auto.py
```

The script:
1. `CREATE SCHEMA IF NOT EXISTS experian_agent_demo_catalog.auto`
2. Builds the three DataFrames in memory (with the correlations described above)
3. Writes each as a managed Delta table
4. Applies a table-level `COMMENT` and per-column `COMMENT`s (important — Genie uses these)
5. Prints row counts for verification

## Verify

```sql
SELECT 'vio' t, COUNT(*) n FROM experian_agent_demo_catalog.auto.gold_vio_market
UNION ALL SELECT 'autocheck', COUNT(*) FROM experian_agent_demo_catalog.auto.gold_autocheck_vin
UNION ALL SELECT 'lending', COUNT(*) FROM experian_agent_demo_catalog.auto.gold_lending;
```
