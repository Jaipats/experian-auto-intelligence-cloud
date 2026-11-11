# 06 — Delta Sharing & Governance

Publish the gold products to customers as **live** shares (no file copies), with
per-customer entitlements enforced by Unity Catalog. This is the distribution + monetization
layer that turns the datasets into products.

## What's here

- `create_share.sql` — create a Delta Share and add the gold + fused tables.
- `entitlements.sql`: the `entitlements` contract table, plus the `rf_state` row filter and
  `mask_orig_amount` column mask keyed on `current_user()`. **Applied and verified live**:
  `sp_contoso` (Contoso Dealer Group, standard tier) sees only CA/NV/AZ with amounts rounded
  to $1,000, and `sp_northwind` (Northwind Auto Finance, full tier) sees only TX/FL with exact
  amounts. See `../../evidence/07_unity_catalog_governance.md`. The Lakeflow pipeline attaches
  the filter and mask in its DDL, so run this file before the first pipeline run.
- `marketplace_listing.md` — notes for publishing as a Databricks Marketplace listing.

## Model

- **One share per customer** (or per contract tier), each granted to that customer's
  Delta Sharing recipient.
- **Row filters** scope a recipient to the geographies / segments they bought.
- **Column masks** hide or coarsen sensitive columns for lower tiers.
- **Audit:** `system.access.audit` + Delta Sharing recipient activity give per-recipient
  usage for billing and compliance.

## Tiers (maps to the deck's monetization story)

| Tier | Shared objects |
|---|---|
| **Data** | `gold_vio_market`, `gold_autocheck_vin`, `gold_lending` (entitled subset) |
| **+ Genie** | above + `analytics_market_360` + access to the Genie space |
| **+ App** | above + the Co-Pilot app + model endpoints |

## ⚠️ Permission prerequisite

Creating a share or recipient needs **`CREATE_SHARE` + `CREATE_RECIPIENT` on the metastore**,
a metastore-admin privilege that is separate from catalog ownership. Without it,
`databricks shares create` returns `User does not have CREATE SHARE on Metastore '…'`.
A metastore admin must run `create_share.sh`, or first grant you the privileges:

```bash
databricks grants update METASTORE <metastore-id> \
  --json '{"changes":[{"principal":"<you>","add":["CREATE_SHARE","CREATE_RECIPIENT"]}]}'
```

## Entitlements (deployed by the job's `setup` task)

The filter and mask key off `current_user()` (a user's email, or a service principal's
application id), looked up in `<catalog>.<schema>.entitlements`. The deployer, workspace
admins, `FULL_ACCESS_PRINCIPALS` and the Co-Pilot app SP are entitled to `*` / `full`, so the
app, Genie, model training and the pipeline keep full visibility. Demo customers come from
`TENANT_CONTRACTS` in `.env`:

```bash
TENANT_CONTRACTS='[{"principal":"<sp-application-id>","customer":"Contoso Dealer Group","tier":"standard","states":["CA","NV","AZ"]}]'
```

The `sync_lakebase` task grants each tenant `SELECT` on `gold_vio_market`, `gold_lending`
and `analytics_market_360`, and the filter and mask decide what they see. To onboard another
customer, add it to `TENANT_CONTRACTS` and re-run the job, or `INSERT` rows into the
`entitlements` table directly. No DDL changes are needed. Evidence of the filter and mask
working per identity: `../../evidence/07_unity_catalog_governance.md`.

For **Delta Sharing recipients**, add a recipient-aware branch to the functions
(`current_recipient('…')`) or share a dynamic view, because `current_user()` isn't the
recipient identity in a share.

## Create the share (needs the privilege above)

```bash
bash scaffold/06_sharing/create_share.sh     # reads CATALOG / SCHEMA / profile from .env
```

`create_share.sh` supports two recipient modes:
- **Databricks-to-Databricks**: needs the target metastore's sharing id (run
  `SELECT current_metastore();` in the customer workspace).
- **Open sharing (token)**: works with only the workspace URL and prints an activation link
  to send the customer. This is the script's default.
