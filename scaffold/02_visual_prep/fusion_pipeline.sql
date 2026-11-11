-- =============================================================================
-- Lakeflow Spark Declarative Pipeline — Experian Auto Intelligence Cloud
-- Target catalog.schema: the pipeline's catalog/schema. `${experian.catalog}` and
-- `${experian.schema}` are pipeline configuration values set by the bundle
-- (resources/experian_auto.pipeline.yml), so the same SQL deploys to any catalog/schema.
--
--   raw CSV drops in UC Volume  /Volumes/${experian.catalog}/${experian.schema}/raw/<feed>/
--        │  Auto Loader (STREAM read_files) — incremental, exactly-once file ingest
--        ▼
--   bronze_*  streaming tables   raw strings + _source_file / _ingested_at lineage cols
--        │  typed, de-duplicated (latest file wins), data-quality EXPECTations
--        ▼
--   gold_*    materialized views documented columns + UC row filter / column mask
--        │  fusion (Visual Prep flow)
--        ▼
--   analytics_market_360  (Genie / AI-BI)     feat_vehicle_fusion (ML features)
--   vin_serving           (operational source for the Lakebase synced table)
--
-- Prereq: the job's `setup` task (00_setup) creates rf_state / mask_orig_amount first.
-- =============================================================================

-- #############################################################################
-- BRONZE — Auto Loader ingest of raw flat files
-- #############################################################################

CREATE OR REFRESH STREAMING TABLE bronze_vio_market
COMMENT "Bronze: raw vio_market CSV drops ingested incrementally by Auto Loader from /Volumes/${experian.catalog}/${experian.schema}/raw/vio_market/. All columns kept as STRING; _rescued_data captures malformed fields."
AS SELECT
  *,
  _metadata.file_path              AS _source_file,
  _metadata.file_modification_time AS _file_modified_at,
  current_timestamp()              AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${experian.catalog}/${experian.schema}/raw/vio_market/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE bronze_autocheck_vin
COMMENT "Bronze: raw autocheck_vin CSV drops ingested incrementally by Auto Loader from /Volumes/${experian.catalog}/${experian.schema}/raw/autocheck_vin/. All columns kept as STRING; _rescued_data captures malformed fields."
AS SELECT
  *,
  _metadata.file_path              AS _source_file,
  _metadata.file_modification_time AS _file_modified_at,
  current_timestamp()              AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${experian.catalog}/${experian.schema}/raw/autocheck_vin/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE bronze_lending
COMMENT "Bronze: raw lending CSV drops ingested incrementally by Auto Loader from /Volumes/${experian.catalog}/${experian.schema}/raw/lending/. All columns kept as STRING; _rescued_data captures malformed fields."
AS SELECT
  *,
  _metadata.file_path              AS _source_file,
  _metadata.file_modification_time AS _file_modified_at,
  current_timestamp()              AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${experian.catalog}/${experian.schema}/raw/lending/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

-- #############################################################################
-- GOLD — typed, de-duplicated, quality-checked, governed data products
-- #############################################################################

