# Evidence — Stage 5: Genie (natural-language analytics)

_Captured 2026-09-25T22:11:09Z. Real questions answered by the Genie space "Experian Auto Intelligence — Genie" (space `01f1856aac00130baa08132c96170c4b`), via the app's `/api/ask` proxy to the Genie Conversations API. Each answer shows Genie's generated SQL and the returned rows._

## Q1: Top 5 fastest-turning SUVs in California this month

**Genie answer:** For **California** in **June 2025**, the **5 fastest-turning SUVs** in the results are:
- **2018 Hyundai Tucson** — **17 days to turn**, **1.54%** market share
- **2015 Ford Explorer** — **20 days to turn**, **1.18%** market share
- **2015 Ford Explorer** — **31 days to turn**, **1.69%** market share
- **2025 Subaru Outback** — **36 days to turn**, **1.67%** market share
- **2021 Subaru Outback** — **36 days to turn**, **0.89%** market share
Across these 5 results, turn time ranges from **17 to 36 days**, with the **Hyundai Tucson** turning the fastest.

**Generated SQL:**
```sql
SELECT `make`, `model`, `model_year`, `avg_days_to_turn`, `market_share_pct`, `snapshot_month`
FROM `experian_agent_demo_catalog`.`auto`.`analytics_market_360`
WHERE `body_style` IS NOT NULL
  AND `body_style` ILIKE '%SUV%'
  AND `state` IS NOT NULL
  AND `state` ILIKE '%CA%'
  AND `snapshot_month` = (
    SELECT MAX(`snapshot_month`)
    FROM `experian_agent_demo_catalog`.`auto`.`analytics_market_360`
  )
  AND `avg_days_to_turn` IS NOT NULL
  AND `make` IS NOT NULL
  AND `model` IS NOT NULL
  AND `model_year` IS NOT NULL
ORDER BY `avg_days_to_turn` ASC, `market_share_pct` DESC, `vio_count` DESC
LIMIT 5
```

**Result (5 rows):**

| make | model | model_year | avg_days_to_turn | market_share_pct | snapshot_month |
|---|---|---|---|---|---|
| Hyundai | Tucson | 2018 | 17 | 1.54 | 2025-06-01T00:00:00.000Z |
| Ford | Explorer | 2015 | 20 | 1.18 | 2025-06-01T00:00:00.000Z |
| Ford | Explorer | 2015 | 31 | 1.69 | 2025-06-01T00:00:00.000Z |
| Subaru | Outback | 2025 | 36 | 1.67 | 2025-06-01T00:00:00.000Z |
| Subaru | Outback | 2021 | 36 | 0.89 | 2025-06-01T00:00:00.000Z |

## Q2: Which lender types have the highest delinquency rate in the West region?

**Genie answer:** In the **West** region, **Captive** lenders have the highest delinquency rate at **6.5%**, based on **1,337** loans. In this result set, **Captive** is the top-ranked lender type for delinquency in the West.

**Generated SQL:**
```sql
WITH lender_delinquency AS (
  SELECT
    lender_type,
    COUNT(*) AS loan_count,
    100 * (try_divide(SUM(delinquency_30d_flag),COUNT(*))) AS delinquency_rate
  FROM experian_agent_demo_catalog.auto.gold_lending
  WHERE region = 'West' AND lender_type IS NOT NULL
  GROUP BY lender_type
), ranked AS (
  SELECT
    lender_type,
    loan_count,
    delinquency_rate,
    RANK() OVER (ORDER BY delinquency_rate DESC) AS rnk
  FROM lender_delinquency
)
SELECT
  lender_type,
  loan_count,
  delinquency_rate
FROM ranked
WHERE rnk = 1
ORDER BY lender_type
```

**Result (1 rows):**

| lender_type | loan_count | delinquency_rate |
|---|---|---|
| Captive | 1337 | 6.507105459985041 |

## Q3: Where is demand high but lender coverage low?

