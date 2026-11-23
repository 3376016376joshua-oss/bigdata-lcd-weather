-- Q2: warm and cold extreme days per city and year.
-- An extreme day has a daily mean temperature 10 degF or more above (warm) or
-- below (cold) the station normal.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q2_extreme_days_by_year.sql
WITH city_year AS (
  SELECT
    city_code,
    MAX(city) AS city,
    yr,
    COUNT(*) AS n_days,
    SUM(IF(dep_f >= 10, 1, 0)) AS warm_days,
    SUM(IF(dep_f <= -10, 1, 0)) AS cold_days
  FROM ${hivevar:db}.lcd_daily
  WHERE is_primary_station AND dep_f IS NOT NULL
  GROUP BY city_code, yr
)
SELECT
  city_code,
  city,
  yr,
  n_days,
  warm_days AS warm_extreme_days,
  cold_days AS cold_extreme_days,
  warm_days + cold_days AS extreme_days,
  ROUND(100 * (warm_days + cold_days) / n_days, 2) AS extreme_day_pct
FROM city_year
ORDER BY city_code, yr;
