#!/usr/bin/env bash
# =============================================================================
# Step 6 — Create the Delta Share and share it with a customer workspace.
#
# ⚠️ REQUIRES METASTORE-ADMIN / CREATE_SHARE + CREATE_RECIPIENT on the provider
#    metastore. A plain catalog owner does NOT have this — a metastore admin must
#    either run this, or first grant you:
#      databricks grants update METASTORE <metastore_id> \
#        --json '{"changes":[{"principal":"<you>","add":["CREATE_SHARE","CREATE_RECIPIENT"]}]}'
#
# Provider metastore (this workspace): aws:us-east-1:c0da88f1-c020-4992-b8c9-c828e556889d
# Target customer workspace:           https://eastus2.azuredatabricks.net/  (Azure, East US 2)
# =============================================================================
set -euo pipefail
P="${DBX_PROFILE:-fe-vm-experian-agent-demo}"
CAT=experian_agent_demo_catalog
SCH=auto
SHARE=experian_auto_share
RECIPIENT=eastus2_customer

echo "==> 1. Create the share"
databricks shares create --profile "$P" --json '{
  "name":"'"$SHARE"'",
  "comment":"Experian Auto Intelligence Cloud - live gold + fused data products for a customer workspace."
}'

echo "==> 2. Add the gold + fused tables"
databricks shares update "$SHARE" --profile "$P" --json '{
  "updates":[
    {"action":"ADD","data_object":{"name":"'"$CAT.$SCH"'.gold_vio_market","data_object_type":"TABLE"}},
    {"action":"ADD","data_object":{"name":"'"$CAT.$SCH"'.gold_autocheck_vin","data_object_type":"TABLE"}},
    {"action":"ADD","data_object":{"name":"'"$CAT.$SCH"'.gold_lending","data_object_type":"TABLE"}},
    {"action":"ADD","data_object":{"name":"'"$CAT.$SCH"'.analytics_market_360","data_object_type":"TABLE"}}
  ]
}'

# ---------------------------------------------------------------------------
# 3. Create the recipient. TWO options depending on what you know about target.
# ---------------------------------------------------------------------------
# OPTION A — Databricks-to-Databricks (preferred when both sides are Databricks).
#   Needs the TARGET metastore's global sharing identifier. Get it FROM the
#   customer workspace (https://eastus2.azuredatabricks.net/) by running there:
#       SELECT current_metastore();            -- e.g. azure:eastus2:<uuid>
#   or Catalog > Delta Sharing > "Sharing identifier". Then:
#
#   databricks recipients create --profile "$P" --json '{
#     "name":"'"$RECIPIENT"'",
#     "authentication_type":"DATABRICKS",
#     "data_recipient_global_metastore_id":"azure:eastus2:<TARGET_METASTORE_UUID>",
#     "comment":"Customer workspace eastus2.azuredatabricks.net"
#   }'
#
# OPTION B — Open sharing (token-based). Works to ANY workspace with only the URL;
#   produces an activation link the customer opens to download credentials.
databricks recipients create --profile "$P" --json '{
  "name":"'"$RECIPIENT"'",
  "authentication_type":"TOKEN",
  "comment":"Customer workspace https://eastus2.azuredatabricks.net/ (open sharing)"
}'

echo "==> 4. Grant the share to the recipient"
databricks shares update-permissions "$SHARE" --profile "$P" --json '{
  "changes":[{"principal":"'"$RECIPIENT"'","add":["SELECT"]}]
}'

echo "==> 5. (Open sharing only) fetch the activation link to send the customer"
databricks recipients get "$RECIPIENT" --profile "$P" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('Activation link:', d.get('tokens',[{}])[0].get('activation_url','<pending>'))"

echo "Done. Then apply entitlements.sql for per-recipient row/column governance."
