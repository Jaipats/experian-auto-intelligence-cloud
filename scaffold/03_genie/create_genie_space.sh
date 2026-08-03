#!/usr/bin/env bash
# Sketch of programmatic Genie Space creation.
# For the POC, creating the Space in the UI is fastest (see README). This script
# documents the API shape; the Genie Spaces API surface evolves, so verify the
# current endpoint/fields with the internal `genie-rooms` skill before relying on it.
set -euo pipefail
PROFILE="${DBX_PROFILE:-fe-vm-experian-agent-demo}"
HOST=$(databricks auth env --profile "$PROFILE" 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['DATABRICKS_HOST'])" 2>/dev/null || echo "https://fevm-experian-agent-demo.cloud.databricks.com")

WAREHOUSE_ID="${WAREHOUSE_ID:?set WAREHOUSE_ID to a serverless SQL warehouse id}"

cat <<JSON
Create the Genie Space with these settings (UI or API):

  title:        Experian Auto Intelligence — Genie
  warehouse_id: ${WAREHOUSE_ID}
  tables:
    - experian_agent_demo_catalog.auto.analytics_market_360
    - experian_agent_demo_catalog.auto.gold_autocheck_vin
    - experian_agent_demo_catalog.auto.gold_lending
  instructions: (paste contents of genie_instructions.md)
  sample_questions + certified SQL: (from sample_questions.md)
JSON

# Example REST call (adjust to current Genie API):
# curl -s -X POST "$HOST/api/2.0/genie/spaces" \
#   -H "Authorization: Bearer $(databricks auth token --profile "$PROFILE" | jq -r .access_token)" \
#   -H "Content-Type: application/json" \
#   -d @genie_space_payload.json
