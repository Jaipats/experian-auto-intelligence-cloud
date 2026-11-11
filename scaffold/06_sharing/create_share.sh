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
# Not part of the bundle deploy (it needs metastore-level privileges). Configure via
# .env at the repo root or the environment:
#   DATABRICKS_CONFIG_PROFILE  CLI profile          CATALOG / SCHEMA   source tables
#   SHARE_NAME                 share to create      RECIPIENT_NAME     customer recipient
#
# Note: the gold tables carry UC row filters / column masks keyed on current_user().
# For recipients, extend rf_state / mask_orig_amount with a current_recipient() branch
# (or share dynamic views) so each recipient is scoped by its contract.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env" && set +a
P="${DATABRICKS_CONFIG_PROFILE:-DEFAULT}"
CAT="${CATALOG:?set CATALOG}"
SCH="${SCHEMA:-experian_auto}"
SHARE="${SHARE_NAME:-experian_auto_share}"
RECIPIENT="${RECIPIENT_NAME:-demo_customer}"

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
#   customer workspace by running there:
#       SELECT current_metastore();            -- e.g. <cloud>:<region>:<uuid>
#   or Catalog > Delta Sharing > "Sharing identifier". Then:
#
#   databricks recipients create --profile "$P" --json '{
#     "name":"'"$RECIPIENT"'",
#     "authentication_type":"DATABRICKS",
#     "data_recipient_global_metastore_id":"<cloud>:<region>:<TARGET_METASTORE_UUID>",
#     "comment":"Customer workspace"
#   }'
#
# OPTION B — Open sharing (token-based). Works to ANY workspace with only the URL;
#   produces an activation link the customer opens to download credentials.
databricks recipients create --profile "$P" --json '{
  "name":"'"$RECIPIENT"'",
  "authentication_type":"TOKEN",
  "comment":"Customer workspace (open sharing)"
}'

echo "==> 4. Grant the share to the recipient"
databricks shares update-permissions "$SHARE" --profile "$P" --json '{
  "changes":[{"principal":"'"$RECIPIENT"'","add":["SELECT"]}]
}'

echo "==> 5. (Open sharing only) fetch the activation link to send the customer"
databricks recipients get "$RECIPIENT" --profile "$P" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('Activation link:', d.get('tokens',[{}])[0].get('activation_url','<pending>'))"

echo "Done."
