-- Q2: in which seasons the warm and cold extreme days of each city fall.
-- Counts cover all years. The share columns give the percentage of the
-- warm (or cold) extreme days that fall in each season (DJF, MAM, JJA, SON).
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q2_extreme_days_by_season.sql
WITH city_season AS (
  SELECT
    city_code,
    MAX(city) AS city,
    season,
    COUNT(*) AS n_days,
    SUM(IF(dep_f >= 10, 1, 0)) AS warm_days,
    SUM(IF(dep_f <= -10, 1, 0)) AS cold_days
  FROM ${hivevar:db}.lcd_daily
  WHERE dep_f IS NOT NULL
  GROUP BY city_code, season
),
with_totals AS (
  SELECT
    city_code,
    city,
    season,
    n_days,
    warm_days,
    cold_days,
    SUM(warm_days) OVER (PARTITION BY city_code) AS city_warm_days,
    SUM(cold_days) OVER (PARTITION BY city_code) AS city_cold_days
  FROM city_season
)
SELECT
  city_code,
  city,
  season,
  n_days,
  warm_days AS warm_extreme_days,
  cold_days AS cold_extreme_days,
  ROUND(100 * warm_days / n_days, 2) AS warm_extreme_day_pct,
  ROUND(100 * cold_days / n_days, 2) AS cold_extreme_day_pct,
  IF(city_warm_days = 0, CAST(NULL AS DOUBLE),
     ROUND(100 * warm_days / city_warm_days, 1)) AS share_of_city_warm_pct,
  IF(city_cold_days = 0, CAST(NULL AS DOUBLE),
     ROUND(100 * cold_days / city_cold_days, 1)) AS share_of_city_cold_pct
FROM with_totals
ORDER BY city_code, season;