CREATE OR REFRESH MATERIALIZED VIEW gold_vio_market (
  vio_id BIGINT COMMENT 'Surrogate primary key for the VIO market record.',
  make STRING COMMENT 'Vehicle manufacturer (shared make pool; joins to autocheck/lending).',
  model STRING COMMENT 'Vehicle model name (shared model pool).',
  trim STRING COMMENT 'Trim level of the model.',
  model_year BIGINT COMMENT 'Model year, 2015-2025.',
  body_style STRING COMMENT 'Body style: SUV, Sedan, Truck, EV, or Van.',
  fuel_type STRING COMMENT 'Fuel/powertrain type: Gas, Hybrid, EV, or Diesel.',
  zip_code STRING COMMENT '5-digit garaging/registration ZIP (shared 40-ZIP pool).',
  dma_region STRING COMMENT 'Designated Market Area / metro for the ZIP.',
  state STRING COMMENT 'US state abbreviation.',
  registration_count BIGINT COMMENT 'New vehicle registrations for this cell in the snapshot month.',
  vio_count BIGINT COMMENT 'Cumulative vehicles in operation (on-road units) for this cell.',
  market_share_pct DOUBLE COMMENT 'Registration share (%) within the state for the snapshot month.',
  avg_days_to_turn BIGINT COMMENT 'Average dealer days-to-turn (inventory velocity) in days.',
  snapshot_month TIMESTAMP COMMENT 'First-of-month date the statistics were snapshotted.',
  CONSTRAINT valid_key EXPECT (vio_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_state EXPECT (length(state) = 2) ON VIOLATION DROP ROW,
  CONSTRAINT valid_market_share EXPECT (market_share_pct BETWEEN 0 AND 100) ON VIOLATION DROP ROW,
  CONSTRAINT non_negative_vio EXPECT (vio_count >= 0)
)
COMMENT "Experian Velocity Vehicles-in-Operation (VIO) market statistics. One row per make/model/model_year/ZIP/snapshot_month, giving new-vehicle registration counts, cumulative vehicles-in-operation, local market share, and inventory turn speed. Join keys: make/model/model_year, state/dma_region, zip_code. Built by Lakeflow from bronze_vio_market (latest file wins per vio_id)."
WITH ROW FILTER ${experian.catalog}.${experian.schema}.rf_state ON (state)
AS SELECT
  CAST(vio_id AS BIGINT) AS vio_id,
  CAST(make AS STRING) AS make,
  CAST(model AS STRING) AS model,
  CAST(trim AS STRING) AS trim,
  CAST(model_year AS BIGINT) AS model_year,
  CAST(body_style AS STRING) AS body_style,
  CAST(fuel_type AS STRING) AS fuel_type,
  CAST(zip_code AS STRING) AS zip_code,
  CAST(dma_region AS STRING) AS dma_region,
  CAST(state AS STRING) AS state,
  CAST(registration_count AS BIGINT) AS registration_count,
  CAST(vio_count AS BIGINT) AS vio_count,
  CAST(market_share_pct AS DOUBLE) AS market_share_pct,
  CAST(avg_days_to_turn AS BIGINT) AS avg_days_to_turn,
  CAST(snapshot_month AS TIMESTAMP) AS snapshot_month
FROM (
  SELECT *, row_number() OVER (PARTITION BY vio_id ORDER BY _file_modified_at DESC, _source_file DESC) AS _rn
  FROM bronze_vio_market
)
WHERE _rn = 1;

CREATE OR REFRESH MATERIALIZED VIEW gold_autocheck_vin (
  vin STRING COMMENT 'Synthetic 17-character Vehicle Identification Number (no I/O/Q).',
  make STRING COMMENT 'Vehicle manufacturer (shared make pool).',
  model STRING COMMENT 'Vehicle model name (shared model pool).',
  trim STRING COMMENT 'Trim level of the model.',
  model_year BIGINT COMMENT 'Model year, 2015-2025.',
  mileage BIGINT COMMENT 'Last reported odometer reading in miles.',
  owner_count BIGINT COMMENT 'Number of distinct owners on record (1-6).',
  accident_count BIGINT COMMENT 'Number of reported accidents (0-5).',
  title_brand STRING COMMENT 'Title brand: Clean, Salvage, Rebuilt, or Flood.',
  odometer_rollback_flag BIGINT COMMENT '1 if a suspected odometer rollback was detected, else 0.',
  auction_count BIGINT COMMENT 'Number of times the vehicle passed through auction.',
  accs_score BIGINT COMMENT 'AutoCheck-style condition/desirability score 0-100; higher is better. Decreases with accidents, owners, mileage, adverse title brands and odometer rollback.',
  last_reported_date TIMESTAMP COMMENT 'Date of the most recent history event on the VIN.',
  garaged_zip STRING COMMENT '5-digit ZIP where the vehicle is garaged (shared ZIP pool).',
  garaged_state STRING COMMENT 'US state where the vehicle is garaged.',
  CONSTRAINT valid_vin EXPECT (vin RLIKE '^[A-HJ-NPR-Z0-9]{17}$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_accs_score EXPECT (accs_score BETWEEN 0 AND 100) ON VIOLATION DROP ROW,
  CONSTRAINT valid_model_year EXPECT (model_year BETWEEN 1990 AND 2030) ON VIOLATION DROP ROW,
  CONSTRAINT plausible_mileage EXPECT (mileage BETWEEN 0 AND 500000)
)
COMMENT "Experian AutoCheck vehicle-history records, one row per VIN. Captures ownership, accident, title-brand, odometer and auction history plus an AutoCheck-style condition/desirability score (accs_score). Join keys: make/model/model_year, garaged_state, garaged_zip. Built by Lakeflow from bronze_autocheck_vin (latest file wins per vin)."
WITH ROW FILTER ${experian.catalog}.${experian.schema}.rf_state ON (garaged_state)
AS SELECT
  CAST(vin AS STRING) AS vin,
  CAST(make AS STRING) AS make,
  CAST(model AS STRING) AS model,
  CAST(trim AS STRING) AS trim,
  CAST(model_year AS BIGINT) AS model_year,
  CAST(mileage AS BIGINT) AS mileage,
  CAST(owner_count AS BIGINT) AS owner_count,
  CAST(accident_count AS BIGINT) AS accident_count,
  CAST(title_brand AS STRING) AS title_brand,
  CAST(odometer_rollback_flag AS BIGINT) AS odometer_rollback_flag,
  CAST(auction_count AS BIGINT) AS auction_count,
  CAST(accs_score AS BIGINT) AS accs_score,
  CAST(last_reported_date AS TIMESTAMP) AS last_reported_date,
  CAST(garaged_zip AS STRING) AS garaged_zip,
  CAST(garaged_state AS STRING) AS garaged_state
FROM (
  SELECT *, row_number() OVER (PARTITION BY vin ORDER BY _file_modified_at DESC, _source_file DESC) AS _rn
  FROM bronze_autocheck_vin
)
WHERE _rn = 1;

CREATE OR REFRESH MATERIALIZED VIEW gold_lending (
  loan_id BIGINT COMMENT 'Surrogate primary key for the auto loan.',
  lender_name STRING COMMENT 'Originating lender (12-lender pool across banks, captives, credit unions, fintechs).',
  lender_type STRING COMMENT 'Lender category: Bank, Captive, Credit Union, or Fintech.',
  make STRING COMMENT 'Financed vehicle manufacturer (shared make pool).',
  model STRING COMMENT 'Financed vehicle model (shared model pool).',
  model_year BIGINT COMMENT 'Vehicle model year, 2015-2025.',
  region STRING COMMENT 'US macro region of the borrower (shared region pool).',
  state STRING COMMENT 'US state of the borrower.',
  orig_month TIMESTAMP COMMENT 'Loan origination month (first-of-month date).',
  orig_amount DOUBLE COMMENT 'Original financed amount in USD.' MASK ${experian.catalog}.${experian.schema}.mask_orig_amount,
  apr DOUBLE COMMENT 'Annual percentage rate (%). Rises with lower credit tier and used vehicles.',
  term_months BIGINT COMMENT 'Loan term in months (36-84).',
  credit_tier STRING COMMENT 'Borrower credit tier: Super Prime, Prime, Near Prime, or Subprime.',
  ltv_pct DOUBLE COMMENT 'Loan-to-value ratio (%). Higher for lower credit tiers.',
  monthly_payment DOUBLE COMMENT 'Scheduled monthly payment in USD (amortized).',
  delinquency_30d_flag BIGINT COMMENT '1 if the loan has ever been 30+ days delinquent, else 0. Rises with lower credit tier.',
  default_flag BIGINT COMMENT '1 if the loan has defaulted/charged off, else 0. Rises with lower credit tier.',
  new_used STRING COMMENT 'Whether the financed vehicle is New or Used.',
  CONSTRAINT valid_key EXPECT (loan_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_apr EXPECT (apr BETWEEN 0 AND 40) ON VIOLATION DROP ROW,
  CONSTRAINT valid_ltv EXPECT (ltv_pct BETWEEN 0 AND 250) ON VIOLATION DROP ROW,
  CONSTRAINT valid_credit_tier EXPECT (credit_tier IN ('Super Prime','Prime','Near Prime','Subprime'))
)
COMMENT "Experian automotive credit & lending loan-level dataset. One row per originated auto loan with lender, credit tier, APR, term, LTV, payment and delinquency/default performance. Join keys: make/model/model_year, state/region. Built by Lakeflow from bronze_lending (latest file wins per loan_id)."
WITH ROW FILTER ${experian.catalog}.${experian.schema}.rf_state ON (state)
AS SELECT
  CAST(loan_id AS BIGINT) AS loan_id,
  CAST(lender_name AS STRING) AS lender_name,
  CAST(lender_type AS STRING) AS lender_type,
  CAST(make AS STRING) AS make,
  CAST(model AS STRING) AS model,
  CAST(model_year AS BIGINT) AS model_year,
  CAST(region AS STRING) AS region,
  CAST(state AS STRING) AS state,
  CAST(orig_month AS TIMESTAMP) AS orig_month,
  CAST(orig_amount AS DOUBLE) AS orig_amount,
  CAST(apr AS DOUBLE) AS apr,
  CAST(term_months AS BIGINT) AS term_months,
  CAST(credit_tier AS STRING) AS credit_tier,
  CAST(ltv_pct AS DOUBLE) AS ltv_pct,
  CAST(monthly_payment AS DOUBLE) AS monthly_payment,
  CAST(delinquency_30d_flag AS BIGINT) AS delinquency_30d_flag,
  CAST(default_flag AS BIGINT) AS default_flag,
  CAST(new_used AS STRING) AS new_used
FROM (
  SELECT *, row_number() OVER (PARTITION BY loan_id ORDER BY _file_modified_at DESC, _source_file DESC) AS _rn
  FROM bronze_lending
)
WHERE _rn = 1;

-- #############################################################################
-- FUSION — Visual Prep flow D (the declarative SQL the Visual Prep canvas emits)
-- #############################################################################

-- -----------------------------------------------------------------------------
-- Intermediate: AutoCheck condition rollup by make/model/model_year/state
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW auto_condition_rollup
COMMENT "AutoCheck condition metrics aggregated to make/model/model_year/state — used to enrich market and feature tables."
AS
SELECT
  make,
  model,
  model_year,
  garaged_state                                            AS state,
  COUNT(*)                                                 AS vin_count,
  ROUND(AVG(accs_score), 1)                                AS avg_accs_score,
  ROUND(AVG(accident_count), 2)                            AS avg_accident_count,
  ROUND(AVG(CASE WHEN title_brand = 'Clean' THEN 1 ELSE 0 END), 3) AS clean_title_rate,
  ROUND(AVG(owner_count), 2)                               AS avg_owner_count,
  ROUND(AVG(mileage))                                      AS avg_mileage
FROM ${experian.catalog}.${experian.schema}.gold_autocheck_vin
GROUP BY make, model, model_year, garaged_state;

-- -----------------------------------------------------------------------------
-- Intermediate: Lending rollup by make/model/model_year/state
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW auto_lending_rollup
COMMENT "Auto lending metrics aggregated to make/model/model_year/state — average APR, LTV, delinquency and default rates, and lender participation."
AS
SELECT
  make,
  model,
  model_year,
  state,
  COUNT(*)                                                 AS loan_count,
  COUNT(DISTINCT lender_name)                              AS lender_count,
  ROUND(AVG(apr), 2)                                       AS avg_apr,
  ROUND(AVG(ltv_pct), 1)                                   AS avg_ltv_pct,
  ROUND(AVG(orig_amount))                                  AS avg_orig_amount,
  ROUND(AVG(delinquency_30d_flag), 3)                      AS delinquency_rate,
  ROUND(AVG(default_flag), 3)                              AS default_rate
FROM ${experian.catalog}.${experian.schema}.gold_lending
GROUP BY make, model, model_year, state;

-- -----------------------------------------------------------------------------
-- Genie-ready: analytics_market_360
-- Wide, human-readable market table. One row per make/model/model_year/state/month.
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW analytics_market_360
COMMENT "Market 360: VIO share and days-to-turn joined with AutoCheck condition rollups and lending rollups by make/model/model_year/state/month. This is the primary table for the Genie space and AI/BI dashboards."
WITH ROW FILTER ${experian.catalog}.${experian.schema}.rf_state ON (state)
AS
SELECT
  v.make,
  v.model,
  v.trim,
  v.model_year,
  v.body_style,
  v.fuel_type,
  v.state,
  v.dma_region,
  v.snapshot_month,
  v.registration_count,
  v.vio_count,
  v.market_share_pct,
  v.avg_days_to_turn,
  c.vin_count                       AS observed_vin_count,
  c.avg_accs_score,
  c.avg_accident_count,
  c.clean_title_rate,
  c.avg_owner_count,
  c.avg_mileage,
  l.loan_count,
  l.lender_count,
  l.avg_apr,
  l.avg_ltv_pct,
  l.avg_orig_amount,
  l.delinquency_rate,
  l.default_rate
FROM ${experian.catalog}.${experian.schema}.gold_vio_market v
LEFT JOIN auto_condition_rollup c
  ON  v.make = c.make AND v.model = c.model
  AND v.model_year = c.model_year AND v.state = c.state
LEFT JOIN auto_lending_rollup l
  ON  v.make = l.make AND v.model = l.model
  AND v.model_year = l.model_year AND v.state = l.state;

-- -----------------------------------------------------------------------------
-- Model-ready: feat_vehicle_fusion
-- One row per VIN, enriched with local VIO demand and lending risk for its
-- make/model/model_year/state. Feeds the residual / demand / risk models.
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW feat_vehicle_fusion
COMMENT "Per-VIN feature table fusing AutoCheck history with the vehicle's local VIO demand signal and lending risk profile. Model-ready input for residual value, days-to-turn, and default-risk models."
WITH ROW FILTER ${experian.catalog}.${experian.schema}.rf_state ON (state)
AS
SELECT
  a.vin,
  a.make,
  a.model,
  a.trim,
  a.model_year,
  a.mileage,
  a.owner_count,
  a.accident_count,
  a.title_brand,
  a.odometer_rollback_flag,
  a.auction_count,
  a.accs_score,
  a.garaged_state                       AS state,
  -- local demand signal from VIO (avg over months for the make/model/year/state)
  vm.market_share_pct                   AS local_market_share_pct,
  vm.avg_days_to_turn                   AS local_avg_days_to_turn,
  vm.vio_count                          AS local_vio_count,
  -- lending risk profile for the vehicle's segment
  l.avg_apr                             AS segment_avg_apr,
  l.avg_ltv_pct                         AS segment_avg_ltv_pct,
  l.delinquency_rate                    AS segment_delinquency_rate,
  l.default_rate                        AS segment_default_rate
FROM ${experian.catalog}.${experian.schema}.gold_autocheck_vin a
LEFT JOIN (
    SELECT make, model, model_year, state,
           ROUND(AVG(market_share_pct), 3) AS market_share_pct,
           ROUND(AVG(avg_days_to_turn))    AS avg_days_to_turn,
           ROUND(AVG(vio_count))           AS vio_count
    FROM ${experian.catalog}.${experian.schema}.gold_vio_market
    GROUP BY make, model, model_year, state
) vm
  ON  a.make = vm.make AND a.model = vm.model
  AND a.model_year = vm.model_year AND a.garaged_state = vm.state
LEFT JOIN auto_lending_rollup l
  ON  a.make = l.make AND a.model = l.model
  AND a.model_year = l.model_year AND a.garaged_state = l.state;

-- #############################################################################
-- OPERATIONAL SERVING SOURCE — synced to Lakebase Postgres
-- #############################################################################
-- One row per VIN carrying the Co-Pilot's display fields AND the full model
-- feature set, so GET /api/vin/{vin} is a single primary-key lookup in Postgres.
-- A Lakebase synced table (job task `sync_lakebase`, notebook 06_sync_lakebase) keeps
-- the Postgres copy <schema>.vin_serving_online in step with this view (SNAPSHOT mode).
-- Not granted to customers: operational table for the app service principal only.
CREATE OR REFRESH MATERIALIZED VIEW vin_serving
COMMENT "Operational per-VIN serving record (display fields + model features). Source of the Lakebase synced table serving the Co-Pilot VIN lookup."
AS
SELECT
  f.vin, f.make, f.model, f.trim, f.model_year, f.mileage, f.owner_count,
  f.accident_count, f.title_brand, f.odometer_rollback_flag, f.auction_count,
  f.accs_score, f.state, g.garaged_state, g.garaged_zip, g.last_reported_date,
  f.local_market_share_pct, f.local_avg_days_to_turn, f.local_vio_count,
  f.segment_avg_apr, f.segment_avg_ltv_pct, f.segment_delinquency_rate,
  f.segment_default_rate
FROM feat_vehicle_fusion f
LEFT JOIN ${experian.catalog}.${experian.schema}.gold_autocheck_vin g USING (vin);
