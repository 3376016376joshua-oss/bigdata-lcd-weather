-- Q6: the volatility, daily range and humidity of q6_city_volatility.sql split
-- by season (DJF, MAM, JJA, SON). A day-to-day change belongs to the season of
-- its second day.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q6_seasonal_volatility.sql
WITH lagged AS (
  SELECT
    city_code,
    city,
    season,
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
    season,
    temp_range_f,
    IF(DATEDIFF(obs_date, prev_date) = 1, tavg_f - prev_tavg_f, CAST(NULL AS DOUBLE))
      AS tavg_change
  FROM lagged
),
daily_stats AS (
  SELECT
    city_code,
    MAX(city) AS city,
    season,
    COUNT(*) AS n_days,
    STDDEV_SAMP(tavg_change) AS tavg_change_sd,
    AVG(ABS(tavg_change)) AS mean_abs_change,
    AVG(temp_range_f) AS mean_range
  FROM changes
  GROUP BY city_code, season
),
humidity AS (
  SELECT
    city_code,
    season,
    AVG(rh_pct) AS mean_rh
  FROM ${hivevar:db}.lcd_hourly
  WHERE is_primary_station AND report_type = 'FM-15'
  GROUP BY city_code, season
)
SELECT
  d.city_code,
  d.city,
  d.season,
  d.n_days,
  ROUND(d.tavg_change_sd, 2) AS tavg_change_sd_f,
  ROUND(d.mean_abs_change, 2) AS mean_abs_tavg_change_f,
  ROUND(d.mean_range, 2) AS mean_daily_range_f,
  ROUND(h.mean_rh, 1) AS mean_rh_pct
FROM daily_stats d
LEFT JOIN humidity h ON d.city_code = h.city_code AND d.season = h.season
ORDER BY city_code, season;
