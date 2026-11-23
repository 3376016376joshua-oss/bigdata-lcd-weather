-- Q6: special weather reports (FM-16) on wet days against dry days per city.
-- A wet day has at least 0.01 in of precipitation. pressure_range_hpa is the
-- highest minus the lowest station pressure reported during the day. Only days
-- that have hourly reports are counted.
-- Run: beeline -u <jdbc-url> --hivevar db=<database> -f hive/queries/q6_special_reports_by_day_type.sql
WITH hourly_day AS (
  SELECT
    city_code,
    obs_date,
    SUM(IF(report_type = 'FM-16', 1, 0)) AS special_reports,
    SUM(IF(report_type = 'FM-15', 1, 0)) AS routine_reports,
    MAX(station_pressure_hpa) - MIN(station_pressure_hpa) AS pressure_range
  FROM ${hivevar:db}.lcd_hourly
  WHERE is_primary_station AND report_type IN ('FM-15', 'FM-16')
  GROUP BY city_code, obs_date
),
days AS (
  SELECT
    d.city_code,
    d.city,
    IF(d.prcp_in >= 0.01, 'wet', 'dry') AS day_type,
    h.special_reports,
    h.routine_reports,
    h.pressure_range
  FROM ${hivevar:db}.lcd_daily d
  JOIN hourly_day h ON d.city_code = h.city_code AND d.obs_date = h.obs_date
  WHERE d.is_primary_station AND d.prcp_in IS NOT NULL
)
SELECT
  city_code,
  MAX(city) AS city,
  day_type,
  COUNT(*) AS n_days,
  SUM(special_reports) AS special_reports,
  ROUND(AVG(special_reports), 2) AS mean_special_reports_per_day,
  ROUND(100 * AVG(IF(special_reports > 0, 1, 0)), 1) AS pct_days_with_special,
  ROUND(100 * SUM(special_reports) / SUM(special_reports + routine_reports), 1)
    AS special_share_of_reports_pct,
  ROUND(AVG(pressure_range), 2) AS mean_pressure_range_hpa
FROM days
GROUP BY city_code, day_type
ORDER BY city_code, day_type;
