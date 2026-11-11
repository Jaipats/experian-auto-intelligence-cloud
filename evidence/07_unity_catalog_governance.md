# Evidence — Stage: Unity Catalog governance

_Captured 2026-09-25T22:12:16Z. Catalog `experian_agent_demo_catalog`, schema `auto`._

## Registered models in Unity Catalog Model Registry
```
experian_agent_demo_catalog.auto.residual_value_model  owner=jaideep.patel@databricks.com
   v2  status=READY  aliases=[]
   v1  status=READY  aliases=[]
experian_agent_demo_catalog.auto.days_to_turn_model  owner=jaideep.patel@databricks.com
   v2  status=READY  aliases=[]
   v1  status=READY  aliases=[]
experian_agent_demo_catalog.auto.default_risk_model  owner=jaideep.patel@databricks.com
   v2  status=READY  aliases=[]
   v1  status=READY  aliases=[]
```

## Table ownership & type (data products in the schema)
```
| table_name | table_type | comment |
|---|---|---|
| analytics_market_360 | MATERIALIZED_VIEW | Market 360: VIO share and days-to-turn joined with AutoCheck condition rollups and lending rollups by make/model/model_year/state/month. This is the primary table for the Genie space and AI/BI dashboards. |
| feat_vehicle_fusion | MATERIALIZED_VIEW | Per-VIN feature table fusing AutoCheck history with the vehicle's local VIO demand signal and lending risk profile. Model-ready input for residual value, days-to-turn, and default-risk models. |
| gold_autocheck_vin | MANAGED | Experian AutoCheck vehicle-history records, one row per VIN. Captures ownership, accident, title-brand, odometer and auction history plus an AutoCheck-style condition/desirability score (accs_score). Join keys: make/model/model_year, garaged_state, garaged_zip. |
| gold_lending | MANAGED | Experian automotive credit & lending loan-level dataset. One row per originated auto loan with lender, credit tier, APR, term, LTV, payment and delinquency/default performance. Join keys: make/model/model_year, state/region. |
| gold_vio_market | MANAGED | Experian Velocity Vehicles-in-Operation (VIO) market statistics. One row per make/model/model_year/ZIP/snapshot_month, giving new-vehicle registration counts, cumulative vehicles-in-operation, local market share, and inventory turn speed. Join keys: make/model/model_year, state/dma_region, zip_code. |
```

## Column-level documentation (governed metadata that powers Genie) — gold_lending
```
| column_name | comment |
|---|---|
| loan_id | Surrogate primary key for the auto loan. |
| lender_name | Originating lender (12-lender pool across banks, captives, credit unions, fintechs). |
| lender_type | Lender category: Bank, Captive, Credit Union, or Fintech. |
| make | Financed vehicle manufacturer (shared make pool). |
| model | Financed vehicle model (shared model pool). |
| model_year | Vehicle model year, 2015-2025. |
| region | US macro region of the borrower (shared region pool). |
| state | US state of the borrower. |
| orig_month | Loan origination month (first-of-month date). |
| orig_amount | Original financed amount in USD. |
| apr | Annual percentage rate (%). Rises with lower credit tier and used vehicles. |
| term_months | Loan term in months (36-84). |
| credit_tier | Borrower credit tier: Super Prime, Prime, Near Prime, or Subprime. |
| ltv_pct | Loan-to-value ratio (%). Higher for lower credit tiers. |
| monthly_payment | Scheduled monthly payment in USD (amortized). |
```

---

## Per-customer entitlements: row filter + column mask, enforced live
_Captured 2026-11-11. Defined in `scaffold/06_sharing/entitlements.sql`, attached in the Lakeflow DDL
(`WITH ROW FILTER … ON (state)`, `orig_amount … MASK …`) so they survive every pipeline refresh._

```
| table | row filter | column mask |
|---|---|---|
| gold_vio_market | rf_state(state) | |
| gold_autocheck_vin | rf_state(garaged_state) | |
| gold_lending | rf_state(state) | orig_amount → mask_orig_amount |
| analytics_market_360 | rf_state(state) | |
| feat_vehicle_fusion | rf_state(state) | |
```

Entitlements table (`experian_agent_demo_catalog.auto.entitlements`):
```
| customer | principal | tier | states |
|---|---|---|---|
| Experian (internal) | owners + Co-Pilot app SP | full | * |
| Contoso Dealer Group | sp_contoso (1ffb3038-…) | standard | CA, NV, AZ |
| Northwind Auto Finance | sp_northwind (29ddede5-…) | full | TX, FL |
```

