-- =============================================================================
-- Visual Prep / Lakeflow Declarative Pipeline — Flow D: Fusion layer
-- Target catalog.schema: experian_agent_demo_catalog.auto
--
-- This is the declarative SQL that the Visual Prep canvas emits. It fuses the
-- three gold products (VIO, AutoCheck, Lending) into:
--   * analytics_market_360   -> Genie-ready wide market table (feeds 03_genie)
--   * feat_vehicle_fusion     -> model-ready per-VIN feature table (feeds 04_models)
--
-- Run as a Lakeflow (Delta Live Tables) pipeline. Uses STREAMING/MV semantics
-- via LIVE tables; here modeled as materialized views for simplicity.
-- =============================================================================

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
FROM experian_agent_demo_catalog.auto.gold_autocheck_vin
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
FROM experian_agent_demo_catalog.auto.gold_lending
GROUP BY make, model, model_year, state;

-- -----------------------------------------------------------------------------
-- Genie-ready: analytics_market_360
-- Wide, human-readable market table. One row per make/model/model_year/state/month.
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW analytics_market_360
COMMENT "Market 360: VIO share and days-to-turn joined with AutoCheck condition rollups and lending rollups by make/model/model_year/state/month. This is the primary table for the Genie space and AI/BI dashboards."
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
FROM experian_agent_demo_catalog.auto.gold_vio_market v
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
FROM experian_agent_demo_catalog.auto.gold_autocheck_vin a
LEFT JOIN (
    SELECT make, model, model_year, state,
           ROUND(AVG(market_share_pct), 3) AS market_share_pct,
           ROUND(AVG(avg_days_to_turn))    AS avg_days_to_turn,
           ROUND(AVG(vio_count))           AS vio_count
    FROM experian_agent_demo_catalog.auto.gold_vio_market
    GROUP BY make, model, model_year, state
) vm
  ON  a.make = vm.make AND a.model = vm.model
  AND a.model_year = vm.model_year AND a.garaged_state = vm.state
LEFT JOIN auto_lending_rollup l
  ON  a.make = l.make AND a.model = l.model
  AND a.model_year = l.model_year AND a.garaged_state = l.state;
