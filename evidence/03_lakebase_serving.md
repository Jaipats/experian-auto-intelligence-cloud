# Evidence — Stage 3: Lakebase (Postgres OLTP operational serving)

_Re-captured 2026-11-11. Lakebase Autoscaling project `experian-auto-oltp` (branch `production`, endpoint `primary`), database `experian_auto`._
_Populated by a **Lakebase synced table**, a managed Lakeflow sync pipeline, from the Lakeflow-built Delta source
`experian_agent_demo_catalog.auto.vin_serving`. This replaces the one-off reverse-ETL script. Serves the Co-Pilot's `GET /api/vin/{vin}` point lookup._

```
UC Delta  experian_agent_demo_catalog.auto.vin_serving          (Lakeflow MV, 20,000 VINs)
   │  Lakebase synced table  experian_agent_demo_catalog.auto.vin_serving_online
   │  mode SNAPSHOT · sync pipeline 524ad5aa-9b03-4f05-a953-14ad51f8f7b9
   │  refreshed by job task `sync_lakebase` right after the fusion pipeline
   ▼
Postgres  experian_auto.auto.vin_serving_online   (PRIMARY KEY vin)  ←  Co-Pilot /api/vin/{vin}
```

## Synced table status
```
detailed_state                    : SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
unity_catalog_provisioning_state  : ACTIVE
last sync (job run 1024333042185272): 2026-11-11T18:44:17Z → 18:44:29Z  (≈11 s for 20,000 rows)
source delta_commit_version       : 4
```

## Postgres table created and owned by the sync (PK index on vin)
```
 Schema |        Name        |       Type        |          Owner
--------+--------------------+-------------------+-------------------------
 auto   | vin_serving_online | partitioned table | databricks_writer_16595

Indexes:
    "vin_serving_online_pkey" PRIMARY KEY, btree (vin)
```

## Row count in Lakebase
```
 rows_in_lakebase
------------------
            20000
(1 row)
```

## Single-VIN operational point lookup: query plan confirms a primary-key index scan
```
EXPLAIN ANALYZE SELECT * FROM auto.vin_serving_online WHERE vin = 'RUU340BML37JXA5WT';

 Index Scan using "__db_tmp_bb7d2535-…_pkey" on partition_82331 vin_serving_online
     (cost=0.29..8.30 rows=1 width=175) (actual time=0.016..0.017 rows=1 loops=1)
   Index Cond: (vin = 'RUU340BML37JXA5WT'::text)
 Planning Time: 0.255 ms
 Execution Time: 0.088 ms
```

## App service principal access survives re-syncs
After the job-triggered snapshot refresh, the Co-Pilot SP still holds its grant:
```
               grantee                | privilege_type
--------------------------------------+----------------
 b4227734-bc68-4c81-9faa-53f6d645c6be | SELECT
```
and the live app keeps serving from Lakebase (`GET /api/vin/RUU340BML37JXA5WT` → `served_by: "lakebase"`,
`predicted_residual_value: 22403.0`). See `05_app_responses.md`.

> **Why SNAPSHOT, not TRIGGERED:** incremental (TRIGGERED/CONTINUOUS) sync reads the source's Change
> Data Feed, and CDF reads from a materialized view are Beta (they need the PREVIEW channel). A full
> snapshot of 20k rows takes about 11 s, so SNAPSHOT is the robust choice here. At production scale,
> make `vin_serving` a streaming table or a CDF-enabled Delta table and switch to TRIGGERED/CONTINUOUS.

## Secondary index example — top-condition vehicles garaged in California
```
        vin        | make  |  model  | model_year | accs_score 
-------------------+-------+---------+------------+------------
 7G2KR1C4CNUL3V8AM | Ford  | F-250   |       2024 |        100
 XMBN7UVERVPH7R81F | Honda | CR-V    |       2024 |        100
 HBWMR8CXWV5ATM6HX | Tesla | Model 3 |       2025 |        100
 4LDGV5ZHEY845BESL | Ram   | 1500    |       2025 |        100
 YEMGVK9A596DPVMUU | Tesla | Model 3 |       2021 |        100
(5 rows)

```
