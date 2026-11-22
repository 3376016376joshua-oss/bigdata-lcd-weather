-- Q4: size of the seasonal and daily temperature cycles per city.
-- seasonal_amplitude_f is the warmest minus the coldest monthly mean, and
-- mean_daily_range_f is the average of daily max minus daily min.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q4_cycle_amplitude.sql
WITH monthly AS (
  SELECT
    city_code,
    MAX(city) AS city,
    MONTH(obs_date) AS mo,
    AVG(tavg_f) AS mean_tavg,
    SUM(tavg_f) AS sum_tavg,
    COUNT(tavg_f) AS n_tavg,
    SUM(temp_range_f) AS sum_range,
    COUNT(temp_range_f) AS n_range
  FROM ${hivevar:db}.lcd_daily
  GROUP BY city_code, MONTH(obs_date)
),
city_cycle AS (
  SELECT
    city_code,
    MAX(city) AS city,
    SUM(sum_tavg) / SUM(n_tavg) AS annual_mean,
    MAX(mean_tavg) AS warmest_month_mean,
    MIN(mean_tavg) AS coldest_month_mean,
    SUM(sum_range) / SUM(n_range) AS mean_daily_range
  FROM monthly
  GROUP BY city_code
)
SELECT
  city_code,
  city,
  ROUND(annual_mean, 2) AS annual_mean_f,
  ROUND(warmest_month_mean, 2) AS warmest_month_mean_f,
  ROUND(coldest_month_mean, 2) AS coldest_month_mean_f,
  ROUND(warmest_month_mean - coldest_month_mean, 2) AS seasonal_amplitude_f,
  ROUND(mean_daily_range, 2) AS mean_daily_range_f
FROM city_cycle
ORDER BY seasonal_amplitude_f DESC, city_code;
