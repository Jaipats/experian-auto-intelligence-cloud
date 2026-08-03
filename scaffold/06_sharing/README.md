# 06 — Delta Sharing & Governance

Publish the gold products to customers as **live** shares (no file copies), with
per-customer entitlements enforced by Unity Catalog. This is the distribution + monetization
layer that turns the datasets into products.

## What's here

- `create_share.sql` — create a Delta Share and add the gold + fused tables.
- `entitlements.sql` — row filters and column masks that enforce per-contract access
  (e.g. a dealer-group recipient only sees its own states; PII-ish columns masked by tier).
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

## Target for this engagement

Customer workspace: **https://eastus2.azuredatabricks.net/** (Azure, East US 2).
Provider metastore: `aws:us-east-1:c0da88f1-c020-4992-b8c9-c828e556889d` (cross-cloud share — supported).

## ⚠️ Permission prerequisite (blocker encountered)

Creating a share/recipient needs **`CREATE_SHARE` + `CREATE_RECIPIENT` on the metastore**,
which is a *metastore-admin* privilege — **separate from catalog ownership**. In this
workspace `jaideep.patel@databricks.com` owns the catalog but is **not** a metastore admin,
so `databricks shares create` returns:

```
Error: User does not have CREATE SHARE on Metastore 'metastore_aws_us_east_1'.
```

A metastore admin must either run `create_share.sh`, or first grant the privileges:

```bash
databricks grants update METASTORE c0da88f1-c020-4992-b8c9-c828e556889d --profile $DBX_PROFILE \
  --json '{"changes":[{"principal":"jaideep.patel@databricks.com","add":["CREATE_SHARE","CREATE_RECIPIENT"]}]}'
```

## Apply (once you have the privilege)

```bash
DBX_PROFILE=fe-vm-experian-agent-demo bash create_share.sh          # create share, add tables, recipient, grant
databricks sql -e "$(cat entitlements.sql)" --warehouse $WAREHOUSE_ID --profile $DBX_PROFILE   # row/column governance
```

`create_share.sh` supports two recipient modes:
- **Databricks-to-Databricks** — needs the target metastore's sharing id (run
  `SELECT current_metastore();` in the eastus2 workspace to get `azure:eastus2:<uuid>`).
- **Open sharing (token)** — works with only the URL; emits an activation link to send the
  customer. This is the default in the script since we only have the destination URL.
