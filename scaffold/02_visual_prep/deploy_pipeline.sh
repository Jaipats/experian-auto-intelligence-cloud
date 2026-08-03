#!/usr/bin/env bash
# Create & run the Visual Prep / Lakeflow fusion pipeline via the Databricks CLI.
# Prereq: fusion_pipeline.sql uploaded to the workspace (see UPLOAD step).
set -euo pipefail

PROFILE="${DBX_PROFILE:-fe-vm-experian-agent-demo}"
CATALOG="experian_agent_demo_catalog"
SCHEMA="auto"
WS_DIR="/Workspace/Users/jaideep.patel@databricks.com/experian_auto/visual_prep"
PIPELINE_NAME="experian_auto_fusion"

echo "==> Uploading fusion_pipeline.sql to workspace"
databricks workspace mkdirs "$WS_DIR" --profile "$PROFILE"
databricks workspace import "$WS_DIR/fusion_pipeline.sql" \
  --file fusion_pipeline.sql --language SQL --format SOURCE --overwrite \
  --profile "$PROFILE"

echo "==> Creating Lakeflow pipeline: $PIPELINE_NAME"
cat > /tmp/${PIPELINE_NAME}.json <<JSON
{
  "name": "${PIPELINE_NAME}",
  "catalog": "${CATALOG}",
  "schema": "${SCHEMA}",
  "serverless": true,
  "continuous": false,
  "libraries": [
    { "file": { "path": "${WS_DIR}/fusion_pipeline.sql" } }
  ]
}
JSON

PIPELINE_ID=$(databricks pipelines create --json @/tmp/${PIPELINE_NAME}.json \
  --profile "$PROFILE" | python3 -c "import sys,json;print(json.load(sys.stdin)['pipeline_id'])")
echo "    pipeline_id=$PIPELINE_ID"

echo "==> Starting an update (build the materialized views)"
databricks pipelines start-update "$PIPELINE_ID" --profile "$PROFILE"

echo "Done. Watch progress in the Lakeflow Pipelines UI."
echo "Outputs: ${CATALOG}.${SCHEMA}.analytics_market_360 and .feat_vehicle_fusion"
