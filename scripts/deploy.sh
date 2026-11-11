#!/usr/bin/env bash
# =============================================================================
# One-command deploy of the Experian Auto Intelligence Cloud demo.
#
#   1. Ensure the Lakebase Autoscaling project exists (creates it if missing)
#   2. databricks bundle deploy  (pipeline, job, app + bindings)
#   3. databricks bundle run copilot           (deploy app source, start the app)
#   4. databricks bundle run experian_auto_e2e (setup → data → Lakeflow → Lakebase
#                                              sync, models, serving, Genie)
#
# Usage:  cp .env.example .env   # fill in CATALOG, WAREHOUSE_ID, profile…
#         scripts/deploy.sh [--deploy-only] [-t <target>]
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TARGET=dev
RUN=1
while [ $# -gt 0 ]; do
  case "$1" in
    --deploy-only) RUN=0 ;;
    -t|--target) TARGET="$2"; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

[ -f .env ] && set -a && . ./.env && set +a
: "${CATALOG:?Set CATALOG in .env (an existing Unity Catalog catalog you can CREATE SCHEMA in)}"
: "${WAREHOUSE_ID:?Set WAREHOUSE_ID in .env (a SQL warehouse id)}"
export DATABRICKS_CONFIG_PROFILE="${DATABRICKS_CONFIG_PROFILE:-DEFAULT}"

# .env keys → bundle variables (only the ones that are set override the defaults)
map() { [ -n "${!1:-}" ] && export "BUNDLE_VAR_$2=${!1}" || true; }
map CATALOG catalog;            map SCHEMA schema;                  map WAREHOUSE_ID warehouse_id
map APP_NAME app_name;          map ENDPOINT_PREFIX endpoint_prefix; map GENIE_SPACE_TITLE genie_space_title
map LAKEBASE_PROJECT lakebase_project;          map LAKEBASE_BRANCH lakebase_branch
map LAKEBASE_DATABASE_ID lakebase_database_id;  map LAKEBASE_PG_DATABASE lakebase_pg_database
map FULL_ACCESS_PRINCIPALS full_access_principals; map TENANT_CONTRACTS tenant_contracts

PROJECT="${LAKEBASE_PROJECT:-experian-auto-oltp}"
echo "==> Profile ${DATABRICKS_CONFIG_PROFILE} · target ${TARGET} · ${CATALOG}.${SCHEMA:-experian_auto}"
databricks current-user me -o json >/dev/null

echo "==> 1/4 Lakebase project ${PROJECT}"
if databricks postgres get-project "projects/${PROJECT}" >/dev/null 2>&1; then
  echo "    exists"
else
  echo "    creating (Autoscaling, takes a few minutes)…"
  databricks postgres create-project "${PROJECT}" \
    --json '{"spec": {"display_name": "Experian Auto OLTP (Lakebase)"}}' >/dev/null
fi

echo "==> 2/4 bundle deploy"
databricks bundle validate -t "$TARGET" >/dev/null
databricks bundle deploy -t "$TARGET"

if [ "$RUN" = 1 ]; then
  echo "==> 3/4 start the Co-Pilot app"
  databricks bundle run -t "$TARGET" copilot
  echo "==> 4/4 run the end-to-end job (≈20–30 min on first run)"
  databricks bundle run -t "$TARGET" experian_auto_e2e
fi

APP="${APP_NAME:-experian-copilot}"
URL=$(databricks apps get "$APP" -o json | python3 -c 'import json,sys;print(json.load(sys.stdin).get("url",""))')
echo
echo "Done. Co-Pilot app: ${URL}"
[ "$RUN" = 1 ] || echo "Run it with: databricks bundle run -t ${TARGET} copilot && databricks bundle run -t ${TARGET} experian_auto_e2e"
