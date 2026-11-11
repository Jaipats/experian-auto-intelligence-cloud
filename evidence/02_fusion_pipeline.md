# Evidence — Stage 2: Visual Prep / Lakeflow fusion pipeline

_Originally captured 2026-09-25; row counts re-verified 2026-11-11 after consolidation. The fusion views are now built by the **same** Lakeflow pipeline (`experian_auto_fusion`) that ingests the raw files — one pipeline, one lineage graph: `raw Volume → bronze_* → gold_* → fusion → vin_serving`. Previously each fusion view was a standalone DBSQL materialized view._

## Materialized views produced by the fusion pipeline
```
| view | rows |
|---|---|
| analytics_market_360 | 4320 |
| feat_vehicle_fusion | 20000 |
| auto_condition_rollup | 4710 |
| auto_lending_rollup | 4869 |
| vin_serving | 20000 |
```
`vin_serving` (new) is the operational per-VIN record — display fields + model features — and is
the source of the Lakebase synced table (see `03_lakebase_serving.md`). `analytics_market_360` and
`feat_vehicle_fusion` carry the `rf_state` row filter (see `07_unity_catalog_governance.md`).

## Sample: analytics_market_360 (fused VIO + AutoCheck condition + lending — one row per make/model/geo/month)
```
| make | model | model_year | body_style | state | avg_days_to_turn | market_share_pct | avg_accs_score | clean_title_rate | avg_apr | default_rate | lender_count |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Jeep | Grand Cherokee | 2015 | SUV | MN | 8 | 7.11 | 31.0 | 1.0 | 6.85 | 0.0 | 2 |
| Jeep | Grand Cherokee | 2025 | SUV | GA | 8 | 2.67 | 87.7 | 1.0 | 7.19 | 0.0 | 3 |
| Subaru | Outback | 2016 | SUV | GA | 8 | 3.41 | 53.0 | 0.8 | 8.81 | 0.0 | 7 |
| Toyota | RAV4 | 2020 | SUV | FL | 9 | 2.95 | 63.5 | 0.8 | 7.59 | 0.0 | 10 |
| Nissan | Rogue | 2018 | SUV | GA | 9 | 7.05 | 71.5 | 1.0 | 11.16 | 0.0 | 5 |
| Hyundai | Tucson | 2017 | SUV | NY | 11 | 1.99 | 56.3 | 0.875 | 10.62 | 0.0 | 7 |
| Nissan | Rogue | 2019 | SUV | TX | 13 | 2.22 | 62.1 | 0.875 | 10.96 | 0.111 | 6 |
| Chevrolet | Equinox | 2019 | SUV | NY | 13 | 2.47 | 70.8 | 1.0 | 8.08 | 0.0 | 8 |
```

## Sample: feat_vehicle_fusion (per-VIN model features — feeds the three Mosaic AI models)
```
| vin | make | model | model_year | mileage | accs_score | accident_count | local_avg_days_to_turn | segment_default_rate | segment_avg_apr |
|---|---|---|---|---|---|---|---|---|---|
| 8NMVSJJGZL6NZPYM8 | Toyota | RAV4 | 2015 | 141965 | 8 | 1 |  | 0.0 | 15.11 |
| K0V84PB0STU0L7V53 | Ford | F-250 | 2019 | 95620 | 58 | 1 | 48.0 | 0.0 | 9.76 |
| 1ESKX1K3U140RTF4P | Honda | CR-V | 2020 | 92538 | 79 | 1 | 33.0 | 0.0 | 8.69 |
| RUU340BML37JXA5WT | Toyota | Camry | 2020 | 70240 | 84 | 0 | 62.0 | 0.0 | 9.05 |
| XHYFCS8DAWZPN7SAU | Tesla | Model Y | 2015 | 137019 | 66 | 1 | 47.0 | 0.0 | 9.95 |
| NY20NTJR9JH87DEZY | Ford | F-250 | 2016 | 141454 | 45 | 2 |  | 0.0 | 12.86 |
| 3030LW54SBDVPSNPD | Toyota | Camry | 2016 | 101653 | 63 | 1 |  | 0.0 | 8.96 |
| 01P1PLMSTHFRSZ6LP | Ford | F-150 | 2015 | 122688 | 68 | 0 | 62.0 | 0.0 | 10.79 |
```
