# Genie Space — Sample Questions & Certified SQL

Add these as **Trusted assets / example SQL** in the Genie Space. They double as the
demo script. All queries target `experian_agent_demo_catalog.auto`.

---

### 1. Fastest-turning used SUVs in a region
> "Show me the top 10 fastest-turning SUVs in California in the latest month."

```sql
SELECT make, model, model_year, avg_days_to_turn, market_share_pct
FROM experian_agent_demo_catalog.auto.analytics_market_360
WHERE body_style = 'SUV'
  AND state = 'CA'
  AND snapshot_month = (SELECT MAX(snapshot_month)
                        FROM experian_agent_demo_catalog.auto.analytics_market_360)
ORDER BY avg_days_to_turn ASC
LIMIT 10;
```

---

### 2. Clean history but trading below segment demand
> "Which model-years have the highest clean-title rate but slower-than-average days-to-turn?"

```sql
WITH seg AS (
  SELECT AVG(avg_days_to_turn) AS seg_dtt
  FROM experian_agent_demo_catalog.auto.analytics_market_360
)
SELECT m.make, m.model, m.model_year,
       m.clean_title_rate, m.avg_accs_score,
       m.avg_days_to_turn, ROUND(s.seg_dtt) AS segment_avg_dtt
FROM experian_agent_demo_catalog.auto.analytics_market_360 m CROSS JOIN seg s
WHERE m.clean_title_rate >= 0.8
  AND m.avg_days_to_turn > s.seg_dtt
ORDER BY m.clean_title_rate DESC, m.avg_days_to_turn DESC
LIMIT 15;
```

---

### 3. Lender share shift vs captives
> "How has lending volume by lender type break down in the Midwest?"

```sql
SELECT l.lender_type,
       COUNT(*)                         AS loans,
       ROUND(AVG(l.apr), 2)             AS avg_apr,
       ROUND(AVG(l.delinquency_30d_flag), 3) AS delinquency_rate
FROM experian_agent_demo_catalog.auto.gold_lending l
WHERE l.region = 'Midwest'
GROUP BY l.lender_type
ORDER BY loans DESC;
```

---

### 4. Condition-adjusted acquisition candidates
> "Best used vehicles to acquire: strong demand and clean history."

```sql
SELECT make, model, model_year, body_style,
       avg_days_to_turn, market_share_pct, avg_accs_score, clean_title_rate
FROM experian_agent_demo_catalog.auto.analytics_market_360
WHERE snapshot_month = (SELECT MAX(snapshot_month)
                        FROM experian_agent_demo_catalog.auto.analytics_market_360)
  AND avg_accs_score >= 80
ORDER BY avg_days_to_turn ASC, market_share_pct DESC
LIMIT 20;
```

---

### 5. Risk by segment for lenders
> "Which segments have the highest default rate relative to their APR?"

```sql
SELECT make, model, model_year,
       avg_apr, avg_ltv_pct, delinquency_rate, default_rate
FROM experian_agent_demo_catalog.auto.analytics_market_360
WHERE loan_count >= 20
ORDER BY default_rate DESC
LIMIT 15;
```

---

### 6. Single-VIN history lookup
> "Show me the full history for VIN <vin>."

```sql
SELECT *
FROM experian_agent_demo_catalog.auto.gold_autocheck_vin
WHERE vin = :vin;
```

---

### 7. EV demand trend
> "How is EV market share trending month over month by state?"

```sql
SELECT snapshot_month, state,
       ROUND(SUM(CASE WHEN fuel_type = 'EV' THEN vio_count ELSE 0 END) * 100.0
             / NULLIF(SUM(vio_count), 0), 2) AS ev_share_pct
FROM experian_agent_demo_catalog.auto.analytics_market_360
GROUP BY snapshot_month, state
ORDER BY state, snapshot_month;
```
