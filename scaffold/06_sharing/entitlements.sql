-- Per-customer entitlements enforced by Unity Catalog: row filters + column masks.
-- These are what let ONE set of gold tables serve MANY customers safely.

-- ---------------------------------------------------------------------------
-- Row filter: a recipient only sees the states/regions in their contract.
-- The mapping table holds (recipient, state) grants; the filter joins to it
-- using the current recipient identity exposed via current_recipient().
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experian_agent_demo_catalog.auto.contract_geo_grants (
  recipient STRING,
  state     STRING
) COMMENT 'Which states each Delta Sharing recipient is entitled to.';

-- Example: Acme dealer group bought CA, NV, AZ.
MERGE INTO experian_agent_demo_catalog.auto.contract_geo_grants t
USING (SELECT * FROM VALUES
  ('acme_dealer_group','CA'),('acme_dealer_group','NV'),('acme_dealer_group','AZ')
  AS v(recipient,state)) s
ON t.recipient = s.recipient AND t.state = s.state
WHEN NOT MATCHED THEN INSERT *;

CREATE OR REPLACE FUNCTION experian_agent_demo_catalog.auto.rf_state(state STRING)
RETURN EXISTS (
  SELECT 1 FROM experian_agent_demo_catalog.auto.contract_geo_grants g
  WHERE g.state = state
    AND g.recipient = current_recipient('recipient_name')  -- recipient identity
);

ALTER TABLE experian_agent_demo_catalog.auto.gold_vio_market
  SET ROW FILTER experian_agent_demo_catalog.auto.rf_state ON (state);
ALTER TABLE experian_agent_demo_catalog.auto.analytics_market_360
  SET ROW FILTER experian_agent_demo_catalog.auto.rf_state ON (state);
ALTER TABLE experian_agent_demo_catalog.auto.gold_lending
  SET ROW FILTER experian_agent_demo_catalog.auto.rf_state ON (state);

-- ---------------------------------------------------------------------------
-- Column mask: coarsen the origination amount for lower tiers (band, not exact).
-- Swap current_recipient() checks for your entitlement model as needed.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION experian_agent_demo_catalog.auto.mask_orig_amount(amt DOUBLE)
RETURN CASE
  WHEN is_account_group_member('experian_full_tier') THEN amt
  ELSE ROUND(amt, -3)  -- round to nearest $1,000 for lower tiers
END;

ALTER TABLE experian_agent_demo_catalog.auto.gold_lending
  ALTER COLUMN orig_amount SET MASK experian_agent_demo_catalog.auto.mask_orig_amount;
