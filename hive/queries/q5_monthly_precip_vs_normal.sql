-- Q5: monthly precipitation against normal per city, year and month.
-- total_prcp_in is the sum of the daily totals. normal_prcp_in is the station
-- normal recovered from the monthly summary (monthly total minus its departure)
-- and is NULL when the monthly summary has no departure. period_mean_prcp_in is
-- the 2010-2025 mean of the same city and calendar month, a second baseline
-- that is always available.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q5_monthly_precip_vs_normal.sql
WITH daily_month AS (
  SELECT
    city_code,
    MAX(city) AS city,
    yr,
    MONTH(obs_date) AS mo,
    COUNT(*) AS n_days,
    SUM(IF(prcp_in >= 0.01, 1, 0)) AS wet_days,
    SUM(prcp_in) AS total_prcp
  FROM ${hivevar:db}.lcd_daily
  WHERE prcp_in IS NOT NULL
  GROUP BY city_code, yr, MONTH(obs_date)
),
official AS (
  SELECT
    city_code,
    yr,
    `month` AS mo,
    MAX(total_prcp_in - dep_prcp_in) AS normal_prcp
  FROM ${hivevar:db}.lcd_monthly
  GROUP BY city_code, yr, `month`
),
joined AS (
  SELECT
    d.city_code,
    d.city,
    d.yr,
    d.mo,
    d.n_days,
    d.wet_days,
    d.total_prcp,
    o.normal_prcp
  FROM daily_month d
  LEFT JOIN official o
    ON d.city_code = o.city_code AND d.yr = o.yr AND d.mo = o.mo
)
SELECT
  city_code,
  city,
  yr,
  mo,
  n_days,
  wet_days,
  ROUND(total_prcp, 2) AS total_prcp_in,
  ROUND(normal_prcp, 2) AS normal_prcp_in,
  ROUND(total_prcp - normal_prcp, 2) AS dep_prcp_in,
  ROUND(AVG(total_prcp) OVER (PARTITION BY city_code, mo), 2) AS period_mean_prcp_in,
  ROUND(total_prcp - AVG(total_prcp) OVER (PARTITION BY city_code, mo), 2)
    AS dep_vs_period_mean_in
FROM joined
ORDER BY city_code, yr, mo;
