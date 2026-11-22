-- Q6: day-to-day temperature volatility, daily range and humidity per city.
-- tavg_change_sd_f is the standard deviation of the change of the daily mean
-- temperature from one day to the next (only pairs of consecutive calendar days
-- are used). Humidity comes from the routine hourly reports (FM-15).
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q6_city_volatility.sql
WITH lagged AS (
  SELECT
    city_code,
    city,
    obs_date,
    tavg_f,
    temp_range_f,
    LAG(tavg_f) OVER (PARTITION BY city_code ORDER BY obs_date) AS prev_tavg_f,
    LAG(obs_date) OVER (PARTITION BY city_code ORDER BY obs_date) AS prev_date
  FROM ${hivevar:db}.lcd_daily
  WHERE is_primary_station
),
changes AS (
  SELECT
    city_code,
    city,
    temp_range_f,
    IF(DATEDIFF(obs_date, prev_date) = 1, tavg_f - prev_tavg_f, CAST(NULL AS DOUBLE))
      AS tavg_change
  FROM lagged
),
daily_stats AS (
  SELECT
    city_code,
    MAX(city) AS city,
    COUNT(*) AS n_days,
    COUNT(tavg_change) AS n_changes,
    STDDEV_SAMP(tavg_change) AS tavg_change_sd,
    AVG(ABS(tavg_change)) AS mean_abs_change,
    AVG(temp_range_f) AS mean_range
  FROM changes
  GROUP BY city_code
),
humidity AS (
  SELECT
    city_code,
    AVG(rh_pct) AS mean_rh,
    AVG(dewpt_f) AS mean_dewpt
  FROM ${hivevar:db}.lcd_hourly
  WHERE is_primary_station AND report_type = 'FM-15'
  GROUP BY city_code
)
SELECT
  RANK() OVER (ORDER BY d.tavg_change_sd DESC) AS volatility_rank,
  d.city_code,
  d.city,
  d.n_days,
  d.n_changes,
  ROUND(d.tavg_change_sd, 2) AS tavg_change_sd_f,
  ROUND(d.mean_abs_change, 2) AS mean_abs_tavg_change_f,
  ROUND(d.mean_range, 2) AS mean_daily_range_f,
  ROUND(h.mean_rh, 1) AS mean_rh_pct,
  ROUND(h.mean_dewpt, 1) AS mean_dewpt_f
FROM daily_stats d
LEFT JOIN humidity h ON d.city_code = h.city_code
ORDER BY volatility_rank, city_code;
