# 03 — Genie One: Natural-Language Interface

A **Genie Space** over the fused analytics table lets dealers, lenders, and OEMs ask
questions in plain English and get an answer, a chart, and the generated SQL. The same
Space is embedded in the Co-Pilot App (`05_app`) as the "Ask" tab.

## Space configuration

- **Name:** Experian Auto Intelligence — Genie
- **Primary tables:**
  - `experian_agent_demo_catalog.auto.analytics_market_360` (the wide market table)
  - `experian_agent_demo_catalog.auto.gold_autocheck_vin` (per-VIN drilldown)
  - `experian_agent_demo_catalog.auto.gold_lending` (loan-level drilldown)
- **Instructions:** see `genie_instructions.md`
- **Sample questions & certified SQL:** see `sample_questions.md`

## Create the Space

Two options:

1. **UI (recommended for the demo):** Genie → New Space → add the three tables above →
   paste `genie_instructions.md` into *General instructions* → add each certified query in
   `sample_questions.md` as a *Trusted asset / example SQL* → add the sample questions.

2. **API/CLI:** use the `genie-rooms` skill (internal) or the Genie REST API to author the
   space programmatically. `create_genie_space.sh` shows the shape of the call.

## Why the comments matter

Genie grounds its SQL generation on table/column `COMMENT`s. The `01_data` generator and
the `02_visual_prep` pipeline both write descriptive comments, so the Space needs minimal
extra curation. Always verify the certified queries return sensible results before a demo.
