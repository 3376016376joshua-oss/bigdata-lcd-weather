-- Q1: temperature anomaly per city for every complete July-June year.
-- The FiveThirtyEight reference year is 2014-07 to 2015-06, so the 16 calendar
-- years are regrouped into July-June periods labelled by their starting year.
-- Only periods with all 12 months present are kept.
-- Regions: West = Los Angeles, Phoenix, Seattle. East = Chicago, Indianapolis,
-- New York, Philadelphia. The remaining cities are Other.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q1_jul_jun_city_anomaly.sql
WITH tagged AS (
  SELECT
    city_code,
    city,
    dep_f,
    MONTH(obs_date) AS mo,
    IF(MONTH(obs_date) >= 7, yr, yr - 1) AS start_yr
  FROM ${hivevar:db}.lcd_daily
  WHERE dep_f IS NOT NULL
),
city_period AS (
  SELECT
    city_code,
    MAX(city) AS city,
    start_yr,
    COUNT(*) AS n_days,
    COUNT(DISTINCT mo) AS n_months,
    AVG(dep_f) AS anomaly
  FROM tagged
  GROUP BY city_code, start_yr
)
SELECT
  city_code,
  city,
  CASE
    WHEN city_code IN ('KCQT', 'KPHX', 'KSEA') THEN 'West'
    WHEN city_code IN ('KMDW', 'KIND', 'KNYC', 'KPHL') THEN 'East'
    ELSE 'Other'
  END AS region,
  start_yr,
  CONCAT(CAST(start_yr AS STRING), '-07..', CAST(start_yr + 1 AS STRING), '-06') AS period_label,
  n_days,
  ROUND(anomaly, 2) AS anomaly_f,
  RANK() OVER (PARTITION BY city_code ORDER BY anomaly DESC) AS warm_rank_in_city
FROM city_period
WHERE n_months = 12
ORDER BY city_code, start_yr;
