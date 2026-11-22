-- Q3: did the warm minus cold balance change over 2010-2025.
-- Least-squares linear trend of the yearly counts against the year, expressed
-- per decade, for each city and for all cities together (city_code = ALL).
-- slope = covar_pop(year, value) / var_pop(year). The fitted line is
-- mean_warm_minus_cold + slope_per_year * (yr - mean_yr).
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q3_balance_trend.sql
WITH city_year AS (
  SELECT
    city_code,
    MAX(city) AS city,
    yr,
    SUM(IF(dep_f >= 10, 1, 0)) AS warm_days,
    SUM(IF(dep_f <= -10, 1, 0)) AS cold_days
  FROM ${hivevar:db}.lcd_daily
  WHERE dep_f IS NOT NULL
  GROUP BY city_code, yr
),
scoped AS (
  SELECT city_code, city, yr, warm_days, cold_days
  FROM city_year
  UNION ALL
  SELECT
    'ALL' AS city_code,
    'All cities' AS city,
    yr,
    SUM(warm_days) AS warm_days,
    SUM(cold_days) AS cold_days
  FROM city_year
  GROUP BY yr
),
fitted AS (
  SELECT
    city_code,
    MAX(city) AS city,
    COUNT(*) AS n_years,
    MIN(yr) AS first_yr,
    MAX(yr) AS last_yr,
    AVG(yr) AS mean_yr,
    SUM(warm_days) AS warm_days,
    SUM(cold_days) AS cold_days,
    AVG(warm_days - cold_days) AS mean_balance,
    VAR_POP(yr) AS yr_variance,
    COVAR_POP(yr, warm_days - cold_days) AS balance_covariance,
    COVAR_POP(yr, warm_days) AS warm_covariance,
    COVAR_POP(yr, cold_days) AS cold_covariance,
    CORR(yr, warm_days - cold_days) AS balance_correlation
  FROM scoped
  GROUP BY city_code
)
SELECT
  city_code,
  city,
  n_years,
  first_yr,
  last_yr,
  ROUND(mean_yr, 2) AS mean_yr,
  warm_days AS warm_extreme_days,
  cold_days AS cold_extreme_days,
  IF(cold_days = 0, CAST(NULL AS DOUBLE),
     ROUND(warm_days / cold_days, 2)) AS warm_to_cold_ratio,
  ROUND(mean_balance, 2) AS mean_warm_minus_cold,
  IF(yr_variance = 0, CAST(NULL AS DOUBLE),
     ROUND(10 * balance_covariance / yr_variance, 3)) AS balance_slope_per_decade,
  IF(yr_variance = 0, CAST(NULL AS DOUBLE),
     ROUND(10 * warm_covariance / yr_variance, 3)) AS warm_slope_per_decade,
  IF(yr_variance = 0, CAST(NULL AS DOUBLE),
     ROUND(10 * cold_covariance / yr_variance, 3)) AS cold_slope_per_decade,
  ROUND(balance_correlation, 3) AS balance_trend_r
FROM fitted
ORDER BY city_code;
