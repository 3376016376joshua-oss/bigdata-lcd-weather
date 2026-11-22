-- Q1: which cities deviated most from normal temperatures over 2010-2025.
-- Cities are ranked by the mean absolute monthly anomaly. The warmest and coldest
-- month of each city are reported as yyyymm with their anomaly.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q1_city_deviation_ranking.sql
WITH monthly AS (
  SELECT
    city_code,
    MAX(city) AS city,
    yr,
    MONTH(obs_date) AS mo,
    AVG(dep_f) AS anomaly
  FROM ${hivevar:db}.lcd_daily
  WHERE dep_f IS NOT NULL
  GROUP BY city_code, yr, MONTH(obs_date)
),
ranked AS (
  SELECT
    city_code,
    city,
    yr,
    mo,
    anomaly,
    ROW_NUMBER() OVER (PARTITION BY city_code ORDER BY anomaly DESC, yr, mo) AS warm_rn,
    ROW_NUMBER() OVER (PARTITION BY city_code ORDER BY anomaly ASC, yr, mo) AS cold_rn
  FROM monthly
),
summary AS (
  SELECT
    city_code,
    MAX(city) AS city,
    COUNT(*) AS n_months,
    AVG(anomaly) AS mean_anomaly,
    AVG(ABS(anomaly)) AS mean_abs_anomaly,
    MAX(IF(warm_rn = 1, yr * 100 + mo, NULL)) AS warmest_yyyymm,
    MAX(IF(warm_rn = 1, anomaly, NULL)) AS warmest_anomaly,
    MAX(IF(cold_rn = 1, yr * 100 + mo, NULL)) AS coldest_yyyymm,
    MAX(IF(cold_rn = 1, anomaly, NULL)) AS coldest_anomaly
  FROM ranked
  GROUP BY city_code
)
SELECT
  RANK() OVER (ORDER BY mean_abs_anomaly DESC) AS deviation_rank,
  city_code,
  city,
  n_months,
  ROUND(mean_anomaly, 2) AS mean_monthly_anomaly_f,
  ROUND(mean_abs_anomaly, 2) AS mean_abs_monthly_anomaly_f,
  warmest_yyyymm,
  ROUND(warmest_anomaly, 2) AS warmest_month_anomaly_f,
  coldest_yyyymm,
  ROUND(coldest_anomaly, 2) AS coldest_month_anomaly_f
FROM summary
ORDER BY deviation_rank, city_code;
