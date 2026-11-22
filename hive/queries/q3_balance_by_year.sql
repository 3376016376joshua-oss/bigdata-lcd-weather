-- Q3: do warm extremes outnumber cold extremes, per year.
-- One row per city and year plus one row per year for all cities together
-- (city_code = ALL). warm_share is warm / (warm + cold) and is NULL in a year
-- without any extreme day.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q3_balance_by_year.sql
WITH city_year AS (
  SELECT
    city_code,
    MAX(city) AS city,
    yr,
    COUNT(*) AS n_days,
    SUM(IF(dep_f >= 10, 1, 0)) AS warm_days,
    SUM(IF(dep_f <= -10, 1, 0)) AS cold_days
  FROM ${hivevar:db}.lcd_daily
  WHERE dep_f IS NOT NULL
  GROUP BY city_code, yr
),
scoped AS (
  SELECT city_code, city, yr, n_days, warm_days, cold_days
  FROM city_year
  UNION ALL
  SELECT
    'ALL' AS city_code,
    'All cities' AS city,
    yr,
    SUM(n_days) AS n_days,
    SUM(warm_days) AS warm_days,
    SUM(cold_days) AS cold_days
  FROM city_year
  GROUP BY yr
)
SELECT
  city_code,
  city,
  yr,
  n_days,
  warm_days AS warm_extreme_days,
  cold_days AS cold_extreme_days,
  warm_days - cold_days AS warm_minus_cold,
  IF(warm_days + cold_days = 0, CAST(NULL AS DOUBLE),
     ROUND(warm_days / (warm_days + cold_days), 3)) AS warm_share
FROM scoped
ORDER BY city_code, yr;
