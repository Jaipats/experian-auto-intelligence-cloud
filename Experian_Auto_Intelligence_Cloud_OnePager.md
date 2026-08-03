# Experian Auto Intelligence Cloud
### Turning automotive data into governed, AI-ready products on Databricks

---

## The Opportunity

Experian Automotive is one of the richest data franchises in the industry — reaching **90%+ of franchise dealers, all 9 public dealer groups, nearly every major U.S. OEM, and 90%+ of the top 50 auto lenders.** Today much of this data ships as flat-file extracts, portals, and static dashboards. Customers increasingly want **live, governed data and AI-driven answers** — not files they have to move, model, and maintain themselves.

**The play:** move from *selling files* to *selling an intelligence product* — governed live data plus a natural-language analyst and an AI app, all delivered on the Databricks Data Intelligence Platform.

## Three Datasets to Lead With

| Dataset | What it contains | Primary buyers |
|---|---|---|
| **VIO / Velocity** | Vehicles-in-Operation & market statistics: registrations, share, days-to-turn by make / model / geography | OEMs, dealers, aftermarket, insurers |
| **AutoCheck** | Vehicle history per VIN: title brands, accidents, owners, odometer, ACCS condition score | Dealers, lenders, insurers |
| **Credit & Lending** | Auto loan/lease originations, portfolio, delinquency, risk tiers, lender market share | Lenders, captives, fintechs |

## The Flagship AI App — "Inventory & Risk Co-Pilot"

One app that fuses all three datasets so a dealer, lender, or OEM can answer:

- **Acquire** — *Which used vehicles should I acquire, at what price, for my local demand?* (VIO + AutoCheck)
- **Price & Risk** — *What is the true condition-adjusted risk and residual on this VIN?* (AutoCheck + Credit)
- **Market Radar** — *Where is loan and lease share shifting, and which segments are underserved?* (Credit + VIO)
- **Ask (Genie)** — an embedded natural-language analyst for anything ad hoc

## How It Works on Databricks — One Prep, Four Consumption Modes

- **Databricks Visual Prep (Lakeflow Designer)** — no-code, drag-and-drop pipelines clean, standardize VIN & geography, join, aggregate, and feature-ize the three datasets into governed **gold data products** in Unity Catalog. Domain analysts productize data without hand-writing Spark.
- **Genie One** — a natural-language interface over the gold tables. Ask in plain English; get the answer, a chart, and the generated SQL — a self-service analyst embedded in the product.
- **AI/BI Dashboards & Mosaic AI Models** — residual, demand, and risk models on Model Serving power the Co-Pilot app's predictions and recommendations.
- **Delta Sharing & Marketplace** — customers query **live** data in their own cloud with no file copies; publish gold products as Marketplace listings or private shares.

Governance is built in: **Unity Catalog** row filters and column masks enforce per-contract entitlements, with full audit logs for billing and compliance.

## From Files to a Living Product

| Dimension | Today (Files & Portals) | Auto Intelligence Cloud |
|---|---|---|
| Delivery | SFTP extracts, static portals | Live Delta Sharing, no copies |
| Insights | Analyst builds reports | Genie NL answers + AI app |
| Time-to-value | Days to weeks | Minutes, self-serve |
| Monetization | Flat subscription | Tiered: data → +Genie → +App |

## POC Plan — 4 to 6 Weeks

1. **Weeks 1–2:** Land sample data; build 3 Visual Prep gold pipelines in Unity Catalog.
2. **Weeks 2–3:** Delta Share to a customer workspace; curated Genie Space answering 10 golden questions.
3. **Weeks 3–5:** Residual, demand, and risk models on Model Serving; Co-Pilot app with 3 modules + embedded Genie.
4. **Weeks 5–6:** Per-customer entitlements; end-to-end executive demo and monetization story.

**Success metrics:** time-to-productize a dataset (Visual Prep vs. legacy ETL), Genie NL answer accuracy, model lift (days-to-turn / residual error), and a clear "files → living product" revenue narrative.
