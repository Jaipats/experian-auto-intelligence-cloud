-- Create a Delta Share for a customer and add the entitled gold + fused products.
-- Run on the provider (Experian) side.

CREATE SHARE IF NOT EXISTS experian_auto_share
  COMMENT 'Experian Auto Intelligence Cloud — live data products for a customer contract.';

-- Add the three gold datasets + the Genie-ready analytics table.
ALTER SHARE experian_auto_share
  ADD TABLE experian_agent_demo_catalog.auto.gold_vio_market;
ALTER SHARE experian_auto_share
  ADD TABLE experian_agent_demo_catalog.auto.gold_autocheck_vin;
ALTER SHARE experian_auto_share
  ADD TABLE experian_agent_demo_catalog.auto.gold_lending;
ALTER SHARE experian_auto_share
  ADD TABLE experian_agent_demo_catalog.auto.analytics_market_360;

-- Create a recipient for the customer (open sharing token, or Databricks-to-Databricks).
CREATE RECIPIENT IF NOT EXISTS acme_dealer_group
  COMMENT 'Example customer: a franchise dealer group.';

-- Grant the share to the recipient.
GRANT SELECT ON SHARE experian_auto_share TO RECIPIENT acme_dealer_group;
