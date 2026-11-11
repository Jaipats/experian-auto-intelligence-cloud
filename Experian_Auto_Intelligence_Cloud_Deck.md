# Experian Auto Intelligence Cloud — Business Overview (deck)

Text version of the presentation deck (`Experian_Auto_Intelligence_Cloud_Deck.pdf`,
also in Google Slides). Audience: automotive data buyer — executive sponsor + domain owner.

---

**Slide 1 — Title**
Experian Auto Intelligence Cloud
_Turning automotive data into a governed inventory & risk product on Databricks_

**Slide 2 — Section**
Insight arrives too late to price the car

**Slide 3 — Every extra day on the lot, every mispriced loan, is margin lost**
- Used vehicles that sit too long bleed gross profit — carrying cost, depreciation, floorplan interest
- Lenders misprice risk when vehicle condition and local demand never reach the credit decision
- Experian VIO, AutoCheck & lending data reach 90%+ of franchise dealers and top-50 lenders — yet ship as flat files customers must move, model and maintain
- The result: static reports, disconnected from the acquire / price / lend decision

**Slide 4 — The outcome, first**
- **Turn inventory faster** — predict days-to-turn and price each unit to a target turn speed
- **Price risk sharper** — condition- and demand-adjusted default risk, inside the credit decision
- **Sell data as a product** — live, governed data + AI, not flat files customers must maintain

**Slide 5 — Quantified impact (illustrative)**
- _Domain owner — inventory & pricing:_ days-to-turn predicted within ~4 days; residual value within ~$932; ~5–7 fewer days on lot per unit → ~10–15% faster turns
- _Executive sponsor — P&L & growth:_ default risk ranked at AUC 0.90; 25–50 bps of avoided loss on a $1B portfolio ≈ $2.5–5M / yr; new revenue via data → +Genie → +App tiers

**Slide 6 — The solution: Inventory & Risk Co-Pilot**
- **Acquire** — which used vehicles to buy, at what price, for local demand (VIO + AutoCheck)
- **Price & Risk** — condition-adjusted residual value and default risk on any VIN (AutoCheck + Credit)
- **Market Radar** — where loan & lease share is shifting and which segments are underserved
- **Ask (Genie)** — a natural-language analyst for anything ad hoc, with the SQL shown

**Slide 7 — One platform, six integrated stages**
- **Ingest & prep** — Lakeflow / Visual Prep lands and fuses VIO, AutoCheck and lending into gold products
- **Govern & serve** — Unity Catalog governs every field; Lakebase Postgres serves sub-ms VIN lookups
- **Make it intelligent** — Mosaic AI models + Genie NL, surfaced in the Co-Pilot Databricks App

**Slide 8 — It's real — live, not a mockup**
- _Built & running today:_ 20,000 VINs served from Lakebase (0.08 ms indexed lookup); 3 models live on Model Serving; Genie answers in plain English with generated SQL; app live with VIN lookup `served_by = lakebase`
- _Model & data quality:_ default-risk AUC 0.90; days-to-turn MAE ~4 days; residual MAE ~$932; 54,320 governed gold rows across 3 datasets

**Slide 9 — From files to a living product**
- _Today — files & portals:_ SFTP extracts, static portals; an analyst builds every report; days-to-weeks time-to-value; flat subscription
- _Auto Intelligence Cloud:_ live Delta Sharing, no copies; Genie NL answers + an AI app; minutes, self-serve; tiered monetization: data → +Genie → +App

**Slide 10 — Get there in 4–6 weeks**
- Weeks 1–2 — land sample data; build 3 Visual Prep gold pipelines in Unity Catalog
- Weeks 2–3 — Delta Share to a customer workspace; Genie space answering 10 golden questions
- Weeks 3–5 — residual / days-to-turn / default models; Co-Pilot app + Lakebase serving
- Weeks 5–6 — per-customer entitlements; executive demo and monetization story

**Slide 11 — Statement**
Move from selling files to selling intelligence.

**Slide 12 — Closing**

---

_Impact figures on slide 5 are illustrative — grounded in the demo models' measured performance
(evidence/04b) applied to public automotive industry benchmarks, not a specific customer's results._
