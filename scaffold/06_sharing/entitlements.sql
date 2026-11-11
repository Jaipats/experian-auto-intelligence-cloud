-- =============================================================================
-- Per-customer entitlements enforced by Unity Catalog: row filters + column masks.
-- These are what let ONE set of gold tables serve MANY customers safely.
--
-- Model: an `entitlements` table maps each principal (current_user(): a user's
-- email, or a service principal's application id) to a customer contract —
-- the states it bought ('*' = all) and a tier ('full' | 'standard').
--
--   * Row filter  rf_state(state)        -> a principal sees only its contracted states
--   * Column mask mask_orig_amount(amt)  -> 'standard' tier sees amounts rounded to $1,000
--
-- This file is a TEMPLATE: {catalog} and {schema} are filled in by the job's `setup`
-- task (scaffold/07_orchestration/notebooks/00_setup.py), which also loads the contract
-- rows (deployer + app service principal + FULL_ACCESS_PRINCIPALS + TENANT_CONTRACTS).
-- The Lakeflow pipeline attaches these functions in its DDL, so they must exist before
-- the pipeline's first run (the job orders setup → generate_data → build_fusion).
-- =============================================================================

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.entitlements (
  principal STRING COMMENT 'Value of current_user(): user email or service-principal application id.',
  customer  STRING COMMENT 'Customer / contract the principal belongs to.',
  tier      STRING COMMENT 'Contract tier: full (exact values) or standard (coarsened values).',
  state     STRING COMMENT 'US state the principal is entitled to, or * for all states.'
) COMMENT 'Customer data-contract entitlements. Drives the rf_state row filter and mask_orig_amount column mask.';

-- Row filter: a principal only sees the states in its contract (workspace admins see all).
CREATE OR REPLACE FUNCTION {catalog}.{schema}.rf_state(state STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: TRUE when the caller is entitled to this state (entitlements table), or is a workspace admin.'
RETURN is_member('admins') OR EXISTS (
  SELECT 1 FROM {catalog}.{schema}.entitlements e
  WHERE e.principal = current_user()
    AND (e.state = '*' OR e.state = rf_state.state)
);

-- Column mask: exact origination amount for full-tier contracts, $1,000 bands otherwise.
CREATE OR REPLACE FUNCTION {catalog}.{schema}.mask_orig_amount(amt DOUBLE)
RETURNS DOUBLE
COMMENT 'Column mask: exact orig_amount for full-tier contracts / admins, rounded to the nearest $1,000 otherwise.'
RETURN CASE
  WHEN is_member('admins') OR EXISTS (
         SELECT 1 FROM {catalog}.{schema}.entitlements e
         WHERE e.principal = current_user() AND e.tier = 'full')
  THEN amt
  ELSE ROUND(amt, -3)
END;
