# 08 — Lakebase (Postgres OLTP operational serving)

The analytical estate (VIO market, lending, fusion views) is served from Unity Catalog
through a SQL warehouse. The **per-VIN point lookup** behind the Co-Pilot's
`GET /api/vin/{vin}` is a latency-sensitive operational read, so it is served from
**Lakebase Postgres**, where a primary-key index lookup returns in well under a millisecond
(see `../../evidence/03_lakebase_serving.md`).

A **Lakebase synced table**, which is a managed Lakeflow sync pipeline, keeps the Postgres
copy up to date from the Lakeflow-built Delta view `vin_serving`. No hand-written reverse ETL
is involved.

```
Lakeflow pipeline ──▶ <catalog>.<schema>.vin_serving               (Delta materialized view)
                         │  synced table <catalog>.<schema>.vin_serving_online  (SNAPSHOT)
                         ▼
        Lakebase <pg_database>.<schema>.vin_serving_online  (PRIMARY KEY vin) ──▶ Co-Pilot /api/vin
```

## How it's deployed

Everything here is automated by the bundle:

| Piece | Where |
|---|---|
| Lakebase Autoscaling project | `scripts/deploy.sh` creates `LAKEBASE_PROJECT` if missing (default `experian-auto-oltp`) |
| App ↔ Lakebase binding | `resources/copilot.app.yml`: a `postgres` app resource injects `PGHOST/PGUSER/PGPORT/PGDATABASE` |
| Synced table create / refresh | job task `sync_lakebase` → `../07_orchestration/notebooks/06_sync_lakebase.py` |
| Postgres `SELECT` for the app SP | same task (runs after every sync; the grant survives snapshot refreshes) |

The synced table can't be a bundle resource because its source (`vin_serving`) only exists
after the pipeline's first run. The job task creates it on that first run and refreshes it on
every later run.

## Design notes

**Why SNAPSHOT and not TRIGGERED / CONTINUOUS.** Incremental sync modes read the source's
Change Data Feed. `vin_serving` is a materialized view, and CDF reads from MVs are still
**Beta** (they need the PREVIEW channel and an external-metadata flag). A full snapshot of
20k rows takes about 11 s, so SNAPSHOT is the robust choice. At production scale, make
`vin_serving` a CDF-enabled streaming/Delta table and switch to `TRIGGERED` or `CONTINUOUS`
for second-level freshness.

**Why the synced table sits in `<catalog>.<schema>`.** Registering the Lakebase database as
its own UC catalog needs `CREATE CATALOG` on the metastore. Autoscaling synced tables can name
the target `branch` + `postgres_database` directly, so the UC entry sits beside its source and
the Postgres schema takes the UC schema name.

## App wiring

The Co-Pilot app (`../05_app/backend/lakebase.py`) uses the official Databricks Apps pattern:
a psycopg connection pool whose connection class mints a fresh OAuth credential for each
connection (`POST /api/2.0/postgres/credentials`). `LAKEBASE_TABLE` (set by the bundle to
`<schema>.vin_serving_online`) selects the table. `GET /api/vin/{vin}` reports
`served_by: "lakebase"` and falls back to the SQL warehouse if Lakebase is unavailable.

## Manual refresh

```bash
databricks postgres get-synced-table synced_tables/<catalog>.<schema>.vin_serving_online   # → status.pipeline_id
databricks pipelines start-update <pipeline_id>
```