**Genie answer:** Using the latest month shown, **June 2025**, the strongest pockets of high demand with below-average lender coverage in this sample are concentrated in **Boise, Denver, Las Vegas, Charlotte, and Milwaukee**. Examples include:
- **Charlotte, NC — 2015 Jeep Grand Cherokee:** **19 days** to turn, **1** lender, **1.48%** market share
- **Las Vegas, NV — 2025 Nissan Rogue:** **24 days** to turn, **2** lenders, **8.40%** market share
- **Boise, ID — 2025 Nissan Rogue:** **27 days** to turn, **2** lenders, **7.65%** market share
- **Charlotte, NC — 2015 Nissan Rogue:** **27 days** to turn, **2** lenders, **6.47%** market share
- **Boise, ID — 2016 Subaru Outback:** **32 days** to turn, **1** lender, **8.68%** market share
Across all **20** results, lender coverage is very thin at just **1–2 lenders**, while demand remains strong with turn times ranging from **19 to 50 days**.

**Generated SQL:**
```sql
WITH `latest_month` AS (
  SELECT MAX(`snapshot_month`) AS `snapshot_month`
  FROM `experian_agent_demo_catalog`.`auto`.`analytics_market_360`
), `base` AS (
  SELECT
    `state`,
    `dma_region`,
    `make`,
    `model`,
    `model_year`,
    `avg_days_to_turn`,
    `market_share_pct`,
    `lender_count`,
    `snapshot_month`
  FROM `experian_agent_demo_catalog`.`auto`.`analytics_market_360`
  WHERE `snapshot_month` = (SELECT `snapshot_month` FROM `latest_month`)
    AND `state` IS NOT NULL
    AND `dma_region` IS NOT NULL
    AND `avg_days_to_turn` IS NOT NULL
    AND `lender_count` IS NOT NULL
    AND `market_share_pct` IS NOT NULL
), `benchmarks` AS (
  SELECT
    AVG(`avg_days_to_turn`) AS `avg_days_to_turn_benchmark`,
    AVG(`lender_count`) AS `lender_count_benchmark`
  FROM `base`
)
SELECT
  `state`,
  `dma_region`,
  `make`,
  `model`,
  `model_year`,
  `avg_days_to_turn`,
  `market_share_pct`,
  `lender_count`,
  `snapshot_month`
FROM `base`
CROSS JOIN `benchmarks`
WHERE `avg_days_to_turn` < `avg_days_to_turn_benchmark`
  AND `lender_count` < `lender_count_benchmark`
ORDER BY `lender_count` ASC, `avg_days_to_turn` ASC, `market_share_pct` DESC
LIMIT 20
```

**Result (20 rows):**

| state | dma_region | make | model | model_year | avg_days_to_turn | market_share_pct | lender_count | snapshot_month |
|---|---|---|---|---|---|---|---|---|
| NC | Charlotte | Jeep | Grand Cherokee | 2015 | 19 | 1.48 | 1 | 2025-06-01T00:00:00.000Z |
| CO | Denver | Honda | CR-V | 2016 | 28 | 0.63 | 1 | 2025-06-01T00:00:00.000Z |
| ID | Boise | Subaru | Outback | 2016 | 32 | 8.68 | 1 | 2025-06-01T00:00:00.000Z |
| OR | Portland | Chevrolet | Silverado | 2025 | 34 | 4.06 | 1 | 2025-06-01T00:00:00.000Z |
| MN | Minneapolis | Chevrolet | Equinox | 2020 | 35 | 9.84 | 1 | 2025-06-01T00:00:00.000Z |
| WA | Seattle | Toyota | Camry | 2022 | 36 | 3.3 | 1 | 2025-06-01T00:00:00.000Z |
| CO | Denver | Nissan | Altima | 2015 | 39 | 5.68 | 1 | 2025-06-01T00:00:00.000Z |
| ID | Boise | Subaru | Outback | 2017 | 42 | 6.32 | 1 | 2025-06-01T00:00:00.000Z |
| WI | Milwaukee | Ram | 1500 | 2024 | 46 | 6.71 | 1 | 2025-06-01T00:00:00.000Z |
| CO | Denver | Jeep | Grand Cherokee | 2020 | 46 | 5.93 | 1 | 2025-06-01T00:00:00.000Z |
