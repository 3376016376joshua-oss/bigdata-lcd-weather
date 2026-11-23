-- Q1: monthly temperature anomaly and warm/cold extreme days per city.
-- The representative query of the proposal, keyed by city_code. Only the primary
-- station of each city and year is read, so the Los Angeles series is
-- Downtown/USC for 2010-2023 and LAX for 2024-2025.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q1_monthly_anomaly.sql
-- Extreme day threshold: daily mean 10 degF or more above or below normal.
SELECT
  city_code,
  MAX(city) AS city,
  yr,
  MONTH(obs_date) AS mo,
  COUNT(dep_f) AS n_days,
  ROUND(AVG(dep_f), 2) AS anomaly_f,
  SUM(IF(dep_f >= 10, 1, 0)) AS warm_extreme_days,
  SUM(IF(dep_f <= -10, 1, 0)) AS cold_extreme_days
FROM ${hivevar:db}.lcd_daily
WHERE is_primary_station AND dep_f IS NOT NULL
GROUP BY city_code, yr, MONTH(obs_date)
ORDER BY city_code, yr, mo;