### The same SQL, run as three identities
```sql
SELECT current_user() AS caller, count(*) AS loans, count(DISTINCT state) AS states_visible,
       array_join(array_sort(collect_set(state)), ',') AS states,
       round(sum(orig_amount),2) AS total_orig_amount
FROM experian_agent_demo_catalog.auto.gold_lending;
```
```
| caller | loans | states_visible | states | total_orig_amount |
|---|---|---|---|---|
| jaideep.patel@databricks.com (owner) | 30000 | 25 | AZ,CA,CO,DC,FL,GA,ID,IL,MA,MI,MN,MO,NC,NJ,NM,NV,NY,OH,OR,PA,TN,TX,UT,WA,WI | 863743169.26 |
| sp_contoso (1ffb3038-…) | 5351 | 3 | AZ,CA,NV | 155049000.0 |
| sp_northwind (29ddede5-…) | 4527 | 2 | FL,TX | 131481219.31 |
```

### Column mask: Contoso (standard tier) sees amounts rounded to $1,000
```
-- owner
| loan_id | state | credit_tier | orig_amount | apr |
| 9000032 | AZ | Subprime    | 34111.97 | 19.74 |
| 9000001 | CA | Super Prime | 20244.24 | 2.58  |
-- sp_contoso
| 9000032 | AZ | Subprime    | 34000.0  | 19.74 |
| 9000001 | CA | Super Prime | 20000.0  | 2.58  |
| 9000048 | NV | Prime       | 34000.0  | 8.58  |
-- sp_northwind (full tier → exact)
| 9000004 | FL | Super Prime | 36744.95 | 5.71  |
| 9000002 | TX | Near Prime  | 48742.88 | 10.06 |
```

### The filter flows through to the Genie / analytics table
```
SELECT count(*) AS market_rows, array_join(array_sort(collect_set(state)), ',') AS states
FROM experian_agent_demo_catalog.auto.analytics_market_360;

owner        | 4320 | AZ,CA,CO,DC,FL,GA,ID,IL,MA,MI,MN,MO,NC,NJ,NM,NV,NY,OH,OR,PA,TN,TX,UT,WA,WI
sp_contoso   |  746 | AZ,CA,NV
sp_northwind |  676 | FL,TX
```

### Least privilege: customers cannot read the operational table
```
sp_contoso   → SELECT count(*) FROM …auto.vin_serving
[INSUFFICIENT_PERMISSIONS] Principal 'sp_contoso (Project Contoso)' does not have SELECT on Table
'experian_agent_demo_catalog.auto.vin_serving'. SQLSTATE: 42501
sp_northwind → [INSUFFICIENT_PERMISSIONS] … 'sp_northwind (Project Northwind)' does not have SELECT …
```

## Lineage: captured automatically by Unity Catalog (`system.access.table_lineage`)
```sql
SELECT source_table_full_name, target_table_full_name, entity_type, max(event_time)
FROM system.access.table_lineage
WHERE target_table_full_name LIKE 'experian_agent_demo_catalog.auto.%' AND event_date >= current_date() - 1
GROUP BY ALL;
```
```
| source | target | entity_type |
|---|---|---|
| NULL (file source) | bronze_vio_market    | PIPELINE |
| NULL (file source) | bronze_autocheck_vin | PIPELINE |
| NULL (file source) | bronze_lending       | PIPELINE |
| bronze_vio_market    | gold_vio_market      | PIPELINE |
| bronze_autocheck_vin | gold_autocheck_vin   | PIPELINE |
| bronze_lending       | gold_lending         | PIPELINE |
| gold_autocheck_vin   | auto_condition_rollup | PIPELINE |
| gold_lending         | auto_lending_rollup  | PIPELINE |
| gold_vio_market      | analytics_market_360 | PIPELINE |
| auto_condition_rollup | analytics_market_360 | PIPELINE |
| auto_lending_rollup  | analytics_market_360 | PIPELINE |
| gold_autocheck_vin   | feat_vehicle_fusion  | PIPELINE |
| gold_vio_market      | feat_vehicle_fusion  | PIPELINE |
| auto_lending_rollup  | feat_vehicle_fusion  | PIPELINE |
| feat_vehicle_fusion  | vin_serving          | PIPELINE |
| gold_autocheck_vin   | vin_serving          | PIPELINE |
| analytics_market_360 | analytics_market_360_profile_metrics | JOB (data-quality monitor) |
```
_`table_lineage` records the file-based source of the bronze tables as NULL; the Volume path is captured per row in `_source_file` instead (see `01_lakeflow_ingest.md`)._
