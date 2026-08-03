# Databricks Marketplace Listing (notes)

To reach customers who aren't set up with a private share, publish the gold products as a
**Databricks Marketplace** listing. Consumers get the data in their own workspace via Delta
Sharing, with no copies.

## Listing structure

- **Provider:** Experian Automotive
- **Listing:** "Experian Auto Intelligence — Market, History & Lending"
- **Shares included:** a curated share of `analytics_market_360` (+ sample rows of the
  three golds for evaluation).
- **Access:** request-based (Experian approves each consumer) so entitlements/billing stay
  under contract control.

## Steps

1. Provider profile → Marketplace → **Provider console** → create provider.
2. Create a **listing** and attach the Delta Share (a public/eval share, not the full
   contract share).
3. Add metadata: description, data dictionary (reuse the column comments), sample queries
   (reuse `03_genie/sample_questions.md`), refresh cadence, and terms.
4. Publish (private or public). Approve consumer requests; on approval, grant the
   contract-scoped share + apply `entitlements.sql`.

## Why Marketplace + private shares together

- **Marketplace** = discovery + eval + self-serve onboarding.
- **Private share + entitlements** = the actual, per-contract, governed product.
- **App tier** (`05_app`) rides on top for customers who buy the full experience.
