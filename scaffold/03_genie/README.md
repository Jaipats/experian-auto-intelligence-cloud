# 03 — Genie: Natural-Language Interface

A **Genie Space** over the fused analytics table lets dealers, lenders, and OEMs ask
questions in plain English and get an answer, a chart, and the generated SQL. The same
Space is embedded in the Co-Pilot App (`05_app`) as the "Ask" tab.

## Space configuration

- **Name:** Experian Auto Intelligence — Genie
- **Primary tables:**
  - `<catalog>.<schema>.analytics_market_360` (the wide market table)
  - `<catalog>.<schema>.gold_autocheck_vin` (per-VIN drilldown)
  - `<catalog>.<schema>.gold_lending` (loan-level drilldown)
- **Instructions:** see `genie_instructions.md`
- **Sample questions & certified SQL:** see `sample_questions.md`

## How it's created

The job's `create_genie_space` task (`../07_orchestration/notebooks/05_create_genie_space.py`)
creates or updates the space (matched by title) on every run, with the instructions and the
nine certified example SQLs, and grants the Co-Pilot app's service principal `CAN_RUN`. The
app finds the space by its title (`GENIE_SPACE_TITLE`), so no space id needs to be configured.

To build it by hand instead: Genie → New Space → add the three tables above → paste
`genie_instructions.md` into *General instructions* → add each query in `sample_questions.md`
as example SQL.

## Why the comments matter

Genie grounds its SQL generation on table/column `COMMENT`s. The `02_visual_prep` pipeline declares
descriptive comments on every gold and fusion column, so the Space needs minimal
extra curation. Always verify the certified queries return sensible results before a demo.
