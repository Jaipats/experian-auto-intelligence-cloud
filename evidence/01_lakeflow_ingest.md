# Evidence — Stage 1: Lakeflow ingestion (raw files → Auto Loader → bronze → gold)

_Re-captured 2026-11-11 from workspace `fevm-experian-agent-demo`, catalog `experian_agent_demo_catalog.auto`, via SQL warehouse `527be374a9154957`.
Pipeline `experian_auto_fusion` (`c6259e3f-7d6a-4661-a58a-cec0442310de`); job run [`1024333042185272`](https://fevm-experian-agent-demo.cloud.databricks.com/?o=7474648980404788#job/729857403662711/run/1024333042185272)._

The generator no longer writes tables. It lands Experian-style **flat-file drops** (CSV) in the
Unity Catalog Volume `experian_agent_demo_catalog.auto.raw`; the Lakeflow pipeline ingests them
incrementally with **Auto Loader** (`STREAM read_files`) into `bronze_*` streaming tables, then
builds typed, de-duplicated, quality-checked `gold_*` materialized views
(`scaffold/02_visual_prep/fusion_pipeline.sql`).

## 1. Raw landing zone — two file drops in the UC Volume
```
/Volumes/experian_agent_demo_catalog/auto/raw/
├── vio_market/     batch_20261111T175042Z/part-00000-…c000.csv     424,466 B
│                   batch_20261111T184201Z/part-00000-…c000.csv     424,466 B
├── autocheck_vin/  batch_20261111T175042Z/part-00000-…c000.csv   1,909,442 B
│                   batch_20261111T184201Z/part-00000-…c000.csv   1,909,442 B
└── lending/        batch_20261111T175042Z/part-00000-…c000.csv   3,941,507 B
                    batch_20261111T184201Z/part-00000-…c000.csv   3,941,507 B
```

## 2. Bronze — Auto Loader picked up each file exactly once
```
| table | rows | files | batches |
|---|---|---|---|
| bronze_autocheck_vin | 40000 | 2 | 2 |
| bronze_lending | 60000 | 2 | 2 |
| bronze_vio_market | 8640 | 2 | 2 |
```
Incremental, not reprocessing: batch 1 was ingested by the 18:17 update; the 18:43 update
(triggered by the job) ingested **only** the new batch-2 file.
```
| batch (bronze_lending) | rows | ingested_at |
|---|---|---|
| batch_20261111T175042Z | 30000 | 2026-11-11T18:17:17.103Z |
| batch_20261111T184201Z | 30000 | 2026-11-11T18:43:05.523Z |
```
Every bronze row carries file-level lineage (`_source_file`, `_file_modified_at`, `_ingested_at`):
```
| loan_id | state | orig_amount | _source_file | _ingested_at |
|---|---|---|---|---|
| 9000001 | CA | 20244.24 | lending/batch_20261111T175042Z/part-00000-…-c000.csv | 2026-11-11T18:17:17.103Z |
| 9000001 | CA | 20244.24 | lending/batch_20261111T184201Z/part-00000-…-c000.csv | 2026-11-11T18:43:05.523Z |
```

## 3. Gold — de-duplicated (latest file wins per key) + data-quality expectations
```
| table | type | rows | expectations (passed / failed) |
|---|---|---|---|
| gold_vio_market | MATERIALIZED_VIEW | 4320 | valid_key 4320/0 · valid_state 4320/0 · valid_market_share 4320/0 · non_negative_vio (warn) 4320/0 |
| gold_autocheck_vin | MATERIALIZED_VIEW | 20000 | valid_vin 20000/0 · valid_accs_score 20000/0 · valid_model_year 20000/0 · plausible_mileage (warn) 20000/0 |
| gold_lending | MATERIALIZED_VIEW | 30000 | valid_key 30000/0 · valid_apr 30000/0 · valid_ltv 30000/0 · valid_credit_tier (warn) 30000/0 |
```
_(from the pipeline event log: `event_log('c6259e3f-…')`, `flow_progress.data_quality.expectations`)_

**Parity with the previous (script-written) gold tables** — row-for-row identical:
```
| table | new_rows | old_rows | rows in old EXCEPT new |
|---|---|---|---|
| gold_vio_market | 4320 | 4320 | 0 |
| gold_autocheck_vin | 20000 | 20000 | 0 |
| gold_lending | 30000 | 30000 | 0 |
```
All 48 gold columns carry Unity Catalog comments (declared in the pipeline DDL, so they survive every refresh): `48 documented, 0 undocumented`.

## Sample: gold_vio_market (Vehicles-in-Operation / Velocity market stats)
```
| make | model | model_year | body_style | state | snapshot_month | vio_count | market_share_pct | avg_days_to_turn |
|---|---|---|---|---|---|---|---|---|
| Chevrolet | Equinox | 2020 | SUV | TX | 2025-04-01T00:00:00.000Z | 45484 | 5.01 | 57 |
| Subaru | Outback | 2020 | SUV | MI | 2025-06-01T00:00:00.000Z | 43895 | 9.02 | 51 |
| Jeep | Grand Cherokee | 2021 | SUV | PA | 2025-06-01T00:00:00.000Z | 43768 | 5.75 | 38 |
| Toyota | RAV4 | 2020 | SUV | CA | 2025-01-01T00:00:00.000Z | 43491 | 2.64 | 38 |
| Subaru | Outback | 2018 | SUV | AZ | 2025-01-01T00:00:00.000Z | 43330 | 5.09 | 63 |
| Honda | CR-V | 2025 | SUV | ID | 2025-06-01T00:00:00.000Z | 43076 | 7.88 | 44 |
| Nissan | Rogue | 2020 | SUV | OR | 2025-04-01T00:00:00.000Z | 42664 | 9.56 | 19 |
| Ford | Explorer | 2020 | SUV | FL | 2025-03-01T00:00:00.000Z | 42376 | 3.27 | 52 |
```

## Sample: gold_autocheck_vin (per-VIN vehicle history)
```
| vin | make | model | model_year | mileage | owner_count | accident_count | title_brand | accs_score | garaged_state |
|---|---|---|---|---|---|---|---|---|---|
| 3ZBK5A3ZEGZAUHKG9 | Ford | F-150 | 2022 | 54156 | 4 | 0 | Clean | 82 | CA |
| D8BU88L7Y0MRRAUTA | Toyota | RAV4 | 2017 | 80515 | 4 | 2 | Clean | 66 | AZ |
| DSHYDNSU0M56NANRW | Nissan | Rogue | 2015 | 165390 | 5 | 1 | Clean | 52 | MA |
| 5B5GXFBK2F09RK0GS | Ford | F-250 | 2025 | 22980 | 1 | 0 | Clean | 95 | UT |
| 86YZ0JG3ER56UV5LR | Subaru | Outback | 2023 | 46239 | 3 | 1 | Clean | 74 | NY |
| F8S0BH5FV547KCXFR | Toyota | RAV4 | 2019 | 72555 | 5 | 1 | Clean | 79 | FL |
| H8PR0JAC045WS3TGC | Nissan | Rogue | 2023 | 39952 | 5 | 0 | Clean | 80 | CA |
| 8SXE6GVWXJ2TAXYW1 | Tesla | Model Y | 2023 | 40726 | 1 | 0 | Salvage | 40 | NY |
```

## Sample: gold_lending (auto loan / lease originations)
```
| loan_id | make | model | model_year | lender_type | credit_tier | apr | orig_amount | ltv_pct | delinquency_30d_flag | region |
|---|---|---|---|---|---|---|---|---|---|---|
| 9000000 | Toyota | RAV4 | 2023 | Fintech | Prime | 8.73 | 29102.52 | 88.2 | 0 | West |
| 9000001 | Ford | F-150 | 2021 | Bank | Super Prime | 2.58 | 20244.24 | 72.4 | 0 | West |
| 9000002 | Nissan | Rogue | 2021 | Credit Union | Near Prime | 10.06 | 48742.88 | 105.9 | 0 | Southwest |
| 9000003 | Jeep | Grand Cherokee | 2021 | Bank | Prime | 7.04 | 35974.48 | 90.3 | 0 | Mountain |
| 9000004 | Ford | F-250 | 2021 | Bank | Super Prime | 5.71 | 36744.95 | 74.0 | 0 | Southeast |
| 9000005 | Tesla | Model Y | 2019 | Fintech | Super Prime | 6.01 | 23557.71 | 73.7 | 0 | Midwest |
| 9000006 | Tesla | Model 3 | 2025 | Captive | Near Prime | 13.35 | 18505.91 | 101.8 | 0 | Southeast |
| 9000007 | Toyota | Sienna | 2022 | Fintech | Prime | 8.83 | 29986.62 | 100.0 | 0 | West |
```
