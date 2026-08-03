#!/usr/bin/env bash
# Deploy the three registered UC models to Model Serving endpoints.
set -euo pipefail
PROFILE="${DBX_PROFILE:-fe-vm-experian-agent-demo}"
CATALOG="experian_agent_demo_catalog"
SCHEMA="auto"

deploy () {
  local endpoint="$1" model="$2"
  echo "==> Creating serving endpoint: $endpoint (model $CATALOG.$SCHEMA.$model)"
  cat > /tmp/${endpoint}.json <<JSON
{
  "name": "${endpoint}",
  "config": {
    "served_entities": [{
      "entity_name": "${CATALOG}.${SCHEMA}.${model}",
      "entity_version": "1",
      "workload_size": "Small",
      "scale_to_zero_enabled": true
    }]
  }
}
JSON
  databricks serving-endpoints create --json @/tmp/${endpoint}.json --profile "$PROFILE" \
    || databricks serving-endpoints update-config --json @/tmp/${endpoint}.json --profile "$PROFILE"
}

deploy "experian-residual-value" "residual_value_model"
deploy "experian-days-to-turn"   "days_to_turn_model"
deploy "experian-default-risk"   "default_risk_model"

echo "Endpoints created. Set these in the App env (see 05_app/app.yaml)."
